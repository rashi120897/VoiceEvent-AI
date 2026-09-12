"""Document upload and management API routes."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status

from app.api.middleware.auth import authenticate_api_key
from app.db.supabase import get_supabase
from app.services.document_service import (
    process_document,
    delete_document,
    get_file_type,
    ALLOWED_EXTENSIONS,
)
from app.models.document import DocumentResponse, DocumentListResponse

logger = structlog.get_logger()
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Depends(authenticate_api_key),
):
    """
    Upload a document to the knowledge base.

    Supports PDF, DOCX, and TXT files up to 50MB.
    Document processing (chunking, embedding) happens in the background.
    """
    # Validate file type
    file_type = get_file_type(file.filename or "")
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    supabase = get_supabase()

    # Create document record with 'processing' status
    doc_result = (
        supabase.table("documents")
        .insert({
            "tenant_id": tenant_id,
            "filename": file.filename,
            "file_type": file_type,
            "file_size_bytes": file_size,
            "status": "processing",
        })
        .execute()
    )

    doc = doc_result.data[0]

    # Process document in background
    background_tasks.add_task(
        process_document,
        tenant_id=tenant_id,
        document_id=doc["id"],
        filename=file.filename,
        file_bytes=file_bytes,
        file_type=file_type,
    )

    logger.info(
        "Document upload accepted",
        tenant_id=tenant_id,
        document_id=doc["id"],
        filename=file.filename,
    )

    return DocumentResponse(
        id=doc["id"],
        tenant_id=doc["tenant_id"],
        filename=doc["filename"],
        file_type=doc["file_type"],
        file_size_bytes=doc["file_size_bytes"],
        chunk_count=doc["chunk_count"],
        status=doc["status"],
        error_message=doc.get("error_message"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: str = Depends(authenticate_api_key),
):
    """List all documents for the current tenant."""
    supabase = get_supabase()

    result = (
        supabase.table("documents")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    documents = [DocumentResponse(**doc) for doc in result.data]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    tenant_id: str = Depends(authenticate_api_key),
):
    """Get a specific document's details."""
    supabase = get_supabase()

    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(**result.data[0])


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    document_id: str,
    tenant_id: str = Depends(authenticate_api_key),
):
    """Delete a document and its vector embeddings."""
    supabase = get_supabase()

    # Verify document belongs to tenant
    result = (
        supabase.table("documents")
        .select("id")
        .eq("id", document_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_document(tenant_id, document_id)
    logger.info("Document deleted via API", tenant_id=tenant_id, document_id=document_id)
