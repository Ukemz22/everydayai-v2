from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase_auth.errors import AuthError

from app.services.supabase import get_supabase

bearer_scheme = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Verifies the Supabase JWT from the Authorization header and
    returns the authenticated user's id (the `sub` claim).
    """
    token = credentials.credentials
    supabase = get_supabase()

    try:
        response = supabase.auth.get_claims(token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )

    if not response or not response.get("claims"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification returned no claims.",
        )

    user_id = response["claims"].get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim.",
        )

    return user_id


async def get_current_business(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Loads the business row belonging to the authenticated user.
    Every protected route depends on this, not get_current_user_id directly,
    since routes need the business record (plan, config, vector_store_id etc),
    not just the raw user id.
    """
    supabase = get_supabase()

    result = (
        supabase.table("businesses")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business found for this user.",
        )

    return result.data