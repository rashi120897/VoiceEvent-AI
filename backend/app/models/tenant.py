"""Tenant models for request/response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class TenantSettings(BaseModel):
    """Tenant-specific settings."""
    system_prompt: str = "You are a helpful voice assistant. Answer questions based on the provided knowledge base context. Be concise and conversational."
    tts_voice_id: str = "alloy"  # OpenAI Realtime voice: alloy, ash, ballad, coral, echo, sage, shimmer, verse
    assistant_name: str = "Assistant"
    max_concurrent_calls: int = 5


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""
    name: str = Field(..., min_length=1, max_length=255)
    settings: TenantSettings = Field(default_factory=TenantSettings)


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    name: str | None = Field(None, min_length=1, max_length=255)
    settings: TenantSettings | None = None


class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: str
    name: str
    settings: TenantSettings
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TenantWithApiKey(BaseModel):
    """Tenant response with generated API key (only returned on creation)."""
    tenant: TenantResponse
    api_key: str  # Only shown once at creation time
