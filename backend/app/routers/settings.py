from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import get_current_business
from app.services.supabase import get_supabase
from app.validators.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(business: dict = Depends(get_current_business)):
    return business


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    business: dict = Depends(get_current_business),
):
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
