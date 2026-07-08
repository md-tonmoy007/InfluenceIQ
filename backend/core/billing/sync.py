"""Map Stripe subscription objects onto local Subscription rows."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.api.schemas.settings import SubscriptionResponse
from backend.core.billing.stripe_client import retrieve_subscription
from backend.core.config import settings
from backend.core.database.models import Subscription

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"active", "trialing", "past_due"}

GROWTH_PRICE_IDS = (
    "STRIPE_PRICE_GROWTH_MONTHLY",
    "STRIPE_PRICE_GROWTH_ANNUAL",
)


def plan_from_price_id(price_id: str | None) -> str:
    if price_id in {
        settings.STRIPE_PRICE_GROWTH_MONTHLY,
        settings.STRIPE_PRICE_GROWTH_ANNUAL,
    }:
        return "pro"
    return "starter"


def resolve_plan_for_active_status(price_id: str | None) -> str:
    """Pick the local plan name for a paid (active/trialing/past_due) subscription.

    The only self-serve paid plan today is Growth, so any subscription in an
    active Stripe status should resolve to ``"pro"`` regardless of which price
    id landed on the subscription. We still consult :func:`plan_from_price_id`
    first so that any future non-pro paid price ids can be added without a
    schema migration; the fallback only fires when the price id is missing or
    not in the configured set (e.g. an env-var drift or a dashboard price
    rotation). In that case we log a warning so the mismatch is visible.
    """
    if price_id is not None:
        mapped = plan_from_price_id(price_id)
        if mapped != "starter":
            return mapped
        configured = {getattr(settings, name) for name in GROWTH_PRICE_IDS}
        if price_id not in configured:
            logger.warning(
                "stripe subscription has active status but unrecognised price id %r; "
                "defaulting to plan='pro'",
                price_id,
            )
    return "pro"


def interval_from_price_id(price_id: str | None) -> str | None:
    if price_id == settings.STRIPE_PRICE_GROWTH_MONTHLY:
        return "month"
    if price_id == settings.STRIPE_PRICE_GROWTH_ANNUAL:
        return "year"
    return None


def _ts_to_dt(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)


def _subscription_price_id(stripe_sub: Any) -> str | None:
    items = getattr(stripe_sub, "items", None)
    data = getattr(items, "data", None) if items is not None else None
    if not data:
        return None
    first = data[0]
    price = getattr(first, "price", None)
    if price is None and isinstance(first, dict):
        price = first.get("price")
    if price is None:
        return None
    if isinstance(price, dict):
        return price.get("id")
    return getattr(price, "id", None)


def _get_or_create_subscription(db: Session, user_id: uuid.UUID) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub is None:
        sub = Subscription(user_id=user_id, plan="starter")
        db.add(sub)
    return sub


def apply_stripe_subscription(
    db: Session,
    *,
    user_id: uuid.UUID,
    stripe_customer_id: str | None,
    stripe_subscription: Any,
) -> Subscription:
    """Upsert the local subscription row from a Stripe Subscription object."""
    row = _get_or_create_subscription(db, user_id)
    sub_id = getattr(stripe_subscription, "id", None)
    status = getattr(stripe_subscription, "status", None)
    price_id = _subscription_price_id(stripe_subscription)

    row.stripe_customer_id = stripe_customer_id or row.stripe_customer_id
    row.stripe_subscription_id = sub_id
    row.status = status
    row.billing_interval = interval_from_price_id(price_id)
    row.trial_end = _ts_to_dt(getattr(stripe_subscription, "trial_end", None))
    row.current_period_end = _ts_to_dt(
        getattr(stripe_subscription, "current_period_end", None)
    )
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)

    if status in ACTIVE_STATUSES:
        row.plan = resolve_plan_for_active_status(price_id)
    elif status == "canceled":
        row.plan = "starter"
        row.stripe_subscription_id = None
        row.billing_interval = None
        row.trial_end = None
        row.current_period_end = None

    db.commit()
    db.refresh(row)
    return row


def apply_checkout_session(db: Session, session: Any) -> Subscription | None:
    """Sync subscription after checkout.session.completed."""
    user_id_raw = getattr(session, "client_reference_id", None)
    subscription_id = getattr(session, "subscription", None)
    customer_id = getattr(session, "customer", None)
    if not user_id_raw or not subscription_id:
        return None

    try:
        user_id = uuid.UUID(str(user_id_raw))
    except ValueError:
        return None

    stripe_sub = retrieve_subscription(str(subscription_id))
    return apply_stripe_subscription(
        db,
        user_id=user_id,
        stripe_customer_id=str(customer_id) if customer_id else None,
        stripe_subscription=stripe_sub,
    )


def apply_subscription_updated(db: Session, stripe_sub: Any) -> Subscription | None:
    """Sync subscription on customer.subscription.updated."""
    sub_id = getattr(stripe_sub, "id", None)
    if not sub_id:
        return None

    row = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == str(sub_id))
        .first()
    )
    if row is None:
        metadata = getattr(stripe_sub, "metadata", None) or {}
        user_id_raw = metadata.get("user_id") if isinstance(metadata, dict) else None
        if not user_id_raw:
            return None
        try:
            user_id = uuid.UUID(str(user_id_raw))
        except ValueError:
            return None
    else:
        user_id = row.user_id

    customer_id = getattr(stripe_sub, "customer", None)
    return apply_stripe_subscription(
        db,
        user_id=user_id,
        stripe_customer_id=str(customer_id) if customer_id else None,
        stripe_subscription=stripe_sub,
    )


def apply_subscription_deleted(db: Session, stripe_sub: Any) -> Subscription | None:
    """Downgrade to starter when a subscription is deleted."""
    sub_id = getattr(stripe_sub, "id", None)
    if not sub_id:
        return None

    row = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == str(sub_id))
        .first()
    )
    if row is None:
        return None

    row.plan = "starter"
    row.status = "canceled"
    row.stripe_subscription_id = None
    row.billing_interval = None
    row.trial_end = None
    row.current_period_end = None
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(row)
    return row


def subscription_to_response(sub: Subscription) -> SubscriptionResponse:
    has_payment_method = bool(
        sub.stripe_customer_id and sub.status in ACTIVE_STATUSES
    )
    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        billing_interval=sub.billing_interval,
        trial_end=sub.trial_end,
        current_period_end=sub.current_period_end,
        has_payment_method=has_payment_method,
        updated_at=sub.updated_at,
    )
