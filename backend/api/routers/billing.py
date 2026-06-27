"""Stripe Billing — Checkout, Customer Portal, and webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.schemas.billing import CheckoutRequest, CheckoutResponse, PortalResponse
from backend.core.auth import get_current_user
from backend.core.billing.stripe_client import (
    create_checkout_session,
    create_portal_session,
    construct_webhook_event,
)
from backend.core.billing.sync import (
    apply_checkout_session,
    apply_subscription_deleted,
    apply_subscription_updated,
)
from backend.core.database.models import Subscription, User
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _get_or_create_subscription(db: Session, user_id) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub is None:
        sub = Subscription(user_id=user_id, plan="starter")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.post("/checkout", response_model=CheckoutResponse)
def start_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutResponse:
    """Start Stripe-hosted Checkout for the Growth (pro) plan."""
    sub = _get_or_create_subscription(db, current_user.id)
    url = create_checkout_session(
        current_user,
        sub,
        plan=payload.plan,
        interval=payload.interval,
    )
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def open_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortalResponse:
    """Open Stripe Customer Portal for plan and payment method changes."""
    sub = _get_or_create_subscription(db, current_user.id)
    url = create_portal_session(sub)
    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Stripe webhook endpoint — verifies signature and syncs subscription state."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = construct_webhook_event(payload, sig_header)

    obj = event.data.object
    if event.type == "checkout.session.completed":
        apply_checkout_session(db, obj)
    elif event.type == "customer.subscription.updated":
        apply_subscription_updated(db, obj)
    elif event.type == "customer.subscription.deleted":
        apply_subscription_deleted(db, obj)
    elif event.type == "invoice.payment_failed":
        subscription_id = getattr(obj, "subscription", None)
        if subscription_id:
            from backend.core.billing.stripe_client import retrieve_subscription

            stripe_sub = retrieve_subscription(str(subscription_id))
            apply_subscription_updated(db, stripe_sub)

    return {"received": True}
