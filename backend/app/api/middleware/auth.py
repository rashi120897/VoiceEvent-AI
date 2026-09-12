"""API key authentication middleware."""

import hashlib
import secrets
import structlog

from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.db.supabase import get_supabase

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- API Key utilities ---

API_KEY_PREFIX = "va_sk_"


def generate_api_key() -> str:
    """Generate a new API key with prefix."""
    random_part = secrets.token_hex(32)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Get the display prefix of an API key (first 12 chars)."""
    return api_key[:12] + "..."


# --- Authentication dependency ---

async def authenticate_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    Authenticate request using API key and resolve tenant_id.

    Returns the tenant_id associated with the API key.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    key_hash = hash_api_key(api_key)
    supabase = get_supabase()

    try:
        result = (
            supabase.table("api_keys")
            .select("id, tenant_id, is_active")
            .eq("key_hash", key_hash)
            .execute()
        )

        if not result.data:
            logger.warning("Invalid API key attempted", key_prefix=api_key[:12])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )

        key_record = result.data[0]

        if not key_record["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key is deactivated.",
            )

        # Verify tenant is active
        tenant_result = (
            supabase.table("tenants")
            .select("id, is_active")
            .eq("id", key_record["tenant_id"])
            .execute()
        )

        if not tenant_result.data or not tenant_result.data[0]["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is deactivated.",
            )

        tenant_id = key_record["tenant_id"]

        # Store tenant_id in request state for downstream use
        request.state.tenant_id = tenant_id

        # Update last_used_at (fire and forget)
        try:
            supabase.table("api_keys").update(
                {"last_used_at": "now()"}
            ).eq("id", key_record["id"]).execute()
        except Exception:
            pass  # Non-critical, don't fail the request

        logger.info("API key authenticated", tenant_id=tenant_id)
        return tenant_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error.",
        )
