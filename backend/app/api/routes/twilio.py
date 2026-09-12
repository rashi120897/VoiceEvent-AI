"""Twilio webhook and Media Streams WebSocket endpoints.

Uses OpenAI Realtime API for speech-to-speech processing.
Audio flows: Twilio -> Our Server -> OpenAI Realtime -> Our Server -> Twilio
"""

import asyncio
import base64
import json
import time
import structlog
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Response, HTTPException

from app.config import get_settings
from app.db.supabase import get_supabase
from app.services.twilio_service import generate_twiml_connect, validate_twilio_signature
from app.services.openai_realtime_service import OpenAIRealtimeSession
from app.services.session_service import (
    CallSession,
    create_session,
    get_session,
    update_session,
    delete_session,
    check_rate_limit,
)
from app.models.tenant import TenantSettings

logger = structlog.get_logger()
router = APIRouter()


@router.post("/voice")
async def incoming_call(request: Request):
    """
    Twilio incoming call webhook.

    Returns TwiML that connects the call to a WebSocket Media Stream.
    This is the entry point when someone calls the Twilio phone number.
    """
    settings = get_settings()

    # Get form data from Twilio
    form_data = await request.form()
    params = dict(form_data)

    # Validate Twilio signature in production
    if settings.is_production:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        if not validate_twilio_signature(signature, url, params):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    call_sid = params.get("CallSid", "unknown")
    caller = params.get("From", "unknown")
    called_number = params.get("To", "")

    logger.info(
        "Incoming call received",
        call_sid=call_sid,
        caller=caller,
        called_number=called_number,
    )

    # Resolve tenant from the called number
    tenant_id, tenant_settings = await resolve_tenant_from_number(called_number)

    if not tenant_id:
        # If we can't resolve tenant, use a default response
        logger.warning("Could not resolve tenant for number", number=called_number)
        response = Response(content="<Response><Say>Sorry, this number is not configured.</Say></Response>")
        response.headers["Content-Type"] = "application/xml"
        return response

    # Check rate limits
    max_concurrent = tenant_settings.max_concurrent_calls if tenant_settings else 5
    if not await check_rate_limit(tenant_id, max_concurrent):
        response = Response(
            content="<Response><Say>All agents are currently busy. Please try again later.</Say></Response>"
        )
        response.headers["Content-Type"] = "application/xml"
        return response

    # Create call session
    session = CallSession(
        call_sid=call_sid,
        tenant_id=tenant_id,
        caller_number=caller,
        system_prompt=tenant_settings.system_prompt if tenant_settings else "",
        tts_voice_id=tenant_settings.tts_voice_id if tenant_settings else "",
    )
    await create_session(session)

    # Log call to Supabase
    supabase = get_supabase()
    try:
        supabase.table("call_logs").insert({
            "tenant_id": tenant_id,
            "twilio_call_sid": call_sid,
            "caller_number": caller,
            "direction": "inbound",
            "status": "in_progress",
        }).execute()
    except Exception as e:
        logger.error("Failed to log call", error=str(e))

    # Generate TwiML to connect to WebSocket
    ws_url = f"{settings.ws_base_url}/twilio/media-stream"
    twiml = generate_twiml_connect(ws_url)

    response = Response(content=twiml)
    response.headers["Content-Type"] = "application/xml"
    return response


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.

    Bidirectional audio relay:
    - Receives mulaw audio from Twilio (caller's voice) -> forwards to OpenAI Realtime API
    - Receives audio from OpenAI Realtime API -> forwards back to Twilio (assistant's response)

    OpenAI Realtime API handles STT + TTS natively. RAG context is injected
    by updating the session instructions when user speech is transcribed.
    """
    await websocket.accept()
    logger.info("Media stream WebSocket connected")

    call_sid = None
    stream_sid = None
    session: CallSession | None = None
    realtime_session: OpenAIRealtimeSession | None = None

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "connected":
                logger.info("Twilio media stream connected", data=data)

            elif event_type == "start":
                # Extract call metadata
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")

                logger.info(
                    "Media stream started",
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                )

                # Load session from Redis
                if call_sid:
                    session = await get_session(call_sid)
                    if not session:
                        logger.error("No session found for call", call_sid=call_sid)
                        break

                # Start OpenAI Realtime session
                if session and stream_sid:
                    settings = get_settings()
                    realtime_session = OpenAIRealtimeSession(
                        tenant_id=session.tenant_id,
                        call_sid=session.call_sid,
                        system_prompt=session.system_prompt or (
                            "You are a helpful voice assistant. Be concise and conversational. "
                            "Keep responses short and natural for a phone conversation."
                        ),
                        voice=settings.openai_realtime_voice,
                    )
                    await realtime_session.connect(
                        twilio_ws=websocket,
                        stream_sid=stream_sid,
                    )
                    logger.info("OpenAI Realtime session started for call", call_sid=call_sid)

            elif event_type == "media":
                # Receive audio from Twilio and forward to OpenAI
                media_data = data.get("media", {})
                payload = media_data.get("payload", "")

                if payload and realtime_session:
                    # Decode base64 mulaw audio from Twilio
                    audio_chunk = base64.b64decode(payload)
                    # Forward to OpenAI Realtime API
                    await realtime_session.send_audio(audio_chunk)

            elif event_type == "mark":
                # Mark event - audio playback completed
                mark_name = data.get("mark", {}).get("name", "")
                logger.debug("Mark received", name=mark_name)

            elif event_type == "stop":
                logger.info("Media stream stopped", call_sid=call_sid)
                break

    except WebSocketDisconnect:
        logger.info("Media stream WebSocket disconnected", call_sid=call_sid)
    except Exception as e:
        logger.error("Media stream error", error=str(e), call_sid=call_sid)
    finally:
        # Cleanup OpenAI Realtime session
        if realtime_session:
            await realtime_session.close()

            # Save conversation history from the Realtime session
            if session:
                session.conversation_history = realtime_session.conversation_history
                await update_session(session)

        # Finalize call log
        if call_sid and session:
            await _finalize_call(call_sid, session)

        logger.info("Media stream cleanup complete", call_sid=call_sid)


async def _finalize_call(call_sid: str, session: CallSession):
    """Finalize the call log when a call ends."""
    try:
        supabase = get_supabase()

        # Calculate duration
        duration = int(time.time() - session.start_time)

        # Update call log
        supabase.table("call_logs").update({
            "status": "completed",
            "duration_seconds": duration,
            "transcript": session.conversation_history,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }).eq("twilio_call_sid", call_sid).execute()

        # Clean up Redis session
        await delete_session(call_sid, session.tenant_id)

        logger.info(
            "Call finalized",
            call_sid=call_sid,
            duration=duration,
            turns=len(session.conversation_history) // 2,
        )
    except Exception as e:
        logger.error("Failed to finalize call", error=str(e), call_sid=call_sid)


async def resolve_tenant_from_number(phone_number: str) -> tuple[str | None, TenantSettings | None]:
    """
    Resolve a tenant from a Twilio phone number.

    For simplicity, we look up the first active tenant.
    In production, you'd map phone numbers to tenants.
    """
    try:
        supabase = get_supabase()

        # For now, get the first active tenant
        # TODO: Implement phone number -> tenant mapping table
        result = (
            supabase.table("tenants")
            .select("id, settings")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if result.data:
            tenant = result.data[0]
            settings = TenantSettings(**tenant["settings"])
            return tenant["id"], settings

        return None, None
    except Exception as e:
        logger.error("Failed to resolve tenant", error=str(e))
        return None, None
