import unittest
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.services.attempt_data import now_utc_naive
from app.models import (
    Attempt,
    AttemptVMInstance,
    Exam,
    ExamVMRequirement,
    Lab,
    Task,
    User,
)


class ExamAttemptApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-jwt-secret-that-is-long-enough",
            "SSH_KEY_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
            "PROXMOX_API_URL": "https://proxmox.example.test:8006",
            "PROXMOX_API_TOKEN_ID": "test@pve!test",
            "PROXMOX_API_TOKEN_SECRET": "test-token-secret",
            "PROXMOX_NODE": "test-node",
            "PROXMOX_TEMPLATE_VMID": "9002",
            "PROXMOX_TEMPLATE_SNAP_ID": "lfcs-base",
            "EXAM_VM_SSH_USERNAME": "student",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            full_name="Exam Attempt User",
            email="exam-attempt@example.test",
            password_hash="not-used",
        )
        self.other_user = User(
            full_name="Other Attempt User",
            email="other-attempt@example.test",
            password_hash="not-used",
        )
        self.exam = Exam(
            name="Multi-VM Exam",
            description="A test exam",
            duration_minutes=90,
            active=True,
        )
        db.session.add_all((self.user, self.other_user, self.exam))
        db.session.flush()
        db.session.add_all((
            ExamVMRequirement(
                exam_id=self.exam.id,
                name="main",
                template_vmid=9000,
                snap_id="base-snapshot",
                ssh_username="student",
                is_main=True,
            ),
            ExamVMRequirement(
                exam_id=self.exam.id,
                name="database",
                template_vmid=9001,
                snap_id="database-snapshot",
                is_main=False,
            ),
        ))
        db.session.add(Task(
            exam_id=self.exam.id,
            title="Configure a service",
            description="Enable and start the target service.",
            points=5,
            order_index=1,
        ))
        db.session.commit()
        self.client = self.app.test_client()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(self.user.id))}",
        }
        self.other_headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(self.other_user.id))}",
        }

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def configured_provider(self):
        provider_patch = patch("app.routes.vm_environment_create.ProxmoxProvider")
        provider_class = provider_patch.start()
        provider = provider_class.return_value
        self.addCleanup(provider_patch.stop)
        for path in (
            "app.routes.attempt_create.ProxmoxProvider",
            "app.routes.set_attempt_data.ProxmoxProvider",
            "app.services.vm_environment.ProxmoxProvider",
        ):
            provider_patch = patch(path, return_value=provider)
            provider_patch.start()
            self.addCleanup(provider_patch.stop)
        provider.is_api_configured = True
        provider.node = "test-node"
        provider.clone_vm.side_effect = [
            (5100, "clone-main"),
            (5101, "clone-database"),
        ]
        provider.task_is_complete.return_value = True
        provider.is_vm_running.side_effect = [False, False, True, True]
        provider.start_vm.side_effect = ["start-main", "start-database"]
        provider.is_vm_ready.return_value = True
        provider.get_vm_ipv4.side_effect = ["192.0.2.10", "192.0.2.11"]
        provider.stop_vm.return_value = None
        provider.delete_vm.return_value = None
        return provider

    def start_attempt(self):
        response = self.client.post(
            f"/api/exams/{self.exam.id}/attempts",
            headers=self.headers,
        )
        if response.status_code < 400:
            attempt_id = response.get_json()["attempt"]["id"]
            response = self.client.post(
                f"/api/attempts/{attempt_id}/environment",
                headers=self.headers,
            )
        return response

    def test_attempt_clones_all_exam_vm_requirements(self) -> None:
        provider = self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            response = self.start_attempt()

        self.assertEqual(response.status_code, 202)
        attempt_data = response.get_json()["attempt"]
        self.assertEqual(attempt_data["status"], "provisioning")
        self.assertEqual(
            [instance["vm_id"] for instance in attempt_data["vm_instances"]],
            [5100, 5101],
        )
        self.assertNotIn("ip_address", attempt_data["vm_instances"][0])
        self.assertNotIn("ssh_private_key_encrypted", attempt_data)
        self.assertEqual(
            [
                instance.template_vmid
                for instance in db.session.scalars(
                    select(AttemptVMInstance)
                    .where(AttemptVMInstance.attempt_id == attempt_data["id"])
                    .order_by(AttemptVMInstance.id)
                ).all()
            ],
            [9000, 9001],
        )
        self.assertEqual(
            [call.kwargs["snap_id"] for call in provider.clone_vm.call_args_list],
            ["base-snapshot", "database-snapshot"],
        )
        self.assertEqual(provider.clone_vm.call_count, 2)
        provider.configure_vm_ssh_key.assert_not_called()

    def test_attempt_data_only_returns_status_timing_and_questions(self) -> None:
        self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            created = self.client.post(
                f"/api/exams/{self.exam.id}/attempts",
                headers=self.headers,
            )
        attempt_id = created.get_json()["attempt"]["id"]

        response = self.client.get(
            f"/api/attempts/{attempt_id}",
            headers=self.headers,
        )
        attempt_data = response.get_json()["attempt"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(attempt_data["status"], "provisioning")
        self.assertTrue(attempt_data["started_at"])
        self.assertTrue(attempt_data["expires_at"])
        self.assertEqual(
            attempt_data["questions"],
            [{
                "id": attempt_data["questions"][0]["id"],
                "title": "Configure a service",
                "description": "Enable and start the target service.",
                "points": 5,
                "order_index": 1,
            }],
        )
        self.assertTrue(all(instance["vm_id"] is None for instance in attempt_data["vm_instances"]))

    def test_examtry_seeds_snapshot_901_and_clones_it_for_an_attempt(self) -> None:
        provider = self.configured_provider()
        exam_response = self.client.get("/api/exams/by-slug/examtry")

        self.assertEqual(exam_response.status_code, 200)
        exam_data = exam_response.get_json()["exam"]
        self.assertEqual(exam_data["slug"], "examtry")
        exam = db.session.scalar(
            select(Exam).where(Exam.slug == "examtry")
        )
        requirement = db.session.scalar(
            select(ExamVMRequirement).where(
                ExamVMRequirement.exam_id == exam.id
            )
        )
        self.assertEqual(requirement.template_vmid, 9002)
        self.assertEqual(requirement.snap_id, "901")
        self.assertTrue(requirement.is_main)

        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            response = self.client.post(
                f"/api/exams/{exam.id}/attempts",
                headers=self.headers,
            )
        response = self.client.post(
            f"/api/attempts/{response.get_json()['attempt']['id']}/environment",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 202)
        instance = response.get_json()["attempt"]["vm_instances"][0]
        self.assertEqual(instance["vm_id"], 5100)
        provider.clone_vm.assert_called_once_with(
            self.user.id,
            response.get_json()["attempt"]["id"],
            snap_id="901",
            template_vmid=9002,
            name=f"exam-{exam.id}-attempt-{response.get_json()['attempt']['id']}-main",
        )

    def test_attempt_becomes_running_only_when_each_vm_is_ready(self) -> None:
        provider = self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            started = self.start_attempt()
        attempt_id = started.get_json()["attempt"]["id"]

        first_poll = self.client.get(
            f"/api/attempts/{attempt_id}/environment",
            headers=self.headers,
        )
        first_data = self.client.get(
            f"/api/attempts/{attempt_id}",
            headers=self.headers,
        )
        self.assertEqual(first_poll.get_json()["attempt"]["status"], "provisioning")
        self.assertEqual(first_data.get_json()["attempt"]["status"], "provisioning")
        provider.configure_vm_ssh_key.assert_called_once_with(5100, "ssh-ed25519 public-test-key")

        second_poll = self.client.get(
            f"/api/attempts/{attempt_id}/environment",
            headers=self.headers,
        )
        second_data = self.client.get(
            f"/api/attempts/{attempt_id}",
            headers=self.headers,
        )
        attempt_data = second_data.get_json()["attempt"]
        self.assertEqual(attempt_data["status"], "running")
        self.assertEqual(
            [instance["status"] for instance in attempt_data["vm_instances"]],
            ["ready", "ready"],
        )
        self.assertEqual(
            [
                instance.ip_address
                for instance in db.session.scalars(
                    select(AttemptVMInstance)
                    .where(AttemptVMInstance.attempt_id == attempt_id)
                    .order_by(AttemptVMInstance.id)
                ).all()
            ],
            ["192.0.2.10", "192.0.2.11"],
        )
        attempt = db.session.get(Attempt, attempt_id)
        self.assertNotEqual(attempt.ssh_private_key_encrypted, "private-test-key")

    def test_attempt_access_is_limited_to_its_owner(self) -> None:
        self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            response = self.start_attempt()
        attempt_id = response.get_json()["attempt"]["id"]

        other_response = self.client.get(
            f"/api/attempts/{attempt_id}",
            headers=self.other_headers,
        )

        self.assertEqual(other_response.status_code, 404)

    def test_finish_stops_and_deletes_every_vm(self) -> None:
        provider = self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            response = self.start_attempt()
        attempt_id = response.get_json()["attempt"]["id"]

        finish = self.client.post(
            f"/api/attempts/{attempt_id}/finish",
            headers=self.headers,
        )

        self.assertEqual(finish.status_code, 200)
        attempt_data = finish.get_json()["attempt"]
        self.assertEqual(attempt_data["status"], "completed")
        self.assertEqual(
            [instance["status"] for instance in attempt_data["vm_instances"]],
            ["stopped", "stopped"],
        )
        self.assertEqual(provider.stop_vm.call_count, 2)
        self.assertEqual(provider.delete_vm.call_count, 2)
        self.assertIsNone(
            db.session.get(Attempt, attempt_id).ssh_private_key_encrypted
        )
        self.assertEqual(
            db.session.scalar(
                select(db.func.count()).select_from(AttemptVMInstance)
            ),
            2,
        )

    def test_exam_requires_one_main_vm_and_one_to_ten_vms(self) -> None:
        requirement = db.session.scalar(
            select(ExamVMRequirement).where(
                ExamVMRequirement.exam_id == self.exam.id,
                ExamVMRequirement.is_main.is_(True),
            )
        )
        requirement.is_main = False
        db.session.commit()

        response = self.start_attempt()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["code"],
            "invalid_exam_vm_requirements",
        )

    def test_slug_lookup_exposes_id_and_seeds_default_lfcs_template(self) -> None:
        response = self.client.get("/api/exams/by-slug/lfcs")

        self.assertEqual(response.status_code, 200)
        exam_data = response.get_json()["exam"]
        self.assertEqual(exam_data["slug"], "lfcs")
        self.assertEqual(exam_data["vm_count"], 1)
        self.assertEqual(exam_data["main_vm"], "main")
        requirement = db.session.scalar(
            select(ExamVMRequirement).where(
                ExamVMRequirement.exam_id == exam_data["id"]
            )
        )
        self.assertEqual(requirement.template_vmid, 9002)
        self.assertEqual(requirement.snap_id, "lfcs-base")
        self.assertEqual(requirement.ssh_username, "student")

    def test_cleanup_worker_expires_and_removes_new_attempt_vms(self) -> None:
        provider = self.configured_provider()
        with patch(
            "app.routes.attempt_create.create_attempt_ssh_key",
            return_value=(b"private-test-key", "ssh-ed25519 public-test-key"),
        ):
            response = self.start_attempt()
        attempt_id = response.get_json()["attempt"]["id"]
        attempt = db.session.get(Attempt, attempt_id)
        attempt.started_at -= timedelta(minutes=91)
        db.session.commit()

        from app.services.vm_environment import expire_due_exam_attempts

        cleaned = expire_due_exam_attempts()

        self.assertEqual(cleaned, 1)
        self.assertEqual(attempt.status, "expired")
        self.assertTrue(all(
            instance.status == "stopped"
            for instance in db.session.scalars(
                select(AttemptVMInstance).where(
                    AttemptVMInstance.attempt_id == attempt_id
                )
            ).all()
        ))
        self.assertEqual(provider.delete_vm.call_count, 2)

    def test_cleanup_worker_finishes_cleanup_of_legacy_lab_vms(self) -> None:
        provider = self.configured_provider()
        attempt = Attempt(
            user_id=self.user.id,
            exam_id=self.exam.id,
            status="running",
            started_at=now_utc_naive() - timedelta(hours=25),
        )
        db.session.add(attempt)
        db.session.flush()
        lab = Lab(
            attempt_id=attempt.id,
            provider="proxmox",
            node="test-node",
            vm_id=5100,
            status="ready",
        )
        db.session.add(lab)
        db.session.commit()

        from app.services.vm_environment import expire_due_exam_attempts

        cleaned = expire_due_exam_attempts()

        self.assertEqual(cleaned, 1)
        self.assertEqual(attempt.status, "expired")
        self.assertEqual(lab.status, "stopped")
        provider.stop_vm.assert_called_once_with(5100)
        provider.delete_vm.assert_called_once_with(5100)


if __name__ == "__main__":
    unittest.main()
