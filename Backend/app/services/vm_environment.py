import logging
from datetime import timedelta

from sqlalchemy import and_, exists, or_, select

from flask import current_app

from ..extensions import db
from ..models import Attempt, AttemptVMInstance, Exam, Lab
from .attempt_data import attempt_expires_at, attempt_instances, now_utc_naive
from .proxmox import ProxmoxError, ProxmoxProvider
from .ssh_terminal import close_attempt_connections

logger = logging.getLogger(__name__)


def cleanup_instance(
    instance: AttemptVMInstance | Lab,
    provider: ProxmoxProvider,
) -> str | None:
    if instance.status == "stopped":
        return None
    if instance.vm_id is None:
        instance.status = "stopped"
        instance.destroyed_at = now_utc_naive()
        db.session.commit()
        return None

    try:
        if instance.task_upid:
            if not provider.task_is_complete(instance.task_upid):
                return None
            instance.task_upid = None
            if instance.status == "stopping":
                instance.status = "deleting"
            elif instance.status == "deleting":
                instance.status = "stopped"
                instance.destroyed_at = now_utc_naive()
                db.session.commit()
                return None
            db.session.commit()

        if instance.status != "deleting":
            instance.status = "stopping"
            db.session.commit()
            stop_task = provider.stop_vm(instance.vm_id)
            if stop_task:
                instance.task_upid = stop_task
                db.session.commit()
                return None
            instance.status = "deleting"
            db.session.commit()

        delete_task = provider.delete_vm(instance.vm_id)
        if delete_task:
            instance.task_upid = delete_task
            db.session.commit()
            return None
    except ProxmoxError as error:
        instance.status = "failed"
        instance.task_upid = None
        db.session.commit()
        logger.exception(
            "Could not clean up VM %s for attempt %s",
            instance.vm_id,
            instance.attempt_id,
        )
        return str(error)

    instance.status = "stopped"
    instance.task_upid = None
    instance.destroyed_at = now_utc_naive()
    db.session.commit()
    return None


def cleanup_attempt(
    attempt: Attempt,
    provider: ProxmoxProvider,
) -> list[str]:
    close_attempt_connections(attempt.id)
    instances = attempt_instances(attempt.id)
    errors = []
    for instance in instances:
        error = cleanup_instance(instance, provider)
        if error:
            errors.append(f"{instance.name}: {error}")
    if instances and all(instance.status == "stopped" for instance in instances):
        attempt.ssh_private_key_encrypted = None
        attempt.ssh_public_key = None
        db.session.commit()
    return errors


def advance_instance(
    instance: AttemptVMInstance,
    attempt: Attempt,
    provider: ProxmoxProvider,
) -> None:
    if instance.status in {"ready", "stopped", "failed"} or instance.vm_id is None:
        return
    if instance.task_upid:
        if not provider.task_is_complete(instance.task_upid):
            return
        instance.task_upid = None
        db.session.commit()

    if instance.status == "creating":
        if instance.is_main:
            if not attempt.ssh_public_key:
                raise ProxmoxError("The attempt SSH public key is missing.")
            provider.configure_vm_ssh_key(instance.vm_id, attempt.ssh_public_key)
        instance.status = "starting"
        db.session.commit()

    if instance.status != "starting":
        return
    if not provider.is_vm_running(instance.vm_id):
        instance.task_upid = provider.start_vm(instance.vm_id)
        db.session.commit()
        return
    if provider.is_vm_ready(instance.vm_id):
        instance.ip_address = provider.get_vm_ipv4(instance.vm_id)
        instance.status = "ready"
        db.session.commit()


def advance_attempt_environment(
    attempt: Attempt,
    provider: ProxmoxProvider,
) -> None:
    if attempt.status != "provisioning":
        return
    for instance in attempt_instances(attempt.id):
        advance_instance(instance, attempt, provider)
    instances = attempt_instances(attempt.id)
    if instances and all(instance.status == "ready" for instance in instances):
        attempt.status = "running"
        db.session.commit()


def expire_due_exam_attempts() -> int:
    now = now_utc_naive()
    attempts = db.session.scalars(
        select(Attempt)
        .join(Exam, Exam.id == Attempt.exam_id)
        .where(
            or_(
                Attempt.status.in_(("provisioning", "running")),
                and_(
                    Attempt.status.in_(("completed", "expired", "failed")),
                    exists(
                        select(AttemptVMInstance.id).where(
                            AttemptVMInstance.attempt_id == Attempt.id,
                            AttemptVMInstance.status != "stopped",
                        )
                    ),
                ),
            )
        )
    ).all()
    provider = ProxmoxProvider(current_app.config)
    cleaned_count = 0
    for attempt in attempts:
        exam = db.session.get(Exam, attempt.exam_id)
        if exam is None:
            continue
        if (
            attempt.status in {"provisioning", "running"}
            and now >= attempt_expires_at(attempt, exam)
        ):
            attempt.status = "expired"
            attempt.finished_at = now
            db.session.commit()
        if attempt.status not in {"completed", "expired", "failed"}:
            continue
        instances = attempt_instances(attempt.id)
        if not instances or all(instance.status == "stopped" for instance in instances):
            continue
        cleanup_attempt(attempt, provider)
        cleaned_count += 1

    legacy_attempts = db.session.scalars(
        select(Attempt)
        .join(Lab, Lab.attempt_id == Attempt.id)
        .where(
            or_(
                Attempt.status.in_(("provisioning", "running")),
                Lab.status.in_((
                    "creating",
                    "starting",
                    "ready",
                    "stopping",
                    "deleting",
                    "failed",
                )),
            )
        )
    ).all()
    legacy_expiration = timedelta(
        hours=current_app.config["EXAM_SESSION_HOURS"]
    )
    for attempt in legacy_attempts:
        lab = db.session.scalar(select(Lab).where(Lab.attempt_id == attempt.id))
        if lab is None:
            continue
        if (
            attempt.status in {"provisioning", "running"}
            and now >= attempt.started_at + legacy_expiration
        ):
            attempt.status = "expired"
            attempt.finished_at = now
            db.session.commit()
        if (
            attempt.status in {"completed", "expired", "failed"}
            and lab.status != "stopped"
        ):
            close_attempt_connections(attempt.id)
            cleanup_instance(lab, provider)
            cleaned_count += 1
    return cleaned_count
