import json
import logging
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class ProxmoxError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ProxmoxProvider:
    def __init__(self, config: Any):
        self.base_url = config.get("PROXMOX_API_URL", "").rstrip("/")
        self.token_id = config.get("PROXMOX_API_TOKEN_ID", "")
        self.token_secret = config.get("PROXMOX_API_TOKEN_SECRET", "")
        self.node = config.get("PROXMOX_NODE", "")
        template_vmid = config.get("PROXMOX_TEMPLATE_VMID", "")
        self.storage = config.get("PROXMOX_STORAGE", "")
        self.console_allowed_vmids = config.get(
            "PROXMOX_CONSOLE_ALLOWED_VMIDS", ""
        )
        self.verify_ssl = config.get("PROXMOX_VERIFY_SSL", True)
        self.timeout = config.get("PROXMOX_TIMEOUT_SECONDS", 20)

        try:
            self.template_vmid = int(template_vmid)
        except (TypeError, ValueError):
            self.template_vmid = None

    @property
    def is_api_configured(self) -> bool:
        return all((
            self.base_url,
            self.token_id,
            self.token_secret,
            self.node,
        ))

    @property
    def is_configured(self) -> bool:
        return self.is_api_configured and self.template_vmid is not None

    def allowed_console_vmids(self) -> set[int]:
        vmids: set[int] = set()
        for value in self.console_allowed_vmids.split(","):
            value = value.strip()
            if not value:
                continue
            try:
                vmid = int(value)
            except ValueError as error:
                raise ProxmoxError(
                    "The Proxmox console VM allowlist is invalid."
                ) from error
            if vmid < 1:
                raise ProxmoxError(
                    "The Proxmox console VM allowlist is invalid."
                )
            vmids.add(vmid)
        return vmids

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        if not self.is_api_configured:
            raise ProxmoxError("The Proxmox environment provider is not configured.")

        url = f"{self.base_url}/api2/json{path}"
        body = urlencode(data).encode() if data is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": (
                    f"PVEAPIToken={self.token_id}={self.token_secret}"
                ),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        context = None
        if url.startswith("https://"):
            context = ssl.create_default_context() if self.verify_ssl else (
                ssl._create_unverified_context()
            )

        try:
            with urlopen(request, timeout=self.timeout, context=context) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            logger.warning("Proxmox request %s %s failed with HTTP %s", method, path, error.code)
            raise ProxmoxError(
                f"The environment provider rejected a {method} request ({error.code}).",
                status_code=error.code,
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            logger.warning("Proxmox request %s %s could not complete: %s", method, path, error)
            raise ProxmoxError("The environment provider could not be reached.") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProxmoxError("The environment provider returned an invalid response.") from error

        if not isinstance(payload, dict) or "data" not in payload:
            raise ProxmoxError("The environment provider returned an invalid response.")
        return payload["data"]

    @staticmethod
    def _path_part(value: str | int) -> str:
        return quote(str(value), safe="")

    def test_connection(self) -> dict[str, Any]:
        version = self._request("GET", "/version")
        node_status = self._request(
            "GET",
            f"/nodes/{self._path_part(self.node)}/status",
        )
        if not isinstance(version, dict):
            raise ProxmoxError("The environment provider returned an invalid version.")
        if not isinstance(node_status, dict):
            raise ProxmoxError("The environment provider returned an invalid node status.")
        return {
            key: version[key]
            for key in ("version", "release", "repository")
            if isinstance(version.get(key), str)
        }

    def list_vms(self) -> list[dict[str, Any]]:
        node = self._path_part(self.node)
        vms = self._request("GET", f"/nodes/{node}/qemu")
        if not isinstance(vms, list):
            raise ProxmoxError("The environment provider returned an invalid VM list.")
        return [
            {
                key: vm[key]
                for key in ("vmid", "name", "status", "uptime")
                if key in vm
            }
            for vm in vms
            if isinstance(vm, dict)
        ]

    def get_vm_status(self, vmid: int) -> dict[str, Any]:
        node = self._path_part(self.node)
        status = self._request(
            "GET",
            f"/nodes/{node}/qemu/{vmid}/status/current",
        )
        if not isinstance(status, dict):
            raise ProxmoxError("The environment provider returned an invalid VM status.")
        return {
            key: status[key]
            for key in ("status", "qmpstatus", "uptime", "name", "vmid")
            if key in status
        }

    def clone_vm(self, user_id: int, attempt_id: int) -> tuple[int, str]:
        if self.template_vmid is None:
            raise ProxmoxError("The Proxmox template VM ID is not configured.")
        vmid = self._request("GET", "/cluster/nextid")
        try:
            vmid = int(vmid)
        except (TypeError, ValueError) as error:
            raise ProxmoxError("The environment provider did not allocate a VM ID.") from error

        node = self._path_part(self.node)
        template_vmid = self._path_part(self.template_vmid)
        options: dict[str, Any] = {
            "newid": vmid,
            "name": f"examlab-user-{user_id}-attempt-{attempt_id}",
            "full": 1,
        }
        if self.storage:
            options["storage"] = self.storage

        task_id = self._request(
            "POST",
            f"/nodes/{node}/qemu/{template_vmid}/clone",
            options,
        )
        if not isinstance(task_id, str) or not task_id:
            raise ProxmoxError("The environment provider did not return a clone task.")
        return vmid, task_id

    def task_is_complete(self, task_id: str) -> bool:
        node = self._path_part(self.node)
        encoded_task_id = self._path_part(task_id)
        status = self._request(
            "GET",
            f"/nodes/{node}/tasks/{encoded_task_id}/status/current",
        )
        if not isinstance(status, dict):
            raise ProxmoxError("The environment provider returned an invalid task status.")
        if status.get("status") != "stopped":
            return False
        if status.get("exitstatus") != "OK":
            raise ProxmoxError("The environment provider could not prepare the exam machine.")
        return True

    def start_vm(self, vmid: int) -> str:
        node = self._path_part(self.node)
        task_id = self._request(
            "POST",
            f"/nodes/{node}/qemu/{vmid}/status/start",
        )
        if not isinstance(task_id, str) or not task_id:
            raise ProxmoxError("The environment provider did not return a start task.")
        return task_id

    def is_vm_running(self, vmid: int) -> bool:
        node = self._path_part(self.node)
        status = self._request(
            "GET",
            f"/nodes/{node}/qemu/{vmid}/status/current",
        )
        return isinstance(status, dict) and status.get("status") == "running"

    def is_vm_ready(self, vmid: int) -> bool:
        node = self._path_part(self.node)
        status = self._request(
            "GET",
            f"/nodes/{node}/qemu/{vmid}/status/current",
        )
        if not isinstance(status, dict) or status.get("status") != "running":
            return False

        try:
            self._request("POST", f"/nodes/{node}/qemu/{vmid}/agent/ping")
            interfaces = self._request(
                "POST",
                f"/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces",
            )
        except ProxmoxError as error:
            if error.status_code in {400, 500}:
                return False
            raise
        return self._has_guest_ipv4(interfaces)

    @staticmethod
    def _has_guest_ipv4(data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        interfaces = data.get("result")
        if not isinstance(interfaces, list):
            return False
        for interface in interfaces:
            if not isinstance(interface, dict):
                continue
            addresses = interface.get("ip-addresses", [])
            if not isinstance(addresses, list):
                continue
            if any(
                isinstance(address, dict)
                and address.get("ip-address-type") == "ipv4"
                and address.get("ip-address") not in {"127.0.0.1", "0.0.0.0"}
                for address in addresses
            ):
                return True
        return False

    def stop_vm(self, vmid: int) -> str | None:
        node = self._path_part(self.node)
        try:
            status = self._request(
                "GET",
                f"/nodes/{node}/qemu/{vmid}/status/current",
            )
        except ProxmoxError as error:
            if error.status_code == 404:
                return None
            raise
        if isinstance(status, dict) and status.get("status") == "running":
            task_id = self._request(
                "POST",
                f"/nodes/{node}/qemu/{vmid}/status/stop",
                {"timeout": 30},
            )
            if not isinstance(task_id, str) or not task_id:
                raise ProxmoxError("The environment provider did not return a stop task.")
            return task_id
        return None

    def delete_vm(self, vmid: int) -> str | None:
        node = self._path_part(self.node)
        try:
            task_id = self._request("DELETE", f"/nodes/{node}/qemu/{vmid}")
        except ProxmoxError as error:
            if error.status_code == 404:
                return None
            raise
        if task_id is not None and (not isinstance(task_id, str) or not task_id):
            raise ProxmoxError("The environment provider returned an invalid delete task.")
        return task_id
