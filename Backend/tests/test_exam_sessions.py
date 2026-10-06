import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Attempt, Lab, User


class ExamSessionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "PROXMOX_API_URL": "https://proxmox.example.test:8006",
            "PROXMOX_API_TOKEN_ID": "test@pve!test",
            "PROXMOX_API_TOKEN_SECRET": "test-token-secret",
            "PROXMOX_NODE": "test-node",
            "PROXMOX_TEMPLATE_VMID": "9000",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            full_name="Exam Session User",
            email="exam-session@example.test",
            password_hash="not-used",
        )
        self.other_user = User(
            full_name="Other Session User",
            email="other-session@example.test",
            password_hash="not-used",
        )
        db.session.add_all((self.user, self.other_user))
        db.session.commit()
        self.client = self.app.test_client()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(str(self.user.id))}"
        }
        self.other_headers = {
            "Authorization": f"Bearer {create_access_token(str(self.other_user.id))}"
        }

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def configured_provider(self):
        provider_patch = patch("app.routes.exam_sessions.ProxmoxProvider")
        provider_class = provider_patch.start()
        self.addCleanup(provider_patch.stop)
        provider = provider_class.return_value
        provider.is_configured = True
        provider.clone_vm.return_value = (5100, "clone-task")
        provider.task_is_complete.return_value = True
        provider.is_vm_running.side_effect = [False, True]
        provider.start_vm.return_value = "start-task"
        provider.is_vm_ready.return_value = True
        provider.stop_vm.return_value = None
        provider.delete_vm.return_value = None
        return provider

    def start_session(self) -> dict:
        response = self.client.post(
            "/api/exam/sessions",
            json={"exam_slug": "lfcs"},
            headers=self.headers,
        )
        self.assertIn(response.status_code, (200, 202))
        return response.get_json()["session"]

    def test_start_and_poll_transitions_to_running(self) -> None:
        provider = self.configured_provider()
        started = self.start_session()

        self.assertEqual(started["status"], "provisioning")
        self.assertEqual(started["environment"]["vm_id"], 5100)
        self.assertTrue(started["expires_at"].endswith("Z"))

        starting = self.client.get(
            f"/api/exam/sessions/{started['id']}",
            headers=self.headers,
        )
        self.assertEqual(starting.status_code, 200)
        self.assertEqual(starting.get_json()["session"]["status"], "provisioning")
        provider.start_vm.assert_called_once_with(5100)

        response = self.client.get(
            f"/api/exam/sessions/{started['id']}",
            headers=self.headers,
        )
        session = response.get_json()["session"]
        self.assertEqual(session["status"], "running")
        self.assertEqual(session["environment"]["status"], "ready")

    def test_start_resumes_existing_active_session(self) -> None:
        provider = self.configured_provider()
        first = self.start_session()
        second = self.start_session()

        self.assertEqual(second["id"], first["id"])
        self.assertEqual(
            db.session.scalar(select(db.func.count()).select_from(Attempt)),
            1,
        )
        provider.clone_vm.assert_called_once()

    def test_attempt_is_only_accessible_to_its_owner(self) -> None:
        self.configured_provider()
        session = self.start_session()

        response = self.client.get(
            f"/api/exam/sessions/{session['id']}",
            headers=self.other_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_expired_attempt_is_closed_and_environment_destroyed(self) -> None:
        provider = self.configured_provider()
        session = self.start_session()
        attempt = db.session.get(Attempt, session["id"])
        lab = db.session.scalar(select(Lab).where(Lab.attempt_id == attempt.id))
        attempt.started_at = datetime.utcnow() - timedelta(hours=25)
        db.session.commit()

        response = self.client.get(
            f"/api/exam/sessions/{session['id']}",
            headers=self.headers,
        )

        payload = response.get_json()["session"]
        self.assertEqual(payload["status"], "expired")
        self.assertEqual(payload["environment"]["status"], "stopped")
        self.assertIsNotNone(attempt.finished_at)
        provider.stop_vm.assert_called_once_with(lab.vm_id)
        provider.delete_vm.assert_called_once_with(lab.vm_id)

    def test_start_requires_a_configured_environment_provider(self) -> None:
        with patch("app.routes.exam_sessions.ProxmoxProvider") as provider_class:
            provider_class.return_value.is_configured = False
            response = self.client.post(
                "/api/exam/sessions",
                json={"exam_slug": "lfcs"},
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "environment_not_configured")
        self.assertEqual(
            db.session.scalar(select(db.func.count()).select_from(Attempt)),
            0,
        )

    def test_finish_completes_attempt_and_stops_environment(self) -> None:
        provider = self.configured_provider()
        session = self.start_session()

        response = self.client.post(
            f"/api/exam/sessions/{session['id']}/finish",
            headers=self.headers,
        )

        payload = response.get_json()["session"]
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["environment"]["status"], "stopped")
        provider.stop_vm.assert_called_once_with(session["environment"]["vm_id"])
        provider.delete_vm.assert_called_once_with(session["environment"]["vm_id"])


if __name__ == "__main__":
    unittest.main()
