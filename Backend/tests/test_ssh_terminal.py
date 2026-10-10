import unittest
from datetime import datetime
from unittest.mock import patch

import paramiko
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db, socketio
from app.models import Attempt, AttemptVMInstance, Exam, ExamVMRequirement, User
from app.services.ssh_terminal import create_attempt_ssh_key, load_private_key


class SshTerminalSocketTests(unittest.TestCase):
    def test_attempt_ssh_key_pair_round_trips_through_paramiko(self) -> None:
        private_key, public_key = create_attempt_ssh_key()

        loaded_key = load_private_key(private_key)

        self.assertEqual(public_key, f"{loaded_key.get_name()} {loaded_key.get_base64()}")

    def setUp(self) -> None:
        self.fernet_key = Fernet.generate_key()
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-jwt-secret-that-is-long-enough",
            "SSH_KEY_ENCRYPTION_KEY": self.fernet_key.decode("ascii"),
            "PROXMOX_API_URL": "https://proxmox.example.test:8006",
            "PROXMOX_API_TOKEN_ID": "test@pve!test",
            "PROXMOX_API_TOKEN_SECRET": "test-token-secret",
            "PROXMOX_NODE": "test-node",
            "EXAM_VM_SSH_ALLOWED_CIDRS": "10.0.0.0/8",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            full_name="Terminal User",
            email="terminal@example.test",
            password_hash="not-used",
        )
        self.other_user = User(
            full_name="Other Terminal User",
            email="other-terminal@example.test",
            password_hash="not-used",
        )
        self.exam = Exam(
            slug="terminal-test",
            name="Terminal Test",
            description="SSH access test",
            duration_minutes=60,
            active=True,
        )
        db.session.add_all((self.user, self.other_user, self.exam))
        db.session.flush()
        self.requirement = ExamVMRequirement(
            exam_id=self.exam.id,
            name="main",
            template_vmid=9000,
            ssh_username="student",
            is_main=True,
        )
        db.session.add(self.requirement)
        db.session.flush()
        self.attempt = Attempt(
            user_id=self.user.id,
            exam_id=self.exam.id,
            status="running",
            started_at=datetime.utcnow(),
            ssh_private_key_encrypted=Fernet(self.fernet_key).encrypt(
                b"test-private-key"
            ).decode("ascii"),
        )
        db.session.add(self.attempt)
        db.session.flush()
        self.instance = AttemptVMInstance(
            attempt_id=self.attempt.id,
            requirement_id=self.requirement.id,
            name="main",
            template_vmid=9000,
            vm_id=5100,
            node="test-node",
            status="ready",
            ip_address="10.0.0.10",
            is_main=True,
        )
        db.session.add(self.instance)
        db.session.commit()
        self.user_token = create_access_token(identity=str(self.user.id))
        self.other_token = create_access_token(identity=str(self.other_user.id))

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_terminal_socket_rejects_attempts_owned_by_another_user(self) -> None:
        client = socketio.test_client(
            self.app,
            namespace="/terminal",
            auth={"token": self.other_token},
        )
        response = client.emit(
            "terminal:connect",
            {"attempt_id": self.attempt.id},
            namespace="/terminal",
            callback=True,
        )

        self.assertFalse(response["ok"])
        self.assertIn("not found", response["error"])
        client.disconnect(namespace="/terminal")

    def test_terminal_connects_to_ready_main_vm_with_host_key_verification(self) -> None:
        client = socketio.test_client(
            self.app,
            namespace="/terminal",
            auth={"token": self.user_token},
        )
        host_key_data = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode("ascii")
        with (
            patch("app.routes.ssh_attempt_connection.paramiko.SSHClient") as ssh_client_class,
            patch("app.routes.ssh_attempt_connection.load_private_key"),
            patch("app.routes.ssh_attempt_connection.ProxmoxProvider") as provider_class,
        ):
            ssh_client = ssh_client_class.return_value
            ssh_client.invoke_shell.return_value.closed = True
            provider_class.return_value.get_vm_ssh_host_key.return_value = (
                f"{host_key_data} guest-host-key"
            )
            response = client.emit(
                "terminal:connect",
                {"attempt_id": self.attempt.id},
                namespace="/terminal",
                callback=True,
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["vm_instance_id"], self.instance.id)
        provider_class.return_value.get_vm_ssh_host_key.assert_called_once_with(5100)
        ssh_client_class.return_value.connect.assert_called_once()
        host_key_policy = ssh_client_class.return_value.set_missing_host_key_policy.call_args.args[0]
        self.assertIsInstance(
            host_key_policy,
            paramiko.RejectPolicy,
        )
        client.disconnect(namespace="/terminal")

    def test_terminal_rejects_main_vm_outside_allowed_network(self) -> None:
        self.instance.ip_address = "192.0.2.10"
        db.session.commit()
        client = socketio.test_client(
            self.app,
            namespace="/terminal",
            auth={"token": self.user_token},
        )
        with patch("app.routes.ssh_attempt_connection.ProxmoxProvider") as provider_class:
            response = client.emit(
                "terminal:connect",
                {"attempt_id": self.attempt.id},
                namespace="/terminal",
                callback=True,
            )

        self.assertFalse(response["ok"])
        self.assertIn("outside the configured SSH network", response["error"])
        provider_class.assert_not_called()
        client.disconnect(namespace="/terminal")


if __name__ == "__main__":
    unittest.main()
