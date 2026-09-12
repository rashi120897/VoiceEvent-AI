"""Call log models."""

from datetime import datetime
from pydantic import BaseModel


class TranscriptEntry(BaseModel):
    """A single entry in the call transcript."""
    role: str  # user, assistant
    text: str
    timestamp: datetime


class CallLogResponse(BaseModel):
    """Call log response schema."""
    id: str
    tenant_id: str
    twilio_call_sid: str
    caller_number: str | None
    direction: str
    duration_seconds: int | None
    status: str
    transcript: list[TranscriptEntry]
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime


class CallLogListResponse(BaseModel):
    """List of call logs response."""
    call_logs: list[CallLogResponse]
    total: int
