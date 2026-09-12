"""Tenant management API routes."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.supabase import get_supabase
from app.api.middleware.auth import (
    authenticate_api_key,
    generate_api_key,
    hash_api_key,
    get_key_prefix,
)
from app.models.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantWithApiKey,
    TenantSettings,
)
from app.models.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyCreated

logger = structlog.get_logger()
router = APIRouter()


@router.post("/", response_model=TenantWithApiKey, status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant_data: TenantCreate):
    """
    Create a new tenant with a default API key.

    This endpoint is NOT protected by API key auth (bootstrap endpoint).
    Returns the tenant info and the API key (shown only once).
    """
    supabase = get_supabase()

    try:
        # Create tenant
        tenant_result = (
            supabase.table("tenants")
            .insert({
                "name": tenant_data.name,
                "settings": tenant_data.settings.model_dump(),
            })
            .execute()
        )
        tenant = tenant_result.data[0]

        # Generate API key
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = get_key_prefix(raw_key)

        supabase.table("api_keys").insert({
            "tenant_id": tenant["id"],
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": "Default API Key",
        }).execute()

        logger.info("Tenant created", tenant_id=tenant["id"], name=tenant_data.name)

        return TenantWithApiKey(
            tenant=TenantResponse(
                id=tenant["id"],
                name=tenant["name"],
                settings=TenantSettings(**tenant["settings"]),
                is_active=tenant["is_active"],
                created_at=tenant["created_at"],
                updated_at=tenant["updated_at"],
            ),
            api_key=raw_key,
        )
    except Exception as e:
        logger.error("Failed to create tenant", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}",
        )


@router.get("/me", response_model=TenantResponse)
async def get_current_tenant(tenant_id: str = Depends(authenticate_api_key)):
    """Get the current tenant's information."""
    supabase = get_supabase()

    result = (
        supabase.table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    return TenantResponse(
        id=tenant["id"],
        name=tenant["name"],
        settings=TenantSettings(**tenant["settings"]),
        is_active=tenant["is_active"],
        created_at=tenant["created_at"],
        updated_at=tenant["updated_at"],
    )


@router.patch("/me", response_model=TenantResponse)
async def update_current_tenant(
    update_data: TenantUpdate,
    tenant_id: str = Depends(authenticate_api_key),
):
    """Update the current tenant's information."""
    supabase = get_supabase()

    update_fields = {}
    if update_data.name is not None:
        update_fields["name"] = update_data.name
    if update_data.settings is not None:
        update_fields["settings"] = update_data.settings.model_dump()

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        supabase.table("tenants")
        .update(update_fields)
        .eq("id", tenant_id)
        .execute()
    )

    tenant = result.data[0]
    logger.info("Tenant updated", tenant_id=tenant_id)

    return TenantResponse(
        id=tenant["id"],
        name=tenant["name"],
        settings=TenantSettings(**tenant["settings"]),
        is_active=tenant["is_active"],
        created_at=tenant["created_at"],
        updated_at=tenant["updated_at"],
    )


@router.post("/me/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    tenant_id: str = Depends(authenticate_api_key),
):
    """Generate a new API key for the current tenant."""
    supabase = get_supabase()

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = get_key_prefix(raw_key)

    result = (
        supabase.table("api_keys")
        .insert({
            "tenant_id": tenant_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": key_data.name,
        })
        .execute()
    )

    logger.info("API key created", tenant_id=tenant_id, key_name=key_data.name)

    return ApiKeyCreated(
        id=result.data[0]["id"],
        key=raw_key,
        key_prefix=key_prefix,
        name=key_data.name,
    )


@router.get("/me/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(tenant_id: str = Depends(authenticate_api_key)):
    """List all API keys for the current tenant."""
    supabase = get_supabase()

    result = (
        supabase.table("api_keys")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [ApiKeyResponse(**key) for key in result.data]


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_api_key(
    key_id: str,
    tenant_id: str = Depends(authenticate_api_key),
):
    """Deactivate an API key."""
    supabase = get_supabase()

    result = (
        supabase.table("api_keys")
        .update({"is_active": False})
        .eq("id", key_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="API key not found")

    logger.info("API key deactivated", tenant_id=tenant_id, key_id=key_id)
