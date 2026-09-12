"""Document processing service: parsing, chunking, and embedding."""

import uuid
import structlog
from io import BytesIO

from pypdf import PdfReader
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.openai_service import generate_embeddings
from app.services.pinecone_service import upsert_vectors, delete_document_vectors
from app.db.supabase import get_supabase

logger = structlog.get_logger()

# Text splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = DocxDocument(BytesIO(file_bytes))
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    return "\n\n".join(text_parts)


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a plain text file."""
    return file_bytes.decode("utf-8", errors="ignore")


EXTRACTORS = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "txt": extract_text_from_txt,
}

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def get_file_type(filename: str) -> str | None:
    """Get the file type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext if ext in ALLOWED_EXTENSIONS else None


async def process_document(
    tenant_id: str,
    document_id: str,
    filename: str,
    file_bytes: bytes,
    file_type: str,
) -> int:
    """
    Process a document: extract text, chunk, embed, and store in Pinecone.

    Args:
        tenant_id: The tenant's ID.
        document_id: The document's ID in Supabase.
        filename: Original filename.
        file_bytes: Raw file bytes.
        file_type: File extension (pdf, docx, txt).

    Returns:
        Number of chunks created.
    """
    supabase = get_supabase()

    try:
        # 1. Extract text
        extractor = EXTRACTORS.get(file_type)
        if not extractor:
            raise ValueError(f"Unsupported file type: {file_type}")

        text = extractor(file_bytes)
        if not text.strip():
            raise ValueError("No text content could be extracted from the document")

        logger.info("Text extracted", document_id=document_id, text_length=len(text))

        # 2. Chunk text
        chunks = text_splitter.split_text(text)
        if not chunks:
            raise ValueError("Document produced no text chunks")

        logger.info("Text chunked", document_id=document_id, chunk_count=len(chunks))

        # 3. Generate embeddings (batch)
        # Process in batches of 50 to avoid API limits
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            embeddings = await generate_embeddings(batch)
            all_embeddings.extend(embeddings)

        # 4. Prepare vectors for Pinecone
        vectors = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            vector_id = f"{document_id}_{idx}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": idx,
                    "text": chunk,
                },
            })

        # 5. Upsert to Pinecone
        await upsert_vectors(tenant_id, vectors)

        # 6. Update document status in Supabase
        supabase.table("documents").update({
            "status": "ready",
            "chunk_count": len(chunks),
        }).eq("id", document_id).execute()

        logger.info(
            "Document processed successfully",
            tenant_id=tenant_id,
            document_id=document_id,
            chunk_count=len(chunks),
        )
        return len(chunks)

    except Exception as e:
        logger.error(
            "Document processing failed",
            tenant_id=tenant_id,
            document_id=document_id,
            error=str(e),
        )
        # Update document status to error
        supabase.table("documents").update({
            "status": "error",
            "error_message": str(e),
        }).eq("id", document_id).execute()
        raise


async def delete_document(tenant_id: str, document_id: str) -> None:
    """
    Delete a document and its vectors.

    Args:
        tenant_id: The tenant's ID.
        document_id: The document's ID.
    """
    supabase = get_supabase()

    # Delete vectors from Pinecone
    await delete_document_vectors(tenant_id, document_id)

    # Delete document record from Supabase
    supabase.table("documents").delete().eq("id", document_id).eq("tenant_id", tenant_id).execute()

    logger.info("Document deleted", tenant_id=tenant_id, document_id=document_id)
