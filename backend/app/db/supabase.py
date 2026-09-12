"""Supabase client setup and initialization."""

import structlog
from supabase import create_client, Client

from app.config import Settings

logger = structlog.get_logger()

_supabase_client: Client | None = None


def init_supabase(settings: Settings) -> Client:
    """Initialize and return the Supabase client."""
    global _supabase_client
    _supabase_client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
    logger.info("Supabase client initialized", url=settings.supabase_url)
    return _supabase_client


def get_supabase() -> Client:
    """Get the initialized Supabase client."""
    if _supabase_client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase() first.")
    return _supabase_client
