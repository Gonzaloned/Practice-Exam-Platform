import threading
from dataclasses import dataclass
from io import StringIO

import paramiko
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def create_attempt_ssh_key() -> tuple[bytes, str]:
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode("ascii")
    return private_bytes, public_key


@dataclass
class TerminalConnection:
    attempt_id: int
    client: paramiko.SSHClient
    channel: paramiko.Channel


_connections: dict[str, TerminalConnection] = {}
_connections_lock = threading.Lock()


def register_connection(socket_id: str, connection: TerminalConnection) -> None:
    with _connections_lock:
        _connections[socket_id] = connection


def get_connection(socket_id: str) -> TerminalConnection | None:
    with _connections_lock:
        return _connections.get(socket_id)


def close_connection(socket_id: str) -> TerminalConnection | None:
    with _connections_lock:
        connection = _connections.pop(socket_id, None)
    if connection is not None:
        connection.channel.close()
        connection.client.close()
    return connection


def close_attempt_connections(attempt_id: int) -> list[str]:
    with _connections_lock:
        socket_ids = [
            socket_id
            for socket_id, connection in _connections.items()
            if connection.attempt_id == attempt_id
        ]
    for socket_id in socket_ids:
        close_connection(socket_id)
    return socket_ids


def load_private_key(private_key_bytes: bytes) -> paramiko.Ed25519Key:
    return paramiko.Ed25519Key.from_private_key(
        StringIO(private_key_bytes.decode("ascii"))
    )
