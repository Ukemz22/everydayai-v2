import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import get_current_business
from app.services.supabase import get_supabase
from app.validators.settings import (
    ByokRequest,
    ByokResponse,
    SettingsResponse,
    SettingsUpdate,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


async def _validate_openai_key(api_key: str) -> None:
    """
    Confirms the key actually works before we store it. OpenAI returns
    200 for a valid key, 401 for an invalid one. Any other failure
    (network issue, OpenAI outage) is surfaced as a 502 so it's clear
    the problem isn't the key itself.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=502, detail="Could not reach OpenAI to validate the key"
            )

    if resp.status_code == 401:
        raise HTTPException(status_code=400, detail="Invalid OpenAI API key")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502, detail="Unexpected response from OpenAI while validating key"
        )


@router.get("", response_model=SettingsResponse)
async def get_settings(business: dict = Depends(get_current_business)):
    """
    Returns the caller's business row. get_current_business already
    verified the JWT and loaded the row — no extra Supabase call needed.
    response_model strips any field not declared on SettingsResponse
    (e.g. openai_key_ref), so it can never leak even if added to the
    table later.
    """
    return business


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    business: dict = Depends(get_current_business),
):
    """
    Partial update — only fields actually sent in the request body
    are changed (exclude_unset=True), so omitted fields are left alone
    rather than overwritten with None.
    """
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    supabase = get_supabase()
    result = (
        supabase.table("businesses")
        .update(updates)
        .eq("id", business["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update settings")

    return result.data[0]


@router.post("/byok", response_model=ByokResponse)
async def set_byok_key(
    payload: ByokRequest,
    business: dict = Depends(get_current_business),
):
    """
    Validates the key against OpenAI first, then stores it in Vault.
    If the business already has a key (openai_key_ref is set), the
    existing vault secret is updated in place rather than creating an
    orphaned second secret.
    """
    await _validate_openai_key(payload.openai_api_key)

    supabase = get_supabase()
    existing_ref = business.get("openai_key_ref")
    rotated = existing_ref is not None

    if rotated:
        supabase.rpc(
            "vault_update_secret",
            {"secret_id": existing_ref, "new_secret_value": payload.openai_api_key},
        ).execute()
        new_ref = existing_ref
    else:
        rpc_result = supabase.rpc(
            "vault_create_secret",
            {"secret_value": payload.openai_api_key, "secret_name": None},
        ).execute()
        new_ref = rpc_result.data

    update_result = (
        supabase.table("businesses")
        .update({"openai_key_ref": new_ref})
        .eq("id", business["id"])
        .execute()
    )

    if not update_result.data:
        raise HTTPException(
            status_code=500, detail="Key stored in Vault but failed to link to business"
        )

    return ByokResponse(status="success", rotated=rotated)


@router.delete("/byok", response_model=ByokResponse)
async def delete_byok_key(business: dict = Depends(get_current_business)):
    """Removes the stored key from Vault and clears the business's reference."""
    existing_ref = business.get("openai_key_ref")

    if existing_ref is None:
        raise HTTPException(status_code=404, detail="No API key is currently stored")

    supabase = get_supabase()
    supabase.rpc("vault_delete_secret", {"secret_id": existing_ref}).execute()

    update_result = (
        supabase.table("businesses")
        .update({"openai_key_ref": None})
        .eq("id", business["id"])
        .execute()
    )

    if not update_result.data:
        raise HTTPException(status_code=500, detail="Failed to clear key reference")

    return ByokResponse(status="success", rotated=False)
