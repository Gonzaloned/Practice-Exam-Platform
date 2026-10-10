from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select

from ..extensions import db
from ..models import Attempt, AttemptVMInstance, Exam, ExamVMRequirement, Task


def now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def authenticated_user_id() -> int | None:
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        return None


def owned_attempt(attempt_id: int, user_id: int) -> Attempt | None:
    return db.session.scalar(
        select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.user_id == user_id,
        )
    )


def attempt_instances(attempt_id: int) -> list[AttemptVMInstance]:
    return db.session.scalars(
        select(AttemptVMInstance)
        .where(AttemptVMInstance.attempt_id == attempt_id)
        .order_by(AttemptVMInstance.id)
    ).all()


def attempt_expires_at(attempt: Attempt, exam: Exam) -> datetime:
    return attempt.started_at + timedelta(minutes=exam.duration_minutes)


def attempt_questions(exam_id: int) -> list[dict[str, Any]]:
    questions = db.session.scalars(
        select(Task).where(Task.exam_id == exam_id).order_by(Task.order_index, Task.id)
    ).all()
    return [
        {
            "id": question.id,
            "title": question.title,
            "description": question.description,
            "points": question.points,
            "order_index": question.order_index,
        }
        for question in questions
    ]


def serialize_attempt(attempt: Attempt, exam: Exam) -> dict[str, Any]:
    instances = attempt_instances(attempt.id)
    main_instance = next(
        (instance for instance in instances if instance.is_main),
        None,
    )
    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "exam_slug": exam.slug or "",
        "exam_name": exam.name,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat() + "Z",
        "expires_at": attempt_expires_at(attempt, exam).isoformat() + "Z",
        "finished_at": (
            attempt.finished_at.isoformat() + "Z" if attempt.finished_at else None
        ),
        "questions": attempt_questions(exam.id),
        "environment": main_instance.to_dict() if main_instance else None,
        "vm_instances": [instance.to_dict() for instance in instances],
    }


def attempt_response(
    attempt: Attempt,
    exam: Exam,
    status_code: int = 200,
):
    return jsonify({"attempt": serialize_attempt(attempt, exam)}), status_code


def ensure_examtry_exam() -> Exam:
    exam = db.session.scalar(select(Exam).where(Exam.slug == "examtry"))
    if exam is None:
        exam = Exam(
            slug="examtry",
            name="ExamTry",
            description="Practice the SSH terminal exam environment.",
            duration_minutes=current_app.config["EXAM_SESSION_HOURS"] * 60,
            active=True,
        )
        db.session.add(exam)
        db.session.flush()

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
                snap_id="901",
                node=current_app.config["PROXMOX_NODE"],
                ssh_username=current_app.config["EXAM_VM_SSH_USERNAME"],
                is_main=True,
            ))
    return exam
