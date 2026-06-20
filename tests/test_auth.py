from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class AuthIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.clients: list[TestClient] = []
        db_path = Path(self.tmpdir.name) / "auth.sqlite"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
        os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
        os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"
        os.environ["REDIS_STATE_DB"] = "redis://localhost:6379/2"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["AUTH_SECRET_KEY"] = "test-secret"

        import app.auth
        import app.models

        import app.config
        import app.db

        importlib.reload(app.config)
        importlib.reload(app.db)
        importlib.reload(app.models)
        importlib.reload(app.auth)

        import app.main
        self.main = importlib.reload(app.main)
        self.client = TestClient(self.main.app)
        self.clients.append(self.client)

    def tearDown(self) -> None:
        import app.db

        for client in self.clients:
            client.close()
        app.db.engine.dispose()
        self.main._engine.dispose()
        try:
            self.tmpdir.cleanup()
        except PermissionError:
            pass

    def _signup(self, email: str) -> TestClient:
        client = TestClient(self.main.app)
        self.clients.append(client)
        response = client.post(
            "/api/auth/signup",
            json={
                "company_name": "Acme",
                "name": "Test User",
                "email": email,
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("user", response.json())
        return client

    def test_signup_login_me_and_logout(self) -> None:
        client = self._signup("owner@example.com")
        self.assertEqual(client.get("/api/auth/me").status_code, 200)

        duplicate = client.post(
            "/api/auth/signup",
            json={
                "company_name": "Acme",
                "name": "Other",
                "email": "OWNER@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        login_client = TestClient(self.main.app)
        self.clients.append(login_client)
        login = login_client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login_client.get("/api/auth/me").status_code, 200)

        logout = login_client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(login_client.get("/api/auth/me").status_code, 401)

    def test_campaigns_are_owned_by_current_user(self) -> None:
        owner = self._signup("owner@example.com")
        other = self._signup("other@example.com")

        with (
            patch("app.main.update_state"),
            patch("app.main.start_campaign_pipeline"),
        ):
            created = owner.post(
                "/api/campaigns",
                json={
                    "brand": "Acme",
                    "product": "Trail Mix",
                    "category": "Food",
                    "goal": "Launch",
                },
            )
        self.assertEqual(created.status_code, 200, created.text)
        campaign_id = created.json()["campaign_id"]

        self.assertEqual(owner.get(f"/api/campaigns/{campaign_id}").status_code, 200)
        self.assertEqual(other.get(f"/api/campaigns/{campaign_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/campaigns/{campaign_id}").status_code, 401)


if __name__ == "__main__":
    unittest.main()
