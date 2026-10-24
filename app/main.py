from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.api.replies import router as replies_router
from app.api.comments import router as comments_router
from starlette.middleware.sessions import SessionMiddleware
from app.api.youtube_oauth import router as youtube_oauth_router
from app.api.channels import router as channels_router
from app.api.auth import router as auth_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,  # Local HTTP development only
    max_age=600,
)
app.include_router(auth_router)
app.include_router(channels_router)
app.include_router(youtube_oauth_router)
app.include_router(replies_router)
app.include_router(comments_router)
@app.get("/health")
def health():
    """Confirm that the application process is running."""
    return {
        "status": "ok",
        "service": "youtube-ai-replier",
    }


def check_database() -> None:
    """Raise an exception if PostgreSQL is unavailable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@app.get("/health/ready")
def readiness():
    """Check whether the app can reach PostgreSQL."""
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

    return {
        "status": "ready",
        "database": "connected",
    }