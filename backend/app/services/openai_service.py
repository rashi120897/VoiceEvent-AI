"""OpenAI service for embeddings and LLM calls."""

import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()

_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    settings = get_settings()
    client = get_openai_client()

    # OpenAI API supports batch embeddings
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )

    embeddings = [item.embedding for item in response.data]
    logger.info("Embeddings generated", count=len(embeddings), model=settings.openai_embedding_model)
    return embeddings


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding for a text string."""
    embeddings = await generate_embeddings([text])
    return embeddings[0]


async def chat_completion(
    system_prompt: str,
    user_message: str,
    context: str = "",
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Generate a chat completion using OpenAI GPT.

    Args:
        system_prompt: The system instruction for the assistant.
        user_message: The user's current message.
        context: Retrieved RAG context to include.
        conversation_history: Previous conversation turns.

    Returns:
        The assistant's response text.
    """
    settings = get_settings()
    client = get_openai_client()

    messages = [{"role": "system", "content": system_prompt}]

    # Add RAG context if available
    if context:
        messages.append({
            "role": "system",
            "content": f"Use the following knowledge base context to answer the user's question. If the context doesn't contain relevant information, answer based on your general knowledge but mention that you don't have specific information in the knowledge base.\n\n---\nContext:\n{context}\n---",
        })

    # Add conversation history
    if conversation_history:
        messages.extend(conversation_history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.openai_llm_model,
        messages=messages,
        temperature=0.7,
        max_tokens=500,  # Keep responses concise for voice
    )

    reply = response.choices[0].message.content
    logger.info(
        "Chat completion generated",
        model=settings.openai_llm_model,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
    return reply
