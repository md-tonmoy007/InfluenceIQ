"""Stripe billing API tests."""

from __future__ import annotations

import os
import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_x")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("STRIPE_PRICE_GROWTH_MONTHLY", "price_monthly_test")
os.environ.setdefault("STRIPE_PRICE_GROWTH_ANNUAL", "price_annual_test")

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db


class FakeQuery:
    def __init__(self, session: "FakeSession", entities: tuple):
        self.session = session
        self.entities = entities
        self._filters: list[tuple] = []

    def filter(self, *args, **kwargs):
        self._filters.extend(args)
        return self

    def first(self):
        results = self._results()
        return results[0] if results else None

    def _results(self):
        if self.entities == (models.Subscription,):
            if self.session.subscription is None:
                return []
            for flt in self._filters:
                left = getattr(flt, "left", None)
                if left is not None and getattr(left, "key", None) == "user_id":
                    if self.session.subscription.user_id == flt.right.value:
                        return [self.session.subscription]
                if left is not None and getattr(left, "key", None) == "stripe_subscription_id":
                    if self.session.subscription.stripe_subscription_id == flt.right.value:
                        return [self.session.subscription]
            return [self.session.subscription]
        return []


class FakeSession:
    def __init__(self):
        self.subscription: models.Subscription | None = None
        self.committed = False

    def add(self, obj):
        if isinstance(obj, models.Subscription):
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.subscription = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    def query(self, *entities):
        return FakeQuery(self, entities)

    def close(self):
        return None


def _fake_user() -> models.User:
    return models.User(
        id=uuid.uuid4(),
        email="billing@example.com",
        password_hash="x",
        name="Billing User",
        company_name="Acme",
    )


class BillingApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides.clear()
        self.session = FakeSession()
        self.user = _fake_user()

        def _override_get_db():
            yield self.session

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_checkout_rejects_starter_plan(self):
        response = self.client.post(
            "/api/billing/checkout",
            json={"plan": "starter", "interval": "month"},
        )
        self.assertEqual(response.status_code, 422)

    @patch("backend.core.billing.stripe_client._stripe")
    def test_checkout_returns_url_for_pro(self, mock_stripe_factory):
        mock_client = MagicMock()
        mock_client.checkout.sessions.create.return_value = SimpleNamespace(
            url="https://checkout.stripe.test/session"
        )
        mock_stripe_factory.return_value = mock_client

        response = self.client.post(
            "/api/billing/checkout",
            json={"plan": "pro", "interval": "month"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["checkout_url"],
            "https://checkout.stripe.test/session",
        )
        create_args = mock_client.checkout.sessions.create.call_args[0][0]
        self.assertEqual(create_args["mode"], "subscription")
        self.assertNotIn("payment_method_types", create_args)
        self.assertEqual(create_args["subscription_data"]["trial_period_days"], 14)

    def test_settings_subscription_post_is_forbidden(self):
        response = self.client.post(
            "/api/settings/subscription",
            json={"plan": "pro"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("backend.api.routers.billing.construct_webhook_event")
    @patch("backend.api.routers.billing.apply_checkout_session")
    def test_webhook_accepts_checkout_completed(self, mock_apply, mock_construct):
        mock_construct.return_value = SimpleNamespace(
            type="checkout.session.completed",
            data=SimpleNamespace(object={"id": "cs_test"}),
        )
        response = self.client.post(
            "/api/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig_test"},
        )
        self.assertEqual(response.status_code, 200)
        mock_apply.assert_called_once()

    @patch("backend.api.routers.billing.construct_webhook_event")
    def test_webhook_rejects_bad_signature(self, mock_construct):
        from fastapi import HTTPException

        mock_construct.side_effect = HTTPException(status_code=400, detail="Invalid webhook signature")
        response = self.client.post(
            "/api/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "bad"},
        )
        self.assertEqual(response.status_code, 400)


class BillingSyncTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.user_id = uuid.uuid4()

    def test_apply_subscription_deleted_resets_to_starter(self):
        from backend.core.billing.sync import apply_subscription_deleted

        row = models.Subscription(
            user_id=self.user_id,
            plan="pro",
            stripe_subscription_id="sub_deleted",
            status="active",
        )
        row.id = uuid.uuid4()
        self.session.subscription = row

        stripe_sub = SimpleNamespace(id="sub_deleted")
        result = apply_subscription_deleted(self.session, stripe_sub)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.plan, "starter")
        self.assertEqual(result.status, "canceled")
        self.assertIsNone(result.stripe_subscription_id)

    def test_apply_stripe_subscription_sets_pro_from_price(self):
        from backend.core.billing.sync import apply_stripe_subscription

        stripe_sub = SimpleNamespace(
            id="sub_active",
            status="trialing",
            customer="cus_test",
            trial_end=int(datetime.now(UTC).timestamp()) + 86400,
            current_period_end=int(datetime.now(UTC).timestamp()) + 86400 * 30,
            items=SimpleNamespace(
                data=[
                    SimpleNamespace(
                        price=SimpleNamespace(id="price_monthly_test"),
                    )
                ]
            ),
        )
        row = apply_stripe_subscription(
            self.session,
            user_id=self.user_id,
            stripe_customer_id="cus_test",
            stripe_subscription=stripe_sub,
        )
        self.assertEqual(row.plan, "pro")
        self.assertEqual(row.status, "trialing")
        self.assertEqual(row.billing_interval, "month")


if __name__ == "__main__":
    unittest.main()
