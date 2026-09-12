"""LangGraph node functions for the voice assistant agent.

With OpenAI Realtime API handling STT/TTS for voice calls, these nodes
focus on RAG retrieval and LLM generation for text-based processing.
"""

import structlog

from app.graph.state import VoiceAgentState
from app.services.openai_service import generate_embedding, chat_completion
from app.services.pinecone_service import query_vectors

logger = structlog.get_logger()


async def retrieve_node(state: VoiceAgentState) -> dict:
    """
    Retrieve relevant context from Pinecone using the user message.

    Queries the tenant's namespace for relevant document chunks.
    """
    user_message = state.get("user_message", "")
    tenant_id = state["tenant_id"]

    if not user_message.strip():
        return {
            "retrieved_context": "",
            "has_relevant_context": False,
        }

    try:
        # Generate embedding for the query
        query_embedding = await generate_embedding(user_message)

        # Query Pinecone
        matches = await query_vectors(
            tenant_id=tenant_id,
            query_embedding=query_embedding,
            top_k=5,
            score_threshold=0.7,
        )

        if not matches:
            logger.info("No relevant context found", tenant_id=tenant_id)
            return {
                "retrieved_context": "",
                "has_relevant_context": False,
            }

        # Combine context chunks
        context_parts = []
        for match in matches:
            context_parts.append(
                f"[Source: {match['filename']}, Score: {match['score']:.2f}]\n{match['text']}"
            )

        combined_context = "\n\n---\n\n".join(context_parts)

        logger.info(
            "Context retrieved",
            tenant_id=tenant_id,
            num_chunks=len(matches),
            top_score=matches[0]["score"],
        )

        return {
            "retrieved_context": combined_context,
            "has_relevant_context": True,
        }

    except Exception as e:
        logger.error("RAG retrieval failed", error=str(e), tenant_id=tenant_id)
        return {
            "retrieved_context": "",
            "has_relevant_context": False,
        }


async def generate_node(state: VoiceAgentState) -> dict:
    """
    Generate a response using OpenAI GPT with optional RAG context.

    Uses the system prompt, conversation history, and retrieved context.
    """
    user_message = state.get("user_message", "")
    context = state.get("retrieved_context", "")
    system_prompt = state.get("system_prompt", "You are a helpful voice assistant.")
    conversation_history = state.get("conversation_history", [])

    if not user_message.strip():
        return {"llm_response": "I'm sorry, I didn't catch that. Could you please repeat?"}

    try:
        response = await chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            context=context,
            conversation_history=conversation_history,
        )

        logger.info("LLM response generated", call_sid=state.get("call_sid"), response_length=len(response))

        # Update conversation history
        updated_history = list(conversation_history)
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": response})

        # Keep only last 10 turns to manage context window
        if len(updated_history) > 20:
            updated_history = updated_history[-20:]

        return {
            "llm_response": response,
            "conversation_history": updated_history,
        }

    except Exception as e:
        logger.error("LLM generation failed", error=str(e))
        return {
            "llm_response": "I'm sorry, I'm having trouble processing your request. Please try again.",
        }
