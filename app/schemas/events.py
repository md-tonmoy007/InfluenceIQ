from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebSocketEvent(BaseModel):
    """Pydantic model validating structured real-time pipeline events."""
    event_id: int
    type: str = Field(..., description="e.g. 'query.generated', 'url.discovered', 'score.calculated'")
    campaign_id: UUID
    timestamp: str = Field(..., description="ISO-8601-Z string representation")
    payload: dict[str, Any] = Field(default_factory=dict)
