"""Pydantic schemas for /api/billing."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BillingInterval = Literal["month", "year"]
CheckoutPlan = Literal["pro"]


class CheckoutRequest(BaseModel):
    plan: CheckoutPlan = Field(..., description="Self-serve paid plan (Growth → pro)")
    interval: BillingInterval = Field(..., description="month or year billing cadence")


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str
