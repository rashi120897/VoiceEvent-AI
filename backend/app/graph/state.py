"""LangGraph state schema for the voice assistant agent.

With OpenAI Realtime API handling STT/TTS natively for voice calls,
this graph is primarily used for:
  - Non-realtime RAG + LLM text processing
  - Testing/debugging the RAG pipeline
  - Future API-based (non-voice) assistant endpoints
"""

from typing import TypedDict


class VoiceAgentState(TypedDict):
    """State that flows through the voice agent graph."""

    # Input
    user_message: str  # User text (from Realtime API transcript or direct text)
    tenant_id: str
    call_sid: str

    # RAG output
    retrieved_context: str  # Combined context from Pinecone
    has_relevant_context: bool  # Whether RAG found relevant docs

    # LLM output
    llm_response: str  # Generated response text

    # Conversation state
    conversation_history: list[dict]  # [{role: "user"/"assistant", content: "..."}]
    system_prompt: str  # Tenant-specific system prompt
