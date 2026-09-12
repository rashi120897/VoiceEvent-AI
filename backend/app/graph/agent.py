"""LangGraph voice assistant agent definition.

With OpenAI Realtime API handling STT/TTS for live voice calls, this graph
focuses on RAG retrieval + LLM generation. It can be used for:
  - Text-based API endpoints (chat without voice)
  - Testing the RAG pipeline independently
  - Future non-voice assistant flows
"""

import structlog
from langgraph.graph import StateGraph, END

from app.graph.state import VoiceAgentState
from app.graph.nodes import (
    retrieve_node,
    generate_node,
)

logger = structlog.get_logger()


def should_retrieve(state: VoiceAgentState) -> str:
    """
    Conditional edge: decide whether to run RAG retrieval.

    Skip retrieval if user_message is empty or too short.
    """
    user_message = state.get("user_message", "").strip()
    if not user_message or len(user_message) < 3:
        return "generate"
    return "retrieve"


def build_voice_agent() -> StateGraph:
    """
    Build and compile the voice assistant LangGraph.

    Graph flow:
        (entry) -> (conditional) -> retrieve -> generate -> END
                                 -> generate -> END  (skip RAG)
    """
    graph = StateGraph(VoiceAgentState)

    # Add nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    # Set entry point with conditional edge
    graph.set_conditional_entry_point(
        should_retrieve,
        {
            "retrieve": "retrieve",
            "generate": "generate",
        },
    )

    # retrieve -> generate -> END
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Pre-compiled agent graph (singleton)
voice_agent = build_voice_agent()


async def run_voice_agent(
    user_message: str,
    tenant_id: str,
    call_sid: str = "",
    conversation_history: list[dict] | None = None,
    system_prompt: str = "",
) -> dict:
    """
    Run the voice agent graph with the given text input.

    Args:
        user_message: The user's text message (or transcript from Realtime API).
        tenant_id: The tenant's ID for RAG namespace.
        call_sid: Optional call SID for logging.
        conversation_history: Previous conversation turns.
        system_prompt: Tenant-specific system prompt.

    Returns:
        Dict with llm_response and updated conversation_history.
    """
    initial_state: VoiceAgentState = {
        "user_message": user_message,
        "tenant_id": tenant_id,
        "call_sid": call_sid,
        "retrieved_context": "",
        "has_relevant_context": False,
        "llm_response": "",
        "conversation_history": conversation_history or [],
        "system_prompt": system_prompt or "You are a helpful voice assistant. Be concise and conversational.",
    }

    logger.info("Running voice agent", call_sid=call_sid, tenant_id=tenant_id)

    result = await voice_agent.ainvoke(initial_state)

    return {
        "llm_response": result.get("llm_response", ""),
        "conversation_history": result.get("conversation_history", []),
    }
