import hmac

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def verify_telegram_webhook(
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> None:
    """
    Verifies that an incoming webhook request actually came from Telegram,
    not a spoofed request from someone who found the endpoint URL.

    Telegram sends the secret we configured via setWebhook back in this
    header on every real request. We compare it using a constant-time
    comparison (hmac.compare_digest) instead of `==` so that an attacker
    can't use response-timing differences to guess the secret one
    character at a time.
    """
    settings = get_settings()
    expected = settings.TELEGRAM_WEBHOOK_SECRET

    if not expected:
        # Fail loudly if we forgot to configure the secret at all,
        # rather than silently accepting every request.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram webhook secret is not configured.",
        )

    if not hmac.compare_digest(x_telegram_bot_api_secret_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook signature.",
        )
