from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.schemas.onboarding import OnboardingRequest, OnboardingResponse
from backend.core.auth import get_current_user
from backend.core.database.models import BrandProfile, User
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingResponse, status_code=status.HTTP_200_OK)
def submit_onboarding(
    payload: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandProfile:
    """Create or update the current user's brand profile from the onboarding wizard.

    Upserts on ``user_id`` so re-submitting (e.g. the user goes back and
    edits a step) updates the existing row instead of creating a duplicate.
    """
    profile = (
        db.query(BrandProfile).filter(BrandProfile.user_id == current_user.id).first()
    )
    if profile is None:
        profile = BrandProfile(user_id=current_user.id, brand_name=payload.brand_name)
        db.add(profile)

    profile.brand_name = payload.brand_name
    profile.industry = payload.industry
    profile.company_size = payload.company_size
    profile.country = payload.country
    profile.goals = payload.goals
    profile.platforms = payload.platforms
    profile.monthly_budget = payload.monthly_budget

    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=OnboardingResponse)
def get_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandProfile:
    """Retrieve the current user's brand profile, if onboarding was completed."""
    profile = (
        db.query(BrandProfile).filter(BrandProfile.user_id == current_user.id).first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Onboarding has not been completed yet")
    return profile
