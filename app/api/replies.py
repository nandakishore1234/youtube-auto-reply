
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.schema import ReplyDraftRequest
from app.auth import get_current_user
from app.database import get_db
from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.services.reply_service import create_draft

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/replies",
    tags=["Replies"],
)


def get_owned_draft(
    db: Session,
    draft_id: int,
    user_id: int,
) -> ReplyDraft:
    """Return a draft only when its channel belongs to this user."""
    statement = (
        select(ReplyDraft)
        .join(Comment, ReplyDraft.comment_id == Comment.id)
        .join(
            YouTubeChannel,
            Comment.youtube_channel_id == YouTubeChannel.id,
        )
        .where(
            ReplyDraft.id == draft_id,
            YouTubeChannel.user_id == user_id,
        )
    )

    draft = db.scalar(statement)

    if draft is None:
        # Do not reveal whether another user's draft exists.
        raise HTTPException(
            status_code=404,
            detail="Reply draft not found",
        )

    return draft


@router.post("/draft")
def draft_reply(
    request: ReplyDraftRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a draft; this endpoint does not publish anything."""
    try:
        result = create_draft(request)
        return result
    except Exception as exc:
        logger.exception(
            "Draft generation failed for user_id=%s",
            current_user.id,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a reply draft",
        ) from exc


@router.get("/pending")
def list_pending_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List pending drafts belonging only to the logged-in user."""
    statement = (
        select(ReplyDraft, Comment, YouTubeChannel)
        .join(Comment, ReplyDraft.comment_id == Comment.id)
        .join(
            YouTubeChannel,
            Comment.youtube_channel_id == YouTubeChannel.id,
        )
        .where(
            YouTubeChannel.user_id == current_user.id,
            ReplyDraft.status == "pending_approval",
            ReplyDraft.needs_human_review.is_(True),
        )
        .order_by(ReplyDraft.created_at.desc())
    )

    rows = db.execute(statement).all()

    return [
        {
            "draft_id": draft.id,
            "channel_id": channel.id,
            "channel_title": channel.title,
            "youtube_video_id": comment.youtube_video_id,
            "youtube_comment_id": comment.youtube_comment_id,
            "author": comment.author_display_name,
            "comment_text": comment.text,
            "reply_text": draft.reply_text,
            "intent": draft.intent,
            "review_reason": draft.review_reason,
            "status": draft.status,
        }
        for draft, comment, channel in rows
    ]


@router.post("/{draft_id}/approve")
def approve_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve an owned draft without publishing it."""
    draft = get_owned_draft(db, draft_id, current_user.id)

    if draft.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Draft cannot be approved from status '{draft.status}'",
        )

    draft.status = "approved"
    draft.needs_human_review = False

    db.commit()
    db.refresh(draft)

    return {
        "draft_id": draft.id,
        "status": draft.status,
        "published": False,
        "message": "Draft approved. It has not been published to YouTube.",
    }


@router.post("/{draft_id}/reject")
def reject_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject an owned draft without publishing it."""
    draft = get_owned_draft(db, draft_id, current_user.id)

    if draft.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Draft cannot be rejected from status '{draft.status}'",
        )

    draft.status = "rejected"
    draft.needs_human_review = False

    db.commit()
    db.refresh(draft)

    return {
        "draft_id": draft.id,
        "status": draft.status,
        "published": False,
        "message": "Draft rejected. Nothing was published to YouTube.",
    }
