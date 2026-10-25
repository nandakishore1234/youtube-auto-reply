
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.services.youtube_comment_service import (
    fetch_and_process_channel_comments,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/channels",
    tags=["Channels"],
)


@router.get("")
def list_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channels = db.scalars(
        select(YouTubeChannel)
        .where(YouTubeChannel.user_id == current_user.id)
        .order_by(YouTubeChannel.id.desc())
    ).all()

    return [
        {
            "id": channel.id,
            "youtube_channel_id": channel.youtube_channel_id,
            "title": channel.title,
            "thumbnail_url": channel.thumbnail_url,
            "status": channel.status,
        }
        for channel in channels
    ]


@router.get("/{channel_id}")
def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channel = db.scalar(
        select(YouTubeChannel).where(
            YouTubeChannel.id == channel_id,
            YouTubeChannel.user_id == current_user.id,
        )
    )

    if channel is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not found",
        )

    return {
        "id": channel.id,
        "youtube_channel_id": channel.youtube_channel_id,
        "title": channel.title,
        "thumbnail_url": channel.thumbnail_url,
        "status": channel.status,
    }


@router.post("/{channel_id}/comments/fetch")
def fetch_channel_comments(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Confirm that this channel belongs to the authenticated user.
    channel = db.scalar(
        select(YouTubeChannel).where(
            YouTubeChannel.id == channel_id,
            YouTubeChannel.user_id == current_user.id,
        )
    )

    if channel is None:
        raise HTTPException(
            status_code=404,
            detail="Channel not found",
        )

    try:
        return fetch_and_process_channel_comments(
            db=db,
            channel_id=channel.id,
            user_id=current_user.id,
            max_videos=5,
            max_pages_per_video=1,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception(
            "YouTube comment fetch failed for channel_id=%s",
            channel_id,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch and process YouTube comments",
        ) from exc
