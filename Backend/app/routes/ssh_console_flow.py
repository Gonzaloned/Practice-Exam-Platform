import logging

import paramiko
from flask import request

from ..extensions import socketio
from ..services.ssh_terminal import (
    close_connection,
    get_connection,
)

logger = logging.getLogger(__name__)
TERMINAL_NAMESPACE = "/terminal"


def forward_vm_output(socket_id: str, channel: paramiko.Channel) -> None:
    while not channel.closed:
        try:
            if channel.recv_ready():
                output_data = channel.recv(4096)
                if not output_data:
                    break
                socketio.emit(
                    "terminal:data",
                    {"data": output_data.decode("utf-8", errors="replace")},
                    namespace=TERMINAL_NAMESPACE,
                    to=socket_id,
                )
            elif channel.exit_status_ready():
                break
            else:
                socketio.sleep(0.025)
        except (paramiko.SSHException, OSError) as error:
            logger.warning("SSH terminal output failed for socket %s: %s", socket_id, error)
            socketio.emit(
                "terminal:error",
                {"error": "The SSH terminal connection was interrupted."},
                namespace=TERMINAL_NAMESPACE,
                to=socket_id,
            )
            break
    closed = close_connection(socket_id)
    if closed is not None:
        socketio.emit(
            "terminal:closed",
            {"attempt_id": closed.attempt_id},
            namespace=TERMINAL_NAMESPACE,
            to=socket_id,
        )


@socketio.on("terminal:input", namespace=TERMINAL_NAMESPACE)
def send_terminal_input(data):
    connection = get_connection(request.sid)
    if connection is None or not isinstance(data, dict):
        return {"ok": False, "error": "No SSH terminal is connected."}
    value = data.get("data")
    if not isinstance(value, str) or len(value) > 8192:
        return {"ok": False, "error": "Terminal input must be text under 8 KiB."}
    try:
        connection.channel.send(value)
    except (paramiko.SSHException, OSError) as error:
        logger.warning("Could not forward SSH terminal input: %s", error)
        return {"ok": False, "error": "Could not send data to the SSH terminal."}
    return {"ok": True}


@socketio.on("terminal:resize", namespace=TERMINAL_NAMESPACE)
def resize_terminal(data):
    connection = get_connection(request.sid)
    if connection is None or not isinstance(data, dict):
        return {"ok": False, "error": "No SSH terminal is connected."}
    columns = data.get("columns")
    rows = data.get("rows")
    if (
        isinstance(columns, bool)
        or not isinstance(columns, int)
        or not 1 <= columns <= 500
        or isinstance(rows, bool)
        or not isinstance(rows, int)
        or not 1 <= rows <= 500
    ):
        return {"ok": False, "error": "Terminal dimensions must be between 1 and 500."}
    try:
        connection.channel.resize_pty(width=columns, height=rows)
    except (paramiko.SSHException, OSError) as error:
        logger.warning("Could not resize SSH terminal: %s", error)
        return {"ok": False, "error": "Could not resize the SSH terminal."}
    return {"ok": True}


@socketio.on("disconnect", namespace=TERMINAL_NAMESPACE)
def disconnect_terminal():
    close_connection(request.sid)
