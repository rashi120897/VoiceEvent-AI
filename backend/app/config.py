"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the Voice Assistant SaaS."""

    # --- Supabase ---
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon/public key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # --- Pinecone ---
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_index_name: str = Field(default="voice-assistant", description="Pinecone index name")
    pinecone_environment: str = Field(default="us-east-1", description="Pinecone environment/region")

    # --- OpenAI ---
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    openai_llm_model: str = Field(default="gpt-4o", description="OpenAI LLM model")
    openai_realtime_model: str = Field(default="gpt-4o-realtime-preview", description="OpenAI Realtime API model")
    openai_realtime_voice: str = Field(default="alloy", description="OpenAI Realtime API voice (alloy, echo, shimmer, etc.)")

    # --- Twilio ---
    twilio_account_sid: str = Field(..., description="Twilio Account SID")
    twilio_auth_token: str = Field(..., description="Twilio Auth Token")
    twilio_phone_number: str = Field(..., description="Twilio phone number")

    # --- App ---
    app_env: str = Field(default="development", description="Application environment")
    app_base_url: str = Field(default="http://localhost:8000", description="Base URL of the app")
    cors_origins: str = Field(default="http://localhost:5173", description="Comma-separated CORS origins")
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def ws_base_url(self) -> str:
        """WebSocket base URL derived from app_base_url."""
        return self.app_base_url.replace("https://", "wss://").replace("http://", "ws://")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
