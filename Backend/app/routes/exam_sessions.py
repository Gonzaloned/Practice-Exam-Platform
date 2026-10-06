from datetime import datetime, timedelta, timezone
import logging

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_, select

from ..extensions import db
from ..models import Attempt, Exam, Lab, User
from ..services.proxmox import ProxmoxError, ProxmoxProvider

exam_sessions_bp = Blueprint("exam_sessions", __name__)
logger = logging.getLogger(__name__)

LFCS_SLUG = "lfcs"
LFCS_NAME = "Linux Foundation Certified System Administrator"


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _provider() -> ProxmoxProvider:
    return ProxmoxProvider(current_app.config)


def _serialize(attempt: Attempt, lab: Lab | None) -> dict[str, object]:
    expires_at = attempt.started_at + timedelta(
        hours=current_app.config["EXAM_SESSION_HOURS"]
    )
    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "finished_at": (
            attempt.finished_at.isoformat() + "Z"
            if attempt.finished_at
            else None
        ),
        "environment": lab.to_dict() if lab else None,
    }


def _session_response(attempt: Attempt, lab: Lab | None, status_code: int = 200):
    return jsonify({"session": _serialize(attempt, lab)}), status_code


def _get_owned_attempt(attempt_id: int) -> Attempt | None:
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.scalar(
        select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.user_id == user_id,
        )
    )


def _get_lab(attempt_id: int) -> Lab | None:
    return db.session.scalar(select(Lab).where(Lab.attempt_id == attempt_id))


def _cleanup_environment(
    lab: Lab | None,
    provider: ProxmoxProvider,
) -> str | None:
    if lab is None or lab.status == "stopped":
        return None
    if lab.vm_id is None:
        lab.status = "stopped"
        db.session.commit()
        return None

    try:
        if lab.status == "failed":
            lab.status = "stopping"
            lab.task_upid = None
            db.session.commit()

        if lab.task_upid:
            if not provider.task_is_complete(lab.task_upid):
                return None
            lab.task_upid = None
            if lab.status == "stopping":
                lab.status = "deleting"
            elif lab.status == "deleting":
                lab.status = "stopped"
                lab.destroyed_at = _now_utc_naive()
                db.session.commit()
                return None
            db.session.commit()

        if lab.status != "deleting":
            lab.status = "stopping"
            db.session.commit()
            stop_task = provider.stop_vm(lab.vm_id)
            if stop_task:
                lab.task_upid = stop_task
                db.session.commit()
                return None
            lab.status = "deleting"
            db.session.commit()

        delete_task = provider.delete_vm(lab.vm_id)
        if delete_task:
            lab.task_upid = delete_task
            db.session.commit()
            return None
    except ProxmoxError as error:
        lab.status = "failed"
        lab.task_upid = None
        db.session.commit()
        logger.exception("Could not clean up exam environment %s", lab.vm_id)
        return str(error)

    lab.status = "stopped"
    lab.task_upid = None
    lab.destroyed_at = _now_utc_naive()
    db.session.commit()
    return None


def _finish_expired(
    attempt: Attempt,
    lab: Lab | None,
    provider: ProxmoxProvider,
) -> str | None:
    attempt.status = "expired"
    attempt.finished_at = _now_utc_naive()
    db.session.commit()
    return _cleanup_environment(lab, provider)


def _fail_attempt(
    attempt: Attempt,
    lab: Lab,
    provider: ProxmoxProvider,
    message: str,
) -> str | None:
    attempt.status = "failed"
    attempt.finished_at = _now_utc_naive()
    lab.status = "failed"
    db.session.commit()
    cleanup_error = _cleanup_environment(lab, provider)
    logger.error("Exam attempt %s failed: %s", attempt.id, message)
    return cleanup_error


