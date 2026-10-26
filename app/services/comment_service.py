from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.schema import ReplyDraftRequest
from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft
from app.models.youtube_channel import YouTubeChannel
from app.schemas.comment import CommentIngestRequest



def get_comment_by_external_id(
    db: Session,
    channel_id: int,
    youtube_comment_id: str,
) -> Comment | None:
    statement = select(Comment).where(
        Comment.youtube_channel_id == channel_id,
        Comment.youtube_comment_id == youtube_comment_id,
    )
    return db.scalar(statement)


def ingest_comment(
    db: Session,
    payload: CommentIngestRequest,
) -> tuple[Comment, bool]:
    """Save a comment once. Return (comment, created)."""

    channel = db.get(YouTubeChannel, payload.channel_id)
    if channel is None:
        raise ValueError("Channel connection not found")

    existing = get_comment_by_external_id(
        db,
        payload.channel_id,
        payload.youtube_comment_id,
    )

    if existing is not None:
        return existing, False

    comment = Comment(
        youtube_channel_id=payload.channel_id,
        youtube_comment_id=payload.youtube_comment_id,
        youtube_video_id=payload.youtube_video_id,
        parent_youtube_comment_id=payload.parent_youtube_comment_id,
        author_display_name=payload.author_display_name,
        text=payload.text,
        status="received",
    )

    db.add(comment)

    try:
        db.commit()
        db.refresh(comment)
        return comment, True
    except IntegrityError:
        # Another request may have inserted the same comment concurrently.
        db.rollback()

        existing = get_comment_by_external_id(
            db,
            payload.channel_id,
            payload.youtube_comment_id,
        )

        if existing is not None:
            return existing, False

        raise


def generate_and_save_draft(
    db: Session,
    comment: Comment,
    payload: CommentIngestRequest,
) -> ReplyDraft:
    """Generate a draft through LangGraph and persist it."""

    existing_draft = db.scalar(
        select(ReplyDraft).where(
            ReplyDraft.comment_id == comment.id
        )
    )

    if existing_draft is not None:
        return existing_draft

    comment.status = "generating"
    db.commit()

    try:
        # Load the channel to identify its owner.
        channel = db.get(
            YouTubeChannel,
            comment.youtube_channel_id,
        )

        if channel is None:
            raise ValueError("Channel connection not found")
        from app.ai.graph import reply_graph
        # Run the LangGraph workflow.
        result = reply_graph.invoke({
            "user_id": channel.user_id,
            "channel_id": comment.youtube_channel_id,
            "comment_id": comment.id,
            "comment_text": "",
            "video_id": "",
            "video_title": "",
            "video_context": "",
            "channel_tone": payload.channel_tone,
            "request": None,
            "draft": None,
            "error": None,
            "needs_review": True,
        })

        # Stop if a graph node reported an error.
        if result.get("error"):
            raise RuntimeError(result["error"])

        generated_draft = result.get("draft")

        if generated_draft is None:
            raise RuntimeError(
                "LangGraph completed without generating a reply"
            )

        # Save the generated draft using the existing database model.
        draft = ReplyDraft(
            comment_id=comment.id,
            reply_text=generated_draft.reply,
            intent=generated_draft.intent,
            needs_human_review=True,
            status="pending_approval",
            review_reason=(
            result.get("policy_reason")
            or result.get("moderation_error")
            or generated_draft.reason
            ),
        )

        db.add(draft)
        comment.status = "draft_ready"
        db.commit()
        db.refresh(draft)

        return draft

    except Exception:
        db.rollback()

        comment = db.get(Comment, comment.id)
        if comment is not None:
            comment.status = "generation_failed"
            db.commit()

        raise