"""Shared FastAPI dependencies."""

from fastapi import Depends, Request, HTTPException, status

from app.config import Settings, get_settings


def get_current_settings() -> Settings:
    """Dependency to get application settings."""
    return get_settings()


async def get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request state (set by auth middleware)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid X-API-Key header.",
        )
    return tenant_id