def _advance_provisioning(
    attempt: Attempt,
    lab: Lab,
    provider: ProxmoxProvider,
) -> None:
    if attempt.status != "provisioning" or lab.vm_id is None:
        return

    if lab.task_upid:
        if not provider.task_is_complete(lab.task_upid):
            return
        lab.task_upid = None
        db.session.commit()

    if lab.status == "creating":
        lab.status = "starting"
        db.session.commit()

    if lab.status != "starting":
        return

    if not provider.is_vm_running(lab.vm_id):
        lab.task_upid = provider.start_vm(lab.vm_id)
        db.session.commit()
        return

    if provider.is_vm_ready(lab.vm_id):
        lab.status = "ready"
        attempt.status = "running"
        db.session.commit()


def expire_due_exam_sessions() -> int:
    now = _now_utc_naive()
    attempts = db.session.scalars(
        select(Attempt)
        .outerjoin(Lab, Lab.attempt_id == Attempt.id)
        .where(or_(
            Attempt.status.in_(("provisioning", "running")),
            Lab.status.in_((
                "creating",
                "starting",
                "ready",
                "stopping",
                "deleting",
                "failed",
            )),
        ))
    ).all()
    provider = _provider()
    processed_count = 0

    for attempt in attempts:
        lab = _get_lab(attempt.id)
        if attempt.status not in {"provisioning", "running"}:
            if lab is not None and lab.vm_id is not None and lab.status != "stopped":
                if _cleanup_environment(lab, provider) is None and lab.status == "stopped":
                    processed_count += 1
            continue

        expires_at = attempt.started_at + timedelta(
            hours=current_app.config["EXAM_SESSION_HOURS"]
        )
        if now < expires_at:
            if attempt.status == "provisioning" and provider.is_configured:
                lab = _get_lab(attempt.id)
                if lab is not None:
                    try:
                        _advance_provisioning(attempt, lab, provider)
                    except ProxmoxError as error:
                        _fail_attempt(attempt, lab, provider, str(error))
            continue
        _finish_expired(attempt, lab, provider)
        processed_count += 1

    return processed_count


def _ensure_catalog_exam() -> Exam:
    exam = db.session.scalar(select(Exam).where(Exam.name == LFCS_NAME))
    if exam is None:
        exam = Exam(
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
    return exam


@exam_sessions_bp.post("/sessions")
@jwt_required()
def start_session():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("exam_slug") != LFCS_SLUG:
        return jsonify({"error": "Choose an available exam to start."}), 400

    provider = _provider()
    if not provider.is_configured:
        return jsonify({
            "error": "Exam environments are not configured on the server.",
            "code": "environment_not_configured",
        }), 503

    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "The authenticated user is invalid."}), 401

    user = db.session.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user is None:
        return jsonify({"error": "The authenticated user no longer exists."}), 401

    exam = _ensure_catalog_exam()
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
        existing_lab = _get_lab(existing.id)
        expiration = existing.started_at + timedelta(
            hours=current_app.config["EXAM_SESSION_HOURS"]
        )
        if _now_utc_naive() >= expiration:
            cleanup_error = _finish_expired(existing, existing_lab, provider)
            payload: dict[str, object] = {
                "session": _serialize(existing, existing_lab)
            }
            if cleanup_error:
                payload["cleanup_error"] = cleanup_error
            return jsonify(payload), 200
        return _session_response(existing, existing_lab, 200)

    attempt = Attempt(
        user_id=user_id,
        exam_id=exam.id,
        status="provisioning",
        started_at=_now_utc_naive(),
    )
    db.session.add(attempt)
    db.session.flush()

    lab = Lab(
        attempt_id=attempt.id,
        provider="proxmox",
        node=current_app.config["PROXMOX_NODE"],
        status="creating",
    )
    db.session.add(lab)
    db.session.commit()

    try:
        vmid, clone_task = provider.clone_vm(user_id, attempt.id)
        lab.vm_id = vmid
        lab.task_upid = clone_task
        db.session.commit()
    except ProxmoxError as error:
        cleanup_error = _fail_attempt(attempt, lab, provider, str(error))
        result = {
            "error": str(error),
            "code": "environment_start_failed",
            "session": _serialize(attempt, lab),
        }
        if cleanup_error:
            result["cleanup_error"] = cleanup_error
        return jsonify(result), 502

    return _session_response(attempt, lab, 202)


