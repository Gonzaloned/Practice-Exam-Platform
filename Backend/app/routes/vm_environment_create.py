import logging

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import Exam
from ..services.attempt_data import (
    attempt_expires_at,
    attempt_instances,
    attempt_response,
    authenticated_user_id,
    now_utc_naive,
    owned_attempt,
    serialize_attempt,
)
from ..services.proxmox import ProxmoxError, ProxmoxProvider
from ..services.vm_environment import (
    advance_attempt_environment,
    cleanup_attempt,
    expire_due_exam_attempts,
)

vm_environment_create_bp = Blueprint("vm_environment_create", __name__)
logger = logging.getLogger(__name__)


@vm_environment_create_bp.post("/attempts/<int:attempt_id>/environment")
@jwt_required()
def create_attempt_environment(attempt_id: int):
    user_id = authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "The authenticated user is invalid."}), 401
    attempt = owned_attempt(attempt_id, user_id)
    if attempt is None:
        return jsonify({"error": "Exam attempt not found."}), 404
    exam = db.session.get(Exam, attempt.exam_id)
    if exam is None:
        return jsonify({"error": "The exam definition for this attempt is missing."}), 409
    if attempt.status != "provisioning":
        return attempt_response(attempt, exam)

    provider = ProxmoxProvider(current_app.config)
    if not provider.is_api_configured:
        return jsonify({
            "error": "Exam environments are not configured on the server.",
            "code": "environment_not_configured",
        }), 503

    try:
        for instance in attempt_instances(attempt.id):
            if instance.vm_id is not None:
                continue
            vmid, task_id = provider.clone_vm(
                user_id,
                attempt.id,
                snap_id=instance.snap_id,
                template_vmid=instance.template_vmid,
                name=f"exam-{exam.id}-attempt-{attempt.id}-{instance.name}",
            )
            instance.vm_id = vmid
            instance.task_upid = task_id
            db.session.commit()
    except ProxmoxError as error:
        attempt.status = "failed"
        attempt.finished_at = now_utc_naive()
        db.session.commit()
        cleanup_errors = cleanup_attempt(attempt, provider)
        logger.error("Could not provision exam attempt %s: %s", attempt.id, error)
        payload: dict[str, object] = {
            "error": str(error),
            "code": "environment_start_failed",
            "attempt": serialize_attempt(attempt, exam),
        }
        if cleanup_errors:
            payload["cleanup_errors"] = cleanup_errors
        return jsonify(payload), 502
    return attempt_response(attempt, exam, 202)


@vm_environment_create_bp.get("/attempts/<int:attempt_id>/environment")
@jwt_required()
def get_attempt_environment(attempt_id: int):
    user_id = authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "The authenticated user is invalid."}), 401
    attempt = owned_attempt(attempt_id, user_id)
    if attempt is None:
        return jsonify({"error": "Exam attempt not found."}), 404
    exam = db.session.get(Exam, attempt.exam_id)
    if exam is None:
        return jsonify({"error": "The exam definition for this attempt is missing."}), 409

    provider = ProxmoxProvider(current_app.config)
    now = now_utc_naive()
    error_message = None
    if (
        attempt.status in {"provisioning", "running"}
        and now >= attempt_expires_at(attempt, exam)
    ):
        attempt.status = "expired"
        attempt.finished_at = now
        db.session.commit()
    elif attempt.status == "provisioning":
        if not provider.is_api_configured:
            return jsonify({
                "error": "The exam environment provider is not configured.",
                "code": "environment_not_configured",
            }), 503
        timeout = current_app.config["EXAM_ENVIRONMENT_START_TIMEOUT_SECONDS"]
        if (now - attempt.started_at).total_seconds() > timeout:
            attempt.status = "failed"
            attempt.finished_at = now
            error_message = "The exam environment did not become ready in time."
            db.session.commit()
        else:
            try:
                advance_attempt_environment(attempt, provider)
            except ProxmoxError as error:
                attempt.status = "failed"
                attempt.finished_at = now_utc_naive()
                error_message = str(error)
                db.session.commit()

    cleanup_errors: list[str] = []
    if attempt.status in {"completed", "expired", "failed"}:
        cleanup_errors = cleanup_attempt(attempt, provider)
    payload: dict[str, object] = {"attempt": serialize_attempt(attempt, exam)}
    if error_message:
        payload["error"] = error_message
    if cleanup_errors:
        payload["cleanup_errors"] = cleanup_errors
        return jsonify(payload), 502
    return jsonify(payload), 200


@vm_environment_create_bp.delete("/attempts/<int:attempt_id>/environment")
@jwt_required()
def cleanup_attempt_environment(attempt_id: int):
    user_id = authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "The authenticated user is invalid."}), 401
    attempt = owned_attempt(attempt_id, user_id)
    if attempt is None:
        return jsonify({"error": "Exam attempt not found."}), 404
    exam = db.session.get(Exam, attempt.exam_id)
    if exam is None:
        return jsonify({"error": "The exam definition for this attempt is missing."}), 409
    if attempt.status not in {"completed", "expired", "failed"}:
        return jsonify({
            "error": "Finish or expire the attempt before cleaning up its environment.",
        }), 409

    cleanup_errors = cleanup_attempt(
        attempt,
        ProxmoxProvider(current_app.config),
    )
    payload: dict[str, object] = {"attempt": serialize_attempt(attempt, exam)}
    if cleanup_errors:
        payload["cleanup_errors"] = cleanup_errors
        return jsonify(payload), 502
    return jsonify(payload), 200
