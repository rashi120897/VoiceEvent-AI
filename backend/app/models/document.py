"""Document models for knowledge base management."""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Document metadata response."""
    id: str
    tenant_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    chunk_count: int
    status: str  # processing, ready, error
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """List of documents response."""
    documents: list[DocumentResponse]
    total: int
