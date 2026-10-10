import logging

from cryptography.fernet import Fernet
from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from ..extensions import db
from ..models import Attempt, AttemptVMInstance, Exam, ExamVMRequirement, User
from ..services.attempt_data import (
    attempt_response,
    authenticated_user_id,
    ensure_examtry_exam,
    now_utc_naive,
)
from ..services.proxmox_operations import ProxmoxProvider
from ..services.ssh_terminal import create_attempt_ssh_key

attempt_create_bp = Blueprint("attempt_create", __name__)
logger = logging.getLogger(__name__)

LFCS_SLUG = "lfcs"
LFCS_NAME = "Linux Foundation Certified System Administrator"


def _ensure_catalog_exam() -> Exam:
    exam = db.session.scalar(select(Exam).where(Exam.name == LFCS_NAME))
    if exam is None:
        exam = Exam(
            slug=LFCS_SLUG,
            name=LFCS_NAME,
            description=(
                "Hands-on Linux system administration practice covering "
                "users, permissions, storage, networking, services, and security."
            ),
            duration_minutes=current_app.config["EXAM_SESSION_HOURS"] * 60,
            active=True,
        )
        db.session.add(exam)
        db.session.flush()
    elif exam.slug is None:
        exam.slug = LFCS_SLUG

    has_vm_requirements = db.session.scalar(
        select(ExamVMRequirement.id)
        .where(ExamVMRequirement.exam_id == exam.id)
        .limit(1)
    )
    if has_vm_requirements is None:
        try:
            template_vmid = int(current_app.config["PROXMOX_TEMPLATE_VMID"])
        except (TypeError, ValueError):
            template_vmid = 0
        if template_vmid > 0:
            db.session.add(ExamVMRequirement(
                exam_id=exam.id,
                name="main",
                template_vmid=template_vmid,
                snap_id=current_app.config["PROXMOX_TEMPLATE_SNAP_ID"] or None,
                node=current_app.config["PROXMOX_NODE"],
                ssh_username=current_app.config["EXAM_VM_SSH_USERNAME"],
                is_main=True,
            ))
    return exam


@attempt_create_bp.get("/exams/by-slug/<string:slug>")
def get_exam_by_slug(slug: str):
    if slug == "lfcs":
        exam = _ensure_catalog_exam()
        db.session.commit()
    elif slug == "examtry":
        exam = ensure_examtry_exam()
        db.session.commit()
    else:
        exam = db.session.scalar(
            select(Exam).where(Exam.slug == slug, Exam.active.is_(True))
        )
    if exam is None or not exam.active:
        return jsonify({"error": "Exam not found or unavailable."}), 404

    requirements = db.session.scalars(
        select(ExamVMRequirement)
        .where(ExamVMRequirement.exam_id == exam.id)
        .order_by(ExamVMRequirement.id)
    ).all()
    return jsonify({
        "exam": {
            "id": exam.id,
            "slug": exam.slug,
            "name": exam.name,
            "description": exam.description,
            "duration_minutes": exam.duration_minutes,
            "vm_count": len(requirements),
            "main_vm": next(
                (requirement.name for requirement in requirements if requirement.is_main),
                None,
            ),
        },
    })


@attempt_create_bp.post("/exams/<int:exam_id>/attempts")
@jwt_required()
def create_attempt(exam_id: int):
    user_id = authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "The authenticated user is invalid."}), 401

    user = db.session.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user is None:
        return jsonify({"error": "The authenticated user no longer exists."}), 401
    exam = db.session.scalar(
        select(Exam).where(Exam.id == exam_id, Exam.active.is_(True))
    )
    if exam is None:
        return jsonify({"error": "Exam not found or unavailable."}), 404

    requirements = db.session.scalars(
        select(ExamVMRequirement)
        .where(ExamVMRequirement.exam_id == exam.id)
        .order_by(ExamVMRequirement.id)
    ).all()
    main_requirements = [
        requirement for requirement in requirements if requirement.is_main
    ]
    if (
        not 1 <= len(requirements) <= 10
        or len(main_requirements) != 1
        or exam.duration_minutes < 1
        or any(requirement.template_vmid < 1 for requirement in requirements)
        or any(
            requirement.node
            and requirement.node != current_app.config["PROXMOX_NODE"]
            for requirement in requirements
        )
        or not main_requirements[0].ssh_username
    ):
        return jsonify({
            "error": "The exam must have 1 to 10 VM requirements and exactly one main VM.",
            "code": "invalid_exam_vm_requirements",
        }), 409

    provider = ProxmoxProvider(current_app.config)
    if not provider.is_api_configured:
        return jsonify({
            "error": "Exam environments are not configured on the server.",
            "code": "environment_not_configured",
        }), 503

    existing = db.session.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user_id,
            Attempt.exam_id == exam.id,
            Attempt.status.in_(("provisioning", "running")),
        )
        .order_by(Attempt.started_at.desc())
    )
    if existing is not None:
        return attempt_response(existing, exam)

    encryption_key = current_app.config.get("SSH_KEY_ENCRYPTION_KEY")
    try:
        fernet = Fernet(encryption_key.encode("ascii"))
    except (AttributeError, TypeError, UnicodeEncodeError, ValueError):
        return jsonify({
            "error": "The server SSH key-encryption secret is not configured correctly.",
            "code": "ssh_encryption_not_configured",
        }), 503

    attempt = Attempt(
        user_id=user_id,
        exam_id=exam.id,
        status="provisioning",
        started_at=now_utc_naive(),
    )
    private_key, public_key = create_attempt_ssh_key()
    attempt.ssh_private_key_encrypted = fernet.encrypt(private_key).decode("ascii")
    attempt.ssh_public_key = public_key
    db.session.add(attempt)
    db.session.flush()

    for requirement in requirements:
        db.session.add(AttemptVMInstance(
            attempt_id=attempt.id,
            requirement_id=requirement.id,
            name=requirement.name,
            template_vmid=requirement.template_vmid,
            snap_id=requirement.snap_id,
            node=requirement.node or provider.node,
            is_main=requirement.is_main,
            status="creating",
        ))
    db.session.commit()
    logger.info("Created attempt %s for exam %s", attempt.id, exam.id)
    return attempt_response(attempt, exam, 202)
