
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.youtube_oauth_service import (
    create_oauth_flow,
    exchange_code_for_channel,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/youtube/oauth",
    tags=["YouTube OAuth"],
)


@router.get("/start")
def start_oauth(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        flow = create_oauth_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            code_challenge_method="S256",
        )

        # Keep the same Google state and PKCE verifier for the callback.
        request.session["youtube_oauth_user_id"] = current_user.id
        request.session["youtube_oauth_state"] = state
        request.session["youtube_oauth_code_verifier"] = (
            flow.code_verifier
        )

        return RedirectResponse(
            url=authorization_url,
            status_code=302,
        )

    except Exception as exc:
        logger.exception("Unable to start YouTube OAuth")
        raise HTTPException(
            status_code=500,
            detail="Unable to start YouTube authorization",
        ) from exc


@router.get("/start-url")
def start_oauth_url(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        flow = create_oauth_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            code_challenge_method="S256",
        )

        request.session["youtube_oauth_user_id"] = current_user.id
        request.session["youtube_oauth_state"] = state
        request.session["youtube_oauth_code_verifier"] = (
            flow.code_verifier
        )

        return {
            "authorization_url": authorization_url,
            "message": "Open authorization_url in your browser.",
        }

    except Exception as exc:
        logger.exception("Unable to create YouTube authorization URL")
        raise HTTPException(
            status_code=500,
            detail="Unable to start YouTube authorization",
        ) from exc

@router.get("/callback")
def oauth_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    expected_state = request.session.pop(
        "youtube_oauth_state", None
    )
    code_verifier = request.session.pop(
        "youtube_oauth_code_verifier", None
    )
    user_id = request.session.pop(
        "youtube_oauth_user_id", None
    )

    returned_state = request.query_params.get("state")

    if not expected_state or not code_verifier or not user_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "OAuth session missing or expired. "
                "Start authorization again."
            ),
        )

    if not returned_state or returned_state != expected_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state",
        )

    if request.query_params.get("error"):
        raise HTTPException(
            status_code=400,
            detail="Google authorization was denied",
        )

    if not request.query_params.get("code"):
        raise HTTPException(
            status_code=400,
            detail="Google did not return an authorization code",
        )

    try:
        channel = exchange_code_for_channel(
            db=db,
            user_id=int(user_id),
            authorization_response=str(request.url),
            state=expected_state,
            code_verifier=code_verifier,
        )

        return {
            "status": "connected",
            "channel": {
                "id": channel.id,
                "youtube_channel_id": channel.youtube_channel_id,
                "title": channel.title,
            },
            "message": "YouTube channel connected successfully.",
        }

    except Exception as exc:
        db.rollback()
        logger.exception("YouTube OAuth callback failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to complete YouTube authorization",
        ) from exc
