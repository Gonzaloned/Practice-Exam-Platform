import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db, socketio


class ProxmoxConsoleApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-jwt-secret-that-is-long-enough",
            "PROXMOX_API_URL": "https://proxmox.example.test:8006",
            "PROXMOX_API_TOKEN_ID": "test@pve!test",
            "PROXMOX_API_TOKEN_SECRET": "test-token-secret",
            "PROXMOX_NODE": "test-node",
            "PROXMOX_CONSOLE_ALLOWED_VMIDS": "5100",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.access_token = create_access_token(identity="1")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def configured_provider(self):
        provider_patch = patch("app.routes.proxmox_console.ProxmoxProvider")
        provider_class = provider_patch.start()
        self.addCleanup(provider_patch.stop)
        provider = provider_class.return_value
        provider.is_api_configured = True
        provider.node = "test-node"
        provider.template_vmid = 9000
        provider.allowed_console_vmids.return_value = {5100}
        provider.start_vm.return_value = "start-task"
        provider.stop_vm.return_value = None
        return provider

    def test_status_requires_authentication(self) -> None:
        response = self.client.get("/api/proxmox/status")
        self.assertEqual(response.status_code, 401)

    def test_socket_requires_a_valid_access_token(self) -> None:
        unauthenticated = socketio.test_client(
            self.app,
            namespace="/proxmox",
        )
        authenticated = socketio.test_client(
            self.app,
            namespace="/proxmox",
            auth={"token": self.access_token},
        )

        self.assertFalse(unauthenticated.is_connected("/proxmox"))
        self.assertTrue(authenticated.is_connected("/proxmox"))
        authenticated.disconnect(namespace="/proxmox")

    def test_socket_command_calls_proxmox_and_returns_ack(self) -> None:
        provider = self.configured_provider()
        provider.test_connection.return_value = {"version": "8.3"}
        client = socketio.test_client(
            self.app,
            namespace="/proxmox",
            auth={"token": self.access_token},
        )

        response = client.emit(
            "proxmox:command",
            {"command": "connect"},
            namespace="/proxmox",
            callback=True,
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["version"], {"version": "8.3"})
        provider.test_connection.assert_called_once_with()
        client.disconnect(namespace="/proxmox")

    def test_socket_start_command_uses_the_vm_allowlist(self) -> None:
        provider = self.configured_provider()
        client = socketio.test_client(
            self.app,
            namespace="/proxmox",
            auth={"token": self.access_token},
        )

        response = client.emit(
            "proxmox:command",
            {"command": "start", "vmid": 5100},
            namespace="/proxmox",
            callback=True,
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["task_id"], "start-task")
        provider.start_vm.assert_called_once_with(5100)
        client.disconnect(namespace="/proxmox")

    def test_socket_lists_vms_and_reads_status(self) -> None:
        provider = self.configured_provider()
        provider.list_vms.return_value = [{"vmid": 5100, "status": "running"}]
        provider.get_vm_status.return_value = {"status": "running"}
        client = socketio.test_client(
            self.app,
            namespace="/proxmox",
            auth={"token": self.access_token},
        )

        vm_list = client.emit(
            "proxmox:command",
            {"command": "vms"},
            namespace="/proxmox",
            callback=True,
        )
        vm_status = client.emit(
            "proxmox:command",
            {"command": "status", "vmid": 5100},
            namespace="/proxmox",
            callback=True,
        )

        self.assertEqual(vm_list["vms"], [{"vmid": 5100, "status": "running"}])
        self.assertEqual(vm_status["vm"], {"vmid": 5100, "status": "running"})
        client.disconnect(namespace="/proxmox")

    def test_status_checks_connection_and_returns_node(self) -> None:
        provider = self.configured_provider()
        provider.test_connection.return_value = {"version": "8.3"}

        response = self.client.get(
            "/api/proxmox/status",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["node"], "test-node")
        provider.test_connection.assert_called_once_with()

    def test_start_is_forwarded_only_for_allowlisted_vm(self) -> None:
        provider = self.configured_provider()

        response = self.client.post(
            "/api/proxmox/commands",
            json={"command": "start", "vmid": 5100},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["task_id"], "start-task")
        provider.start_vm.assert_called_once_with(5100)

    def test_mutation_is_rejected_for_vm_outside_allowlist(self) -> None:
        provider = self.configured_provider()

        response = self.client.post(
            "/api/proxmox/commands",
            json={"command": "stop", "vmid": 5101},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 403)
        provider.stop_vm.assert_not_called()

    def test_exam_template_cannot_be_mutated(self) -> None:
        provider = self.configured_provider()
        provider.allowed_console_vmids.return_value = {9000}

        response = self.client.post(
            "/api/proxmox/commands",
            json={"command": "start", "vmid": 9000},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 403)
        provider.start_vm.assert_not_called()

    def test_arbitrary_command_is_rejected(self) -> None:
        provider = self.configured_provider()

        response = self.client.post(
            "/api/proxmox/commands",
            json={"command": "delete", "vmid": 5100},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 400)
        provider.start_vm.assert_not_called()
        provider.stop_vm.assert_not_called()

    def test_non_string_command_is_rejected(self) -> None:
        self.configured_provider()

        response = self.client.post(
            "/api/proxmox/commands",
            json={"command": ["start"], "vmid": 5100},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
