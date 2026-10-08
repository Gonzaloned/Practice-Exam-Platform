import logging

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import decode_token, jwt_required
from flask_jwt_extended.exceptions import JWTExtendedException

from ..extensions import socketio
from ..services.proxmox import ProxmoxError, ProxmoxProvider

proxmox_console_bp = Blueprint("proxmox_console", __name__)
logger = logging.getLogger(__name__)


def _provider() -> ProxmoxProvider:
    return ProxmoxProvider(current_app.config)


def _configured_provider():
    provider = _provider()
    if not provider.is_api_configured:
        return None, (jsonify({
            "error": "The Proxmox API is not configured on the server.",
            "code": "proxmox_not_configured",
        }), 503)
    return provider, None


def _start_or_stop(provider: ProxmoxProvider, command: str, vmid: int):
    if vmid == provider.template_vmid:
        return {
            "error": "The configured exam template cannot be started or stopped here.",
            "code": "template_vm_protected",
        }, 403

    try:
        allowed_vmids = provider.allowed_console_vmids()
    except ProxmoxError as error:
        logger.error("The Proxmox console allowlist is invalid.")
        return {"error": str(error), "code": "invalid_vm_allowlist"}, 503
    if vmid not in allowed_vmids:
        return {
            "error": "This VM is not enabled for console start/stop commands.",
            "code": "vm_not_allowlisted",
        }, 403

    try:
        task_id = (
            provider.start_vm(vmid)
            if command == "start"
            else provider.stop_vm(vmid)
        )
    except ProxmoxError as error:
        logger.warning("Proxmox VM %s command %s failed: %s", vmid, command, error)
        status_code = 404 if error.status_code == 404 else 502
        return {"error": str(error), "code": "proxmox_request_failed"}, status_code

    return {
        "command": command,
        "vmid": vmid,
        "task_id": task_id,
        "message": (
            f"VM {vmid} start request accepted."
            if command == "start"
            else (
                f"VM {vmid} stop request accepted."
                if task_id
                else f"VM {vmid} is already stopped."
            )
        ),
    }, 202 if task_id else 200


@proxmox_console_bp.get("/status")
#@jwt_required()
def get_connection_status():
    provider, error_response = _configured_provider()
    if error_response:
        return error_response
    try:
        version = provider.test_connection()
    except ProxmoxError as error:
        logger.warning("Proxmox connection test failed: %s", error)
        return jsonify({"error": str(error), "code": "proxmox_unavailable"}), 502
    return jsonify({"connected": True, "node": provider.node, "version": version})


@proxmox_console_bp.get("/vms")
@jwt_required()
def list_vms():
    provider, error_response = _configured_provider()
    if error_response:
        return error_response
    try:
        vms = provider.list_vms()
    except ProxmoxError as error:
        logger.warning("Could not list Proxmox VMs: %s", error)
        return jsonify({"error": str(error), "code": "proxmox_request_failed"}), 502
    return jsonify({"node": provider.node, "vms": vms})


@proxmox_console_bp.get("/vms/<int:vmid>")
@jwt_required()
def get_vm_status(vmid: int):
    provider, error_response = _configured_provider()
    if error_response:
        return error_response
    try:
        status = provider.get_vm_status(vmid)
    except ProxmoxError as error:
        logger.warning("Could not get status for Proxmox VM %s: %s", vmid, error)
        status_code = 404 if error.status_code == 404 else 502
        return jsonify({"error": str(error), "code": "proxmox_request_failed"}), status_code
    return jsonify({"node": provider.node, "vm": {"vmid": vmid, **status}})


@proxmox_console_bp.post("/commands")
@jwt_required()
def run_command():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON command and VM ID."}), 400

    command = data.get("command")
    vmid = data.get("vmid")
    if not isinstance(command, str) or command not in {"start", "stop"}:
        return jsonify({"error": "Supported commands are start and stop."}), 400
    if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
        return jsonify({"error": "Provide a valid VM ID."}), 400

    provider, error_response = _configured_provider()
    if error_response:
        return error_response

    result, status_code = _start_or_stop(provider, command, vmid)
    return jsonify(result), status_code


@socketio.on("connect", namespace="/proxmox")
def authenticate_proxmox_socket(auth):
    if not isinstance(auth, dict) or not isinstance(auth.get("token"), str):
        return False

    try:
        claims = decode_token(auth["token"])
    except JWTExtendedException:
        return False

    if claims.get("type") != "access" or not claims.get("sub"):
        return False
    return True


@socketio.on("proxmox:command", namespace="/proxmox")
def handle_proxmox_socket_command(data):
    if not isinstance(data, dict):
        return {
            "ok": False,
            "status": 400,
            "error": "Send a command object.",
        }

    command = data.get("command")
    if not isinstance(command, str) or command not in {
        "connect",
        "vms",
        "status",
        "start",
        "stop",
    }:
        return {
            "ok": False,
            "status": 400,
            "error": "Supported commands are connect, vms, status, start, and stop.",
        }

    vmid = data.get("vmid")
    if command in {"status", "start", "stop"} and (
        isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1
    ):
        return {
            "ok": False,
            "status": 400,
            "error": f"Provide a valid VM ID for {command}.",
        }

    provider, error_response = _configured_provider()
    if error_response:
        error_payload = error_response[0].get_json()
        return {
            "ok": False,
            "status": error_response[1],
            **error_payload,
        }

    try:
        if command == "connect":
            result = {
                "connected": True,
                "node": provider.node,
                "version": provider.test_connection(),
            }
            status_code = 200
        elif command == "vms":
            result = {"node": provider.node, "vms": provider.list_vms()}
            status_code = 200
        elif command == "status":
            result = {
                "node": provider.node,
                "vm": {"vmid": vmid, **provider.get_vm_status(vmid)},
            }
            status_code = 200
        else:
            result, status_code = _start_or_stop(provider, command, vmid)
    except ProxmoxError as error:
        logger.warning("Proxmox console command %s failed: %s", command, error)
        status_code = 404 if error.status_code == 404 else 502
        result = {"error": str(error), "code": "proxmox_request_failed"}

    return {
        "ok": status_code < 400,
        "status": status_code,
        **result,
    }
