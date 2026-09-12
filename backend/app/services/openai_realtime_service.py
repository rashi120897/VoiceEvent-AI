"""
OpenAI Realtime API service for speech-to-speech voice assistant.

Manages a WebSocket connection to OpenAI's Realtime API which handles
both STT (speech-to-text) and TTS (text-to-speech) natively, providing
the lowest-latency voice experience.

Architecture:
  Twilio Media Stream -> Our Server -> OpenAI Realtime API
  Twilio Media Stream <- Our Server <- OpenAI Realtime API

RAG context is injected by updating the session instructions whenever
the user speaks, so the model has knowledge base context available.
"""

import asyncio
import base64
import json
import structlog
import websockets

from app.config import get_settings
from app.services.openai_service import generate_embedding
from app.services.pinecone_service import query_vectors

logger = structlog.get_logger()

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class OpenAIRealtimeSession:
    """
    Manages a single OpenAI Realtime API WebSocket session for a voice call.

    Handles bidirectional audio relay between Twilio and OpenAI, plus
    RAG context injection when the user's speech is transcribed.
    """

    def __init__(
        self,
        tenant_id: str,
        call_sid: str,
        system_prompt: str,
        voice: str | None = None,
    ):
        self.tenant_id = tenant_id
        self.call_sid = call_sid
        self.system_prompt = system_prompt
        self.settings = get_settings()
        self.voice = voice or self.settings.openai_realtime_voice
        self.ws = None
        self._is_connected = False
        self._receive_task: asyncio.Task | None = None
        self._twilio_ws = None
        self._stream_sid: str | None = None
        self.conversation_history: list[dict] = []
        self._on_transcript_callback = None
        self._on_response_text_callback = None

    async def connect(self, twilio_ws, stream_sid: str) -> None:
        """
        Open a WebSocket connection to OpenAI Realtime API.

        Args:
            twilio_ws: The Twilio Media Stream WebSocket to relay audio back to.
            stream_sid: The Twilio stream SID for sending audio.
        """
        self._twilio_ws = twilio_ws
        self._stream_sid = stream_sid

        model = self.settings.openai_realtime_model
        url = f"{OPENAI_REALTIME_URL}?model={model}"

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self.ws = await websockets.connect(
            url,
            additional_headers=headers,
            max_size=None,
        )
        self._is_connected = True

        logger.info(
            "OpenAI Realtime API connected",
            call_sid=self.call_sid,
            model=model,
        )

        # Configure the session
        await self._configure_session()

        # Start receiving responses from OpenAI
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _configure_session(self) -> None:
        """Configure the OpenAI Realtime session with initial settings."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.system_prompt,
                "voice": self.voice,
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "temperature": 0.7,
                "max_response_output_tokens": 500,
            },
        }

        await self.ws.send(json.dumps(session_config))
        logger.info("OpenAI Realtime session configured", call_sid=self.call_sid)

    async def send_audio(self, audio_chunk: bytes) -> None:
        """
        Send a mulaw audio chunk from Twilio to OpenAI Realtime API.

        Args:
            audio_chunk: Base64-decoded mulaw 8kHz audio from Twilio.
        """
        if not self.ws or not self._is_connected:
            return

        try:
            # OpenAI expects base64-encoded audio in the append event
            audio_b64 = base64.b64encode(audio_chunk).decode("utf-8")
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64,
            }
            await self.ws.send(json.dumps(event))
        except Exception as e:
            logger.error("Failed to send audio to OpenAI", error=str(e))

    async def inject_rag_context(self, transcript: str) -> None:
        """
        When user speech is transcribed, query RAG and update session instructions
        with relevant context so the model's next response is context-aware.

        Args:
            transcript: The transcribed user speech.
        """
        if not transcript.strip():
            return

        try:
            # Generate embedding and query Pinecone
            query_embedding = await generate_embedding(transcript)
            matches = await query_vectors(
                tenant_id=self.tenant_id,
                query_embedding=query_embedding,
                top_k=5,
                score_threshold=0.7,
            )

            if not matches:
                logger.info("No RAG context found", tenant_id=self.tenant_id)
                return

            # Build context string
            context_parts = [m["text"] for m in matches]
            context = "\n\n---\n\n".join(context_parts)

            # Update session instructions with RAG context
            updated_instructions = (
                f"{self.system_prompt}\n\n"
                f"Use the following knowledge base context to answer the user's question. "
                f"If the context doesn't contain relevant information, answer based on your "
                f"general knowledge but mention you don't have specific information in the knowledge base.\n\n"
                f"---\nContext:\n{context}\n---"
            )

            session_update = {
                "type": "session.update",
                "session": {
                    "instructions": updated_instructions,
                },
            }

            if self.ws and self._is_connected:
                await self.ws.send(json.dumps(session_update))
                logger.info(
                    "RAG context injected into session",
                    tenant_id=self.tenant_id,
                    num_chunks=len(matches),
                    top_score=matches[0]["score"],
                )

        except Exception as e:
            logger.error("RAG context injection failed", error=str(e))

    async def _receive_loop(self) -> None:
        """
        Background task that receives events from OpenAI Realtime API
        and relays audio back to Twilio.
        """
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type", "")

                if event_type == "session.created":
                    logger.info("OpenAI Realtime session created", call_sid=self.call_sid)

                elif event_type == "session.updated":
                    logger.debug("OpenAI Realtime session updated")

                elif event_type == "input_audio_buffer.speech_started":
                    logger.debug("User started speaking", call_sid=self.call_sid)
                    # Cancel any in-progress response to allow interruption
                    await self._handle_speech_started()

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.debug("User stopped speaking", call_sid=self.call_sid)

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # User's speech has been transcribed -- inject RAG context
                    transcript = event.get("transcript", "")
                    if transcript.strip():
                        logger.info(
                            "User transcript received",
                            call_sid=self.call_sid,
                            text=transcript[:100],
                        )
                        self.conversation_history.append({
                            "role": "user",
                            "content": transcript,
                        })
                        # Inject RAG context for the model's response
                        await self.inject_rag_context(transcript)

                elif event_type == "response.audio.delta":
                    # Stream audio back to Twilio
                    audio_b64 = event.get("delta", "")
                    if audio_b64 and self._twilio_ws:
                        await self._send_audio_to_twilio(audio_b64)

                elif event_type == "response.audio_transcript.done":
                    # Assistant's full response text
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(
                            "Assistant response",
                            call_sid=self.call_sid,
                            text=transcript[:100],
                        )
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": transcript,
                        })

                elif event_type == "response.done":
                    logger.debug("Response complete", call_sid=self.call_sid)

                elif event_type == "error":
                    error_data = event.get("error", {})
                    logger.error(
                        "OpenAI Realtime error",
                        call_sid=self.call_sid,
                        error_type=error_data.get("type"),
                        error_message=error_data.get("message"),
                    )

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI Realtime WebSocket closed", call_sid=self.call_sid)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("OpenAI Realtime receive error", error=str(e), call_sid=self.call_sid)
        finally:
            self._is_connected = False

    async def _handle_speech_started(self) -> None:
        """Handle user interruption by cancelling the current response."""
        try:
            if self.ws and self._is_connected:
                # Cancel the current response
                cancel_event = {"type": "response.cancel"}
                await self.ws.send(json.dumps(cancel_event))

                # Clear Twilio's audio buffer to stop playback immediately
                if self._twilio_ws and self._stream_sid:
                    clear_message = {
                        "event": "clear",
                        "streamSid": self._stream_sid,
                    }
                    await self._twilio_ws.send_text(json.dumps(clear_message))

        except Exception as e:
            logger.error("Failed to handle speech interruption", error=str(e))

    async def _send_audio_to_twilio(self, audio_b64: str) -> None:
        """Send base64 audio from OpenAI back to Twilio Media Stream."""
        try:
            if self._twilio_ws and self._stream_sid:
                media_message = {
                    "event": "media",
                    "streamSid": self._stream_sid,
                    "media": {
                        "payload": audio_b64,
                    },
                }
                await self._twilio_ws.send_text(json.dumps(media_message))
        except Exception as e:
            logger.error("Failed to send audio to Twilio", error=str(e))

    async def close(self) -> None:
        """Close the OpenAI Realtime API connection."""
        self._is_connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass

        # Trim conversation history
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        logger.info("OpenAI Realtime session closed", call_sid=self.call_sid)
