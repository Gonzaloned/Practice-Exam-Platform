from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import Exam
from ..services.attempt_data import (
    attempt_response,
    authenticated_user_id,
    now_utc_naive,
    owned_attempt,
    serialize_attempt,
)
from ..services.proxmox_operations import ProxmoxProvider
from ..services.vm_environment import cleanup_attempt

set_attempt_data_bp = Blueprint("set_attempt_data", __name__)


@set_attempt_data_bp.get("/attempts/<int:attempt_id>")
@jwt_required()
def get_attempt_data(attempt_id: int):
    user_id = authenticated_user_id()
    if user_id is None:
        return jsonify({"error": "The authenticated user is invalid."}), 401
    attempt = owned_attempt(attempt_id, user_id)
    if attempt is None:
        return jsonify({"error": "Exam attempt not found."}), 404
    exam = db.session.get(Exam, attempt.exam_id)
    if exam is None:
        return jsonify({"error": "The exam definition for this attempt is missing."}), 409
    return attempt_response(attempt, exam)


@set_attempt_data_bp.post("/attempts/<int:attempt_id>/finish")
@jwt_required()
def finish_attempt(attempt_id: int):
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
        attempt.status = "completed"
        attempt.finished_at = now_utc_naive()
        db.session.commit()
    cleanup_errors = cleanup_attempt(
        attempt,
        ProxmoxProvider(current_app.config),
    )
    if cleanup_errors:
        return jsonify({
            "attempt": serialize_attempt(attempt, exam),
            "cleanup_errors": cleanup_errors,
        }), 502
    return attempt_response(attempt, exam)