@exam_sessions_bp.get("/sessions/<int:attempt_id>")
@jwt_required()
def get_session(attempt_id: int):
    attempt = _get_owned_attempt(attempt_id)
    if attempt is None:
        return jsonify({"error": "Exam session not found."}), 404

    lab = _get_lab(attempt.id)
    provider = _provider()
    if attempt.status in {"completed", "expired", "failed"}:
        cleanup_error = None
        if lab is not None and lab.vm_id is not None and lab.status != "stopped":
            cleanup_error = _cleanup_environment(lab, provider)
        payload: dict[str, object] = {"session": _serialize(attempt, lab)}
        if cleanup_error:
            payload["cleanup_error"] = cleanup_error
        return jsonify(payload), 200

    expires_at = attempt.started_at + timedelta(
        hours=current_app.config["EXAM_SESSION_HOURS"]
    )
    if _now_utc_naive() >= expires_at:
        cleanup_error = _finish_expired(attempt, lab, provider)
        payload: dict[str, object] = {"session": _serialize(attempt, lab)}
        if cleanup_error:
            payload["cleanup_error"] = cleanup_error
        return jsonify(payload), 200

    if lab is None:
        return jsonify({
            "error": "The exam environment is not available.",
            "code": "environment_unavailable",
        }), 503

    startup_timeout = current_app.config["EXAM_ENVIRONMENT_START_TIMEOUT_SECONDS"]
    if (
        attempt.status == "provisioning"
        and (_now_utc_naive() - attempt.started_at).total_seconds() > startup_timeout
    ):
        attempt.status = "failed"
        attempt.finished_at = _now_utc_naive()
        lab.status = "failed"
        db.session.commit()
        cleanup_error = _cleanup_environment(lab, provider)
        payload: dict[str, object] = {"session": _serialize(attempt, lab)}
        payload["error"] = "The exam environment did not become ready in time."
        if cleanup_error:
            payload["cleanup_error"] = cleanup_error
        return jsonify(payload), 200

    if lab.vm_id is None:
        return _session_response(attempt, lab, 202)
    if not provider.is_configured:
        return jsonify({
            "error": "The exam environment provider is not configured.",
            "code": "environment_not_configured",
        }), 503

    try:
        _advance_provisioning(attempt, lab, provider)
    except ProxmoxError as error:
        cleanup_error = _fail_attempt(attempt, lab, provider, str(error))
        payload: dict[str, object] = {
            "session": _serialize(attempt, lab),
            "error": str(error),
        }
        if cleanup_error:
            payload["cleanup_error"] = cleanup_error
        return jsonify(payload), 502

    return _session_response(attempt, lab)


@exam_sessions_bp.post("/sessions/<int:attempt_id>/finish")
@jwt_required()
def finish_session(attempt_id: int):
    attempt = _get_owned_attempt(attempt_id)
    if attempt is None:
        return jsonify({"error": "Exam session not found."}), 404

    lab = _get_lab(attempt.id)
    if attempt.status in {"completed", "expired", "failed"}:
        cleanup_error = None
        if lab is not None and lab.vm_id is not None and lab.status != "stopped":
            cleanup_error = _cleanup_environment(lab, _provider())
        payload: dict[str, object] = {"session": _serialize(attempt, lab)}
        if cleanup_error:
            payload["cleanup_error"] = cleanup_error
            return jsonify(payload), 502
        return jsonify(payload), 200

    attempt.status = "completed"
    attempt.finished_at = _now_utc_naive()
    db.session.commit()

    cleanup_error = _cleanup_environment(lab, _provider())
    payload: dict[str, object] = {"session": _serialize(attempt, lab)}
    if cleanup_error:
        payload["cleanup_error"] = cleanup_error
        return jsonify(payload), 502
    return jsonify(payload), 200
