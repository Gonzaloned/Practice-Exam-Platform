import base64
import ipaddress
import logging
from datetime import timedelta

import paramiko
from cryptography.fernet import Fernet, InvalidToken
from flask import Blueprint, current_app, request, session
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from sqlalchemy import select

from ..extensions import db, socketio
from ..models import Attempt, AttemptVMInstance, Exam, ExamVMRequirement
from ..services.attempt_data import now_utc_naive
from ..services.proxmox import ProxmoxError, ProxmoxProvider
from ..services.ssh_terminal import (
    TerminalConnection,
    close_connection,
    load_private_key,
    register_connection,
)
from .ssh_console_flow import forward_vm_output

ssh_attempt_connection_bp = Blueprint("ssh_attempt_connection", __name__)
logger = logging.getLogger(__name__)
TERMINAL_NAMESPACE = "/terminal"


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _ssh_target_is_allowed(address: str) -> bool:
    configured_cidrs = current_app.config.get("EXAM_VM_SSH_ALLOWED_CIDRS", "")
    if not isinstance(configured_cidrs, str):
        logger.error("EXAM_VM_SSH_ALLOWED_CIDRS must be a comma-separated string")
        return False
    try:
        target = ipaddress.ip_address(address)
        networks = [
            ipaddress.ip_network(cidr.strip(), strict=False)
            for cidr in configured_cidrs.split(",")
            if cidr.strip()
        ]
    except ValueError:
        logger.error("Invalid SSH target IP or EXAM_VM_SSH_ALLOWED_CIDRS configuration")
        return False
    return (
        bool(networks)
        and not target.is_loopback
        and not target.is_link_local
        and not target.is_multicast
        and not target.is_unspecified
        and any(target in network for network in networks)
    )


@socketio.on("connect", namespace=TERMINAL_NAMESPACE)
def authenticate_terminal_socket(auth):
    if not isinstance(auth, dict) or not isinstance(auth.get("token"), str):
        return False
    try:
        claims = decode_token(auth["token"])
    except JWTExtendedException:
        return False
    if claims.get("type") != "access":
        return False
    try:
        user_id = int(claims.get("sub"))
    except (TypeError, ValueError):
        return False
    if user_id < 1:
        return False
    session["terminal_user_id"] = user_id
    return True


@socketio.on("terminal:connect", namespace=TERMINAL_NAMESPACE)
def connect_terminal(data):
    if not isinstance(data, dict):
        return {"ok": False, "error": "Send terminal connection data."}
    attempt_id = _positive_int(data.get("attempt_id"))
    if attempt_id is None:
        return {"ok": False, "error": "Provide a valid attempt ID."}

    user_id = session.get("terminal_user_id")
    if not isinstance(user_id, int):
        return {"ok": False, "error": "The terminal socket is not authenticated."}
    attempt = db.session.scalar(
        select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.user_id == user_id,
            Attempt.status == "running",
        )
    )
    if attempt is None:
        return {"ok": False, "error": "A running exam attempt was not found."}

    instance = db.session.scalar(
        select(AttemptVMInstance).where(
            AttemptVMInstance.attempt_id == attempt.id,
            AttemptVMInstance.is_main.is_(True),
        )
    )
    if (
        instance is None
        or instance.status != "ready"
        or instance.vm_id is None
        or not instance.ip_address
    ):
        return {"ok": False, "error": "The main exam VM is not ready for SSH."}
    if not _ssh_target_is_allowed(instance.ip_address):
        return {
            "ok": False,
            "error": "The main VM IP is outside the configured SSH network.",
        }

    requirement = db.session.get(ExamVMRequirement, instance.requirement_id)
    if requirement is None or not requirement.ssh_username:
        return {"ok": False, "error": "The main VM SSH username is not configured."}
    exam = db.session.get(Exam, attempt.exam_id)
    if exam is None:
        return {"ok": False, "error": "The exam definition is unavailable."}

    private_key_ciphertext = attempt.ssh_private_key_encrypted
    encryption_key = current_app.config.get("SSH_KEY_ENCRYPTION_KEY")
    if not private_key_ciphertext or not encryption_key:
        return {"ok": False, "error": "The attempt SSH credentials are unavailable."}
    try:
        private_key = Fernet(encryption_key.encode("ascii")).decrypt(
            private_key_ciphertext.encode("ascii")
        )
    except (AttributeError, TypeError, UnicodeEncodeError, ValueError, InvalidToken):
        logger.exception("Could not decrypt SSH credentials for attempt %s", attempt.id)
        return {"ok": False, "error": "The attempt SSH credentials could not be read."}

    if now_utc_naive() >= attempt.started_at + timedelta(minutes=exam.duration_minutes):
        return {"ok": False, "error": "The exam attempt has expired."}

    client = paramiko.SSHClient()
    provider = ProxmoxProvider(current_app.config)
    try:
        host_key_line = provider.get_vm_ssh_host_key(instance.vm_id)
        key_type, encoded_key, *_ = host_key_line.split()
        if key_type != "ssh-ed25519":
            raise ProxmoxError("The guest agent returned an unsupported SSH host key.")
        host_key = paramiko.Ed25519Key(
            data=base64.b64decode(encoded_key, validate=True)
        )
    except (ProxmoxError, TypeError, ValueError, paramiko.SSHException) as error:
        logger.error(
            "Could not verify the SSH host key for attempt %s: %s",
            attempt.id,
            error,
        )
        return {"ok": False, "error": "Could not verify the main VM SSH host key."}

    client.get_host_keys().add(instance.ip_address, host_key.get_name(), host_key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    close_connection(request.sid)
    try:
        client.connect(
            hostname=instance.ip_address,
            port=current_app.config["SSH_PORT"],
            username=requirement.ssh_username,
            pkey=load_private_key(private_key),
            timeout=current_app.config["SSH_CONNECT_TIMEOUT_SECONDS"],
            banner_timeout=current_app.config["SSH_CONNECT_TIMEOUT_SECONDS"],
            auth_timeout=current_app.config["SSH_CONNECT_TIMEOUT_SECONDS"],
            allow_agent=False,
            look_for_keys=False,
        )
        channel = client.invoke_shell(term="xterm-256color", width=80, height=24)
    except (paramiko.SSHException, OSError) as error:
        client.close()
        logger.warning(
            "SSH connection to main VM %s for attempt %s failed: %s",
            instance.vm_id,
            attempt.id,
            error,
        )
        return {"ok": False, "error": "Could not open an SSH terminal to the main VM."}

    connection = TerminalConnection(attempt.id, client, channel)
    register_connection(request.sid, connection)
    socketio.start_background_task(forward_vm_output, request.sid, channel)
    return {
        "ok": True,
        "attempt_id": attempt.id,
        "vm_instance_id": instance.id,
        "vm_name": instance.name,
    }
