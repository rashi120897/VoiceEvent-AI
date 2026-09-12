"""FastAPI application entry point for Voice Assistant SaaS."""

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import health, tenants, documents, twilio
from app.db.supabase import init_supabase
from app.db.redis import init_redis, close_redis
from app.services.pinecone_service import init_pinecone


def configure_logging(is_production: bool = False) -> None:
    """Configure structlog for the application."""
    renderer = (
        structlog.processors.JSONRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # Configure logging based on environment
    configure_logging(settings.is_production)

    logger.info("Starting Voice Assistant SaaS", env=settings.app_env)

    # Initialize external services
    init_supabase(settings)
    await init_redis(settings)
    init_pinecone(settings)

    logger.info("All services initialized successfully")
    yield

    # Cleanup
    await close_redis()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Configure logging early
    configure_logging(settings.is_production)

    app = FastAPI(
        title="Voice Assistant SaaS",
        description="Multi-tenant voice assistant with RAG-powered knowledge base",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])
    app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
    app.include_router(twilio.router, prefix="/twilio", tags=["Twilio"])

    return app


app = create_app()
