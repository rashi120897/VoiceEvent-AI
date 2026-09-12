"""API Key models."""

from datetime import datetime
from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    name: str = Field(default="Default API Key", max_length=255)


class ApiKeyResponse(BaseModel):
    """API key response schema (without the actual key)."""
    id: str
    tenant_id: str
    key_prefix: str
    name: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(BaseModel):
    """Response returned when a new API key is created (includes the full key)."""
    id: str
    key: str  # Full key, only shown once
    key_prefix: str
    name: str
