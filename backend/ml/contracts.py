from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SubjectType(StrEnum):
    ACCOUNT = "account"
    CONTENT = "content"
    CLUSTER = "cluster"
    CAMPAIGN = "campaign"


class TextInferenceRequest(BaseModel):
    tenant_id: UUID
    subject_id: UUID
    text: str = Field(min_length=1, max_length=100_000)
    language: str | None = None


class SemanticScore(BaseModel):
    model_config = {"protected_namespaces": ()}

    subject_id: UUID
    semantic_score: float = Field(ge=0, le=1)
    spam_probability: float = Field(ge=0, le=1)
    toxicity_probability: float = Field(ge=0, le=1)
    aigc_probability: float = Field(ge=0, le=1)
    model_versions: dict[str, str]
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BehaviorFeatures(BaseModel):
    tenant_id: UUID
    subject_id: UUID
    posts_per_hour: float = Field(ge=0)
    median_session_minutes: float = Field(ge=0)
    account_age_days: float = Field(ge=0)
    engagement_velocity: float = Field(ge=0)
    follower_growth_per_day: float
    duplicate_comment_ratio: float = Field(ge=0, le=1)
    posting_interval_cv: float = Field(ge=0)
    night_activity_ratio: float = Field(ge=0, le=1)


class BehaviorScore(BaseModel):
    model_config = {"protected_namespaces": ()}

    subject_id: UUID
    behavior_score: float = Field(ge=0, le=1)
    feature_contributions: dict[str, float]
    model_version: str = "behavior-calibration-v1"


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = Field(default=1, gt=0)


class GraphAnalysisRequest(BaseModel):
    tenant_id: UUID
    edges: list[GraphEdge] = Field(min_length=1, max_length=1_000_000)


class RiskyCluster(BaseModel):
    cluster_id: UUID = Field(default_factory=uuid4)
    members: list[str]
    density: float
    reciprocity: float
    cluster_risk_score: float = Field(ge=0, le=1)


class GraphAnalysisResponse(BaseModel):
    graph_risk_score: float = Field(ge=0, le=1)
    clusters: list[RiskyCluster]
    metrics: dict[str, Any]

