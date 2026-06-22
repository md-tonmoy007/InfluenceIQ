"""Shared API error envelope.

All non-2xx responses across the API return the same shape so clients
can write one error handler instead of branching on ``detail`` vs
``message`` vs custom fields per endpoint.

Shape::

    {
        "error": {
            "code": "validation_error",
            "message": "1 validation error: body -> weights -> sum must be 1.0",
            "details": [
                {"field": "weights.relevance", "issue": "value must sum to 1.0"}
            ],
            "request_id": "01HZ...ULID",
        }
    }
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """One concrete issue inside an :class:`ErrorEnvelope`."""

    field: str | None = Field(default=None, description="dotted path to the offending field, if any")
    issue: str = Field(..., description="human-readable issue description")
    code: str | None = Field(default=None, description="machine-readable code for this detail row")


class ErrorBody(BaseModel):
    """The inner ``error`` object of :class:`ErrorEnvelope`."""

    code: str = Field(..., description="machine-readable top-level error code")
    message: str = Field(..., description="human-readable summary of what went wrong")
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="granular issues; empty when the error is a single message",
    )
    request_id: str | None = Field(
        default=None,
        description="request ID echoed from the X-Request-ID header, when present",
    )


class ErrorEnvelope(BaseModel):
    """Top-level wrapper for every non-2xx response."""

    error: ErrorBody

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "validation_error",
                    "message": "Request payload failed schema validation",
                    "details": [
                        {"field": "weights", "issue": "Custom weights must sum to 1.0"}
                    ],
                    "request_id": "01HZ-EXAMPLE",
                }
            }
        }


__all__ = ["ErrorBody", "ErrorDetail", "ErrorEnvelope"]
