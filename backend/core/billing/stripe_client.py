"""Thin Stripe SDK wrapper for Checkout, Portal, and webhooks."""

from __future__ import annotations

from typing import Any, Literal

import stripe
from fastapi import HTTPException, status

from backend.core.config import settings
from backend.core.database.models import Subscription, User

BillingInterval = Literal["month", "year"]
PAID_PLAN = "pro"
TRIAL_DAYS = 14


def billing_configured() -> bool:
    """Return True when Stripe keys and Growth price IDs are present."""
    return bool(
        settings.STRIPE_SECRET_KEY
        and settings.STRIPE_PRICE_GROWTH_MONTHLY
        and settings.STRIPE_PRICE_GROWTH_ANNUAL
    )


def _require_billing() -> None:
    if not billing_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this server",
        )


def _stripe() -> stripe.StripeClient:
    _require_billing()
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def price_id_for_interval(interval: BillingInterval) -> str:
    if interval == "month":
        return settings.STRIPE_PRICE_GROWTH_MONTHLY
    return settings.STRIPE_PRICE_GROWTH_ANNUAL


def create_checkout_session(
    user: User,
    subscription_row: Subscription | None,
    *,
    plan: str,
    interval: BillingInterval,
) -> str:
    """Create a hosted Checkout Session and return its URL."""
    if plan != PAID_PLAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only the Growth (pro) plan is available for self-serve checkout",
        )

    if subscription_row and subscription_row.status in {"active", "trialing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active subscription. Use the billing portal to manage it.",
        )

    client = _stripe()
    price_id = price_id_for_interval(interval)
    success_url = f"{settings.FRONTEND_URL.rstrip('/')}/settings?billing=success#billing"
    cancel_url = f"{settings.FRONTEND_URL.rstrip('/')}/settings?billing=canceled#billing"

    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": str(user.id),
        "customer_email": user.email,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "subscription_data": {"trial_period_days": TRIAL_DAYS},
        "metadata": {"user_id": str(user.id), "plan": PAID_PLAN},
    }
    if subscription_row and subscription_row.stripe_customer_id:
        params["customer"] = subscription_row.stripe_customer_id
        params.pop("customer_email", None)

    session = client.checkout.sessions.create(params)
    if not session.url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a checkout URL",
        )
    return session.url


def create_portal_session(subscription_row: Subscription) -> str:
    """Create a Customer Portal session URL."""
    if not subscription_row.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account on file. Upgrade to Growth first.",
        )

    client = _stripe()
    return_url = f"{settings.FRONTEND_URL.rstrip('/')}/settings#billing"
    session = client.billing_portal.sessions.create(
        {
            "customer": subscription_row.stripe_customer_id,
            "return_url": return_url,
        }
    )
    if not session.url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a portal URL",
        )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str | None) -> stripe.Event:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret is not configured",
        )
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from exc


def retrieve_subscription(subscription_id: str) -> stripe.Subscription:
    client = _stripe()
    return client.subscriptions.retrieve(subscription_id)
