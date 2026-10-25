
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.services.youtube_comment_service import get_youtube_client
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


def serialize_draft_row(draft: ReplyDraft, comment: Comment, channel: YouTubeChannel):
    return {
        "id": draft.id,
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
        "youtube_reply_id": draft.youtube_reply_id,
        "published_at": draft.published_at,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


def list_owned_drafts_by_status(
    db: Session,
    user_id: int,
    status: str,
    channel_id: int | None = None,
):
    statement = (
        select(ReplyDraft, Comment, YouTubeChannel)
        .join(Comment, ReplyDraft.comment_id == Comment.id)
        .join(
            YouTubeChannel,
            Comment.youtube_channel_id == YouTubeChannel.id,
        )
        .where(
            YouTubeChannel.user_id == user_id,
            ReplyDraft.status == status,
        )
        .order_by(ReplyDraft.updated_at.desc())
    )

    if channel_id is not None:
        statement = statement.where(YouTubeChannel.id == channel_id)

    if status == "pending_approval":
        statement = statement.where(ReplyDraft.needs_human_review.is_(True))

    rows = db.execute(statement).all()
    return [
        serialize_draft_row(draft, comment, channel)
        for draft, comment, channel in rows
    ]


@router.get("/pending")
def list_pending_drafts(
    channel_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List pending drafts belonging only to the logged-in user."""
    return list_owned_drafts_by_status(
        db=db,
        user_id=current_user.id,
        status="pending_approval",
        channel_id=channel_id,
    )


@router.get("/published")
def list_published_drafts(
    channel_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List approved/published replies belonging to the logged-in user."""
    return list_owned_drafts_by_status(
        db=db,
        user_id=current_user.id,
        status="published",
        channel_id=channel_id,
    )


@router.get("/rejected")
def list_rejected_drafts(
    channel_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List rejected drafts belonging to the logged-in user."""
    return list_owned_drafts_by_status(
        db=db,
        user_id=current_user.id,
        status="rejected",
        channel_id=channel_id,
    )


@router.post("/{draft_id}/approve")
def approve_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve the draft and publish it as a YouTube reply."""
    draft = get_owned_draft(db, draft_id, current_user.id)

    if draft.youtube_reply_id:
        raise HTTPException(
            status_code=409,
            detail="This draft has already been published",
        )

    if draft.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Draft cannot be published from status '{draft.status}'",
        )

    comment = db.get(Comment, draft.comment_id)

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Original comment not found",
        )

    try:
        youtube, _ = get_youtube_client(
            db=db,
            channel_id=comment.youtube_channel_id,
            user_id=current_user.id,
        )

        response = youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": comment.youtube_comment_id,
                    "textOriginal": draft.reply_text,
                }
            },
        ).execute()

        youtube_reply_id = response.get("id")

        if not youtube_reply_id:
            raise RuntimeError("YouTube did not return a reply ID")

        draft.status = "published"
        draft.needs_human_review = False
        draft.youtube_reply_id = youtube_reply_id
        draft.published_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(draft)

        return {
            "id": draft.id,
            "status": draft.status,
            "published": True,
            "youtube_reply_id": draft.youtube_reply_id,
            "message": "Reply published to YouTube successfully.",
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "YouTube reply publishing failed for draft_id=%s",
            draft_id,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to publish reply to YouTube",
        ) from exc


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
        "id": draft.id,
        "status": draft.status,
        "published": False,
        "message": "Draft rejected. Nothing was published to YouTube.",
    }
