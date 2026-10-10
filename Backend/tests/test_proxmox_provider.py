import base64
import unittest
from unittest.mock import call, patch

from app.services.proxmox import ProxmoxProvider


class ProxmoxProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = ProxmoxProvider({
            "PROXMOX_API_URL": "https://proxmox.example.test:8006",
            "PROXMOX_API_TOKEN_ID": "test@pve!test",
            "PROXMOX_API_TOKEN_SECRET": "test-token-secret",
            "PROXMOX_NODE": "test-node",
            "PROXMOX_TEMPLATE_VMID": "9000",
        })

    def test_clone_uses_requirement_template_and_snapshot(self) -> None:
        with patch.object(
            self.provider,
            "_request",
            side_effect=(5100, "clone-task"),
        ) as request:
            result = self.provider.clone_vm(
                user_id=5,
                attempt_id=12,
                snap_id="ubuntu-base",
                template_vmid=9100,
                name="exam-2-attempt-12-main",
            )

        self.assertEqual(result, (5100, "clone-task"))
        request.assert_has_calls((
            call("GET", "/cluster/nextid"),
            call(
                "POST",
                "/nodes/test-node/qemu/9100/clone",
                {
                    "newid": 5100,
                    "name": "exam-2-attempt-12-main",
                    "full": 1,
                    "snapname": "ubuntu-base",
                },
            ),
        ))

    def test_guest_agent_host_key_file_is_read_and_closed(self) -> None:
        host_key = "ssh-ed25519 " + base64.b64encode(b"public-key-bytes").decode()
        with patch.object(
            self.provider,
            "_request",
            side_effect=(
                {"handle": 42},
                {"count": len(host_key), "data": base64.b64encode(host_key.encode()).decode()},
                None,
            ),
        ) as request:
            result = self.provider.get_vm_ssh_host_key(5100)

        self.assertEqual(result, host_key)
        self.assertEqual(request.call_args_list[0].args[2], {
            "file": "/etc/ssh/ssh_host_ed25519_key.pub",
        })
        self.assertEqual(request.call_args_list[2].args[2], {"handle": 42})

    def test_connection_check_uses_service_provider(self) -> None:
        with patch.object(
            self.provider,
            "_request",
            side_effect=(
                {
                    "version": "8.3",
                    "release": "8.3.0",
                    "repository": "test-repo",
                    "ignored": "value",
                },
                {"status": "ok"},
            ),
        ) as request:
            result = self.provider.test_connection()

        self.assertEqual(result, {
            "version": "8.3",
            "release": "8.3.0",
            "repository": "test-repo",
        })
        request.assert_has_calls((
            call("GET", "/version"),
            call("GET", "/nodes/test-node/status"),
        ))

    def test_vm_inventory_is_loaded_by_service_provider(self) -> None:
        with patch.object(
            self.provider,
            "_request",
            return_value=[
                {"vmid": 5100, "name": "exam-vm", "status": "running", "uptime": 12},
                {"vmid": 5101, "name": "unused", "status": "stopped", "extra": True},
                "invalid",
            ],
        ) as request:
            result = self.provider.list_vms()

        self.assertEqual(result, [
            {"vmid": 5100, "name": "exam-vm", "status": "running", "uptime": 12},
            {"vmid": 5101, "name": "unused", "status": "stopped"},
        ])
        request.assert_called_once_with("GET", "/nodes/test-node/qemu")

    def test_vm_status_is_loaded_by_service_provider(self) -> None:
        with patch.object(
            self.provider,
            "_request",
            return_value={
                "status": "running",
                "qmpstatus": "running",
                "uptime": 12,
                "name": "exam-vm",
                "vmid": 5100,
                "ignored": "value",
            },
        ) as request:
            result = self.provider.get_vm_status(5100)

        self.assertEqual(result, {
            "status": "running",
            "qmpstatus": "running",
            "uptime": 12,
            "name": "exam-vm",
            "vmid": 5100,
        })
        request.assert_called_once_with(
            "GET",
            "/nodes/test-node/qemu/5100/status/current",
        )


if __name__ == "__main__":
    unittest.main()
