from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import FeatureFlag, get_settings
from app.core.db import engine
from app.core.errors import register_error_handlers
from app.core.features import feature_required
from app.core.logging import configure_logging
from app.core.middleware import (
    REQUEST_ID_HEADER,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import redis_client
from app.routers import (
    admin,
    analytics,
    applications,
    auth,
    candidates,
    comms,
    documents,
    health,
    interviews,
    jobs,
    offers,
    org,
    parsed_profiles,
    public_jobs,
    ratings,
    requisitions,
    users,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await redis_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # Added last so it is outermost and also covers CORS preflight responses.
    app.add_middleware(RequestIDMiddleware)

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(org.router)
    app.include_router(jobs.router)
    app.include_router(applications.router)
    app.include_router(candidates.router)
    app.include_router(documents.router)
    app.include_router(parsed_profiles.router)
    app.include_router(comms.router)
    app.include_router(ratings.router)
    app.include_router(analytics.router)
    app.include_router(admin.router)
    app.include_router(admin.audit_router)
    # Optional modules: always mounted, but answer 404 while their flag is off.
    optional: tuple[tuple[APIRouter, FeatureFlag], ...] = (
        (public_jobs.router, "public_careers"),
        (interviews.router, "interviews"),
        (offers.router, "offers"),
        (requisitions.router, "requisitions"),
    )
    for router, flag in optional:
        app.include_router(router, dependencies=[Depends(feature_required(flag))])
    return app


app = create_app()
