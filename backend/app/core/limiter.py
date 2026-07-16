from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def rate_limit_key(request: Request) -> str:
    """
    Identifies who is making the request, for rate-limit counting.

    If the request already went through auth (get_current_business set
    request.state.business_id), we key on that so limits apply per
    business account regardless of which device/IP they use.

    If there's no business_id yet (e.g. unauthenticated routes, or
    routes we haven't wired auth into yet), we fall back to IP address.
    """
    business_id = getattr(request.state, "business_id", None)
    if business_id:
        return f"business:{business_id}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=get_settings().REDIS_URL,
)
