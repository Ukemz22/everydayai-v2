from contextlib import asynccontextmanager
import sentry_sdk
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.core.limiter import limiter
from app.middleware.auth import get_current_business
from app.routers import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="EverydayAI API",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.add_middleware(SlowAPIMiddleware)

    app.include_router(settings_router.router)

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/me", tags=["Auth"])
    @limiter.limit("5/minute")
    async def me(request: Request, business: dict = Depends(get_current_business)):
        return {"business_id": business["id"], "name": business["name"]}

    return app


app = create_app()
