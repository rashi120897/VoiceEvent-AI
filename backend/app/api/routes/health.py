"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for Railway and monitoring."""
    return {"status": "healthy", "service": "voice-assistant-api"}
