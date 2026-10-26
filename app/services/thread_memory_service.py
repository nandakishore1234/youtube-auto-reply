from sqlalchemy import text

from app.ai.thread_memory import summarize_thread_history
from app.database import SessionLocal
from app.models.comment import Comment
from app.models.thread_summary import ThreadSummary


SUMMARY_AFTER_MESSAGES = 10
KEEP_RECENT_MESSAGES = 5


def update_thread_summary(
    channel_id: int,
    video_id: str,
    root_comment_id: str,
) -> bool:
    """Summarize older thread messages and persist a checkpoint."""
    db = SessionLocal()

    try:
        # Serialize updates for the same channel and thread.
        # PostgreSQL releases this lock when the transaction ends.
        db.execute(
            text(
                "SELECT pg_advisory_xact_lock(hashtext(:lock_key))"
            ),
            {
                "lock_key": f"{channel_id}:{root_comment_id}"
            },
        )

        # Confirm the root comment belongs to this channel and video.
        root = (
            db.query(Comment)
            .filter(
                Comment.youtube_channel_id == channel_id,
                Comment.youtube_video_id == video_id,
                Comment.youtube_comment_id == root_comment_id,
                Comment.parent_youtube_comment_id.is_(None),
            )
            .first()
        )

        if root is None:
            return False

        # Fetch the root comment and its direct replies in chronological
        # order. The current schema stores direct parent comment IDs.
        comments = (
            db.query(Comment)
            .filter(
                Comment.youtube_channel_id == channel_id,
                Comment.youtube_video_id == video_id,
                (
                    (Comment.youtube_comment_id == root_comment_id)
                    | (
                        Comment.parent_youtube_comment_id
                        == root_comment_id
                    )
                ),
            )
            .order_by(Comment.created_at, Comment.id)
            .all()
        )

        # Lock the existing summary row, if one exists.
        summary_row = (
            db.query(ThreadSummary)
            .filter(
                ThreadSummary.youtube_channel_id == channel_id,
                ThreadSummary.root_youtube_comment_id == root_comment_id,
            )
            .with_for_update()
            .first()
        )

        checkpoint_id = (
            summary_row.summarized_through_comment_id
            if summary_row is not None
            else None
        )

        if checkpoint_id:
            checkpoint_index = next(
                (
                    index
                    for index, comment in enumerate(comments)
                    if comment.youtube_comment_id == checkpoint_id
                ),
                None,
            )

            # Don't silently rebuild a summary if its checkpoint
            # no longer exists in the fetched thread.
            if checkpoint_index is None:
                return False

            unsummarized = comments[checkpoint_index + 1:]
        else:
            unsummarized = comments

        # Keep the newest messages verbatim.
        older_messages = unsummarized[:-KEEP_RECENT_MESSAGES]

        # Wait until enough unsummarized messages have accumulated.
        if len(unsummarized) <= SUMMARY_AFTER_MESSAGES:
            return False

        if len(older_messages) < KEEP_RECENT_MESSAGES:
            return False

        existing_summary = (
            summary_row.summary or ""
            if summary_row is not None
            else ""
        )

        message_lines = [
            (
                f"Author: {comment.author_display_name or 'Unknown'}\n"
                f"Comment: {(comment.text or '')[:1000]}"
            )
            for comment in older_messages
        ]

        # The LLM must preserve existing context without inventing facts.
        new_summary = summarize_thread_history(
            existing_summary=existing_summary,
            older_messages=message_lines,
        )

        checkpoint = older_messages[-1].youtube_comment_id

        if summary_row is None:
            summary_row = ThreadSummary(
                youtube_channel_id=channel_id,
                root_youtube_comment_id=root_comment_id,
                summary=new_summary,
                summarized_through_comment_id=checkpoint,
            )
            db.add(summary_row)
        else:
            summary_row.summary = new_summary
            summary_row.summarized_through_comment_id = checkpoint

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
