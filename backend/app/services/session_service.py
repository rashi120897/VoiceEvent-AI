"""Redis session management for active voice calls."""

import json
import time
import structlog

from app.db.redis import get_redis

logger = structlog.get_logger()

SESSION_TTL = 3600  # 1 hour
RATE_LIMIT_WINDOW = 60  # 1 minute


class CallSession:
    """Represents an active call session."""

    def __init__(
        self,
        call_sid: str,
        tenant_id: str,
        caller_number: str = "",
        conversation_history: list[dict] | None = None,
        system_prompt: str = "",
        tts_voice_id: str = "",
    ):
        self.call_sid = call_sid
        self.tenant_id = tenant_id
        self.caller_number = caller_number
        self.conversation_history = conversation_history or []
        self.system_prompt = system_prompt
        self.tts_voice_id = tts_voice_id
        self.start_time = time.time()

    def to_dict(self) -> dict:
        return {
            "call_sid": self.call_sid,
            "tenant_id": self.tenant_id,
            "caller_number": self.caller_number,
            "conversation_history": self.conversation_history,
            "system_prompt": self.system_prompt,
            "tts_voice_id": self.tts_voice_id,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CallSession":
        session = cls(
            call_sid=data["call_sid"],
            tenant_id=data["tenant_id"],
            caller_number=data.get("caller_number", ""),
            conversation_history=data.get("conversation_history", []),
            system_prompt=data.get("system_prompt", ""),
            tts_voice_id=data.get("tts_voice_id", ""),
        )
        session.start_time = data.get("start_time", time.time())
        return session


def _session_key(call_sid: str) -> str:
    return f"session:{call_sid}"


def _tenant_calls_key(tenant_id: str) -> str:
    return f"tenant_calls:{tenant_id}"


async def create_session(session: CallSession) -> None:
    """Create a new call session in Redis."""
    redis = get_redis()

    key = _session_key(session.call_sid)
    await redis.set(key, json.dumps(session.to_dict()), ex=SESSION_TTL)

    # Track active calls per tenant
    tenant_key = _tenant_calls_key(session.tenant_id)
    await redis.sadd(tenant_key, session.call_sid)
    await redis.expire(tenant_key, SESSION_TTL)

    logger.info(
        "Call session created",
        call_sid=session.call_sid,
        tenant_id=session.tenant_id,
    )


async def get_session(call_sid: str) -> CallSession | None:
    """Get an active call session from Redis."""
    redis = get_redis()

    key = _session_key(call_sid)
    data = await redis.get(key)

    if data is None:
        return None

    return CallSession.from_dict(json.loads(data))


async def update_session(session: CallSession) -> None:
    """Update an existing call session."""
    redis = get_redis()

    key = _session_key(session.call_sid)
    await redis.set(key, json.dumps(session.to_dict()), ex=SESSION_TTL)


async def delete_session(call_sid: str, tenant_id: str) -> None:
    """Delete a call session from Redis."""
    redis = get_redis()

    key = _session_key(call_sid)
    await redis.delete(key)

    # Remove from tenant's active calls
    tenant_key = _tenant_calls_key(tenant_id)
    await redis.srem(tenant_key, call_sid)

    logger.info("Call session deleted", call_sid=call_sid)


async def get_active_call_count(tenant_id: str) -> int:
    """Get the number of active calls for a tenant."""
    redis = get_redis()
    tenant_key = _tenant_calls_key(tenant_id)
    return await redis.scard(tenant_key)


async def check_rate_limit(tenant_id: str, max_concurrent: int = 5) -> bool:
    """
    Check if a tenant has exceeded their concurrent call limit.

    Returns True if within limits, False if rate limited.
    """
    active_count = await get_active_call_count(tenant_id)
    if active_count >= max_concurrent:
        logger.warning(
            "Tenant rate limited",
            tenant_id=tenant_id,
            active_calls=active_count,
            max_concurrent=max_concurrent,
        )
        return False
    return True
