"""Pinecone vector database service with multi-tenant namespace isolation."""

import structlog
from pinecone import Pinecone

from app.config import Settings

logger = structlog.get_logger()

_pinecone_client: Pinecone | None = None
_index = None


def init_pinecone(settings: Settings) -> None:
    """Initialize the Pinecone client and index."""
    global _pinecone_client, _index

    _pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
    _index = _pinecone_client.Index(settings.pinecone_index_name)

    logger.info(
        "Pinecone initialized",
        index=settings.pinecone_index_name,
    )


def get_index():
    """Get the Pinecone index."""
    if _index is None:
        raise RuntimeError("Pinecone not initialized. Call init_pinecone() first.")
    return _index


async def upsert_vectors(
    tenant_id: str,
    vectors: list[dict],
) -> int:
    """
    Upsert vectors into the tenant's Pinecone namespace.

    Args:
        tenant_id: The tenant's ID (used as namespace).
        vectors: List of dicts with keys: id, values, metadata.

    Returns:
        Number of vectors upserted.
    """
    index = get_index()

    # Pinecone expects list of (id, values, metadata) tuples
    records = [
        (v["id"], v["values"], v["metadata"])
        for v in vectors
    ]

    # Batch upsert (Pinecone recommends batches of 100)
    batch_size = 100
    total_upserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        index.upsert(vectors=batch, namespace=tenant_id)
        total_upserted += len(batch)

    logger.info(
        "Vectors upserted",
        tenant_id=tenant_id,
        count=total_upserted,
    )
    return total_upserted


async def query_vectors(
    tenant_id: str,
    query_embedding: list[float],
    top_k: int = 5,
    score_threshold: float = 0.7,
) -> list[dict]:
    """
    Query vectors from the tenant's namespace.

    Args:
        tenant_id: The tenant's ID (used as namespace).
        query_embedding: The query vector.
        top_k: Number of results to return.
        score_threshold: Minimum similarity score.

    Returns:
        List of matching documents with text and scores.
    """
    index = get_index()

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=tenant_id,
        include_metadata=True,
    )

    matches = []
    for match in results.matches:
        if match.score >= score_threshold:
            matches.append({
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("text", ""),
                "document_id": match.metadata.get("document_id", ""),
                "chunk_index": match.metadata.get("chunk_index", 0),
                "filename": match.metadata.get("filename", ""),
            })

    logger.info(
        "Vector query completed",
        tenant_id=tenant_id,
        results_count=len(matches),
        top_score=matches[0]["score"] if matches else 0,
    )
    return matches


async def delete_document_vectors(
    tenant_id: str,
    document_id: str,
) -> None:
    """
    Delete all vectors for a specific document in the tenant's namespace.

    Args:
        tenant_id: The tenant's ID (used as namespace).
        document_id: The document ID whose vectors should be deleted.
    """
    index = get_index()

    # Delete by metadata filter
    index.delete(
        namespace=tenant_id,
        filter={"document_id": {"$eq": document_id}},
    )

    logger.info(
        "Document vectors deleted",
        tenant_id=tenant_id,
        document_id=document_id,
    )


async def delete_tenant_namespace(tenant_id: str) -> None:
    """Delete all vectors in a tenant's namespace."""
    index = get_index()
    index.delete(delete_all=True, namespace=tenant_id)
    logger.info("Tenant namespace deleted", tenant_id=tenant_id)
