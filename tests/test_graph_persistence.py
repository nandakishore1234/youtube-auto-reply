
from sqlalchemy import select

from app.database import SessionLocal
from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft
from app.models.youtube_channel import YouTubeChannel
from app.schemas.comment import CommentIngestRequest
from app.services.comment_service import generate_and_save_draft


USER_ID = 2
CHANNEL_ID = 2
COMMENT_ID = 2


def main():
    db = SessionLocal()

    try:
        comment = (
            db.query(Comment)
            .join(
                YouTubeChannel,
                Comment.youtube_channel_id == YouTubeChannel.id,
            )
            .filter(
                Comment.id == COMMENT_ID,
                Comment.youtube_channel_id == CHANNEL_ID,
                YouTubeChannel.user_id == USER_ID,
            )
            .first()
        )

        if comment is None:
            raise ValueError(
                "Test comment not found or channel access denied"
            )

        payload = CommentIngestRequest(
            channel_id=CHANNEL_ID,
            youtube_comment_id=comment.youtube_comment_id,
            youtube_video_id=comment.youtube_video_id,
            parent_youtube_comment_id=comment.parent_youtube_comment_id,
            author_display_name=comment.author_display_name,
            text=comment.text,
            channel_tone="Friendly, natural, and respectful",
        )

        # Reuse an existing draft if one already exists.
        draft = db.scalar(
            select(ReplyDraft).where(
                ReplyDraft.comment_id == comment.id
            )
        )

        if draft is None:
            draft = generate_and_save_draft(
                db=db,
                comment=comment,
                payload=payload,
            )
            print("Created a new draft.")
        else:
            print("A draft already exists; no duplicate created.")

        # Refresh persisted values before checking.
        db.refresh(draft)
        db.refresh(comment)

        print("\n--- Persistence Test Result ---")
        print("Comment ID:", comment.id)
        print("Draft ID:", draft.id)
        print("Reply:", draft.reply_text)
        print("Intent:", draft.intent)
        print("Draft status:", draft.status)
        print("Human review required:", draft.needs_human_review)
        print("Comment status:", comment.status)

        assert draft.status == "pending_approval"
        assert draft.needs_human_review is True
        assert draft.comment_id == comment.id
        assert comment.status == "draft_ready"

        print("\nPASS: Draft is persisted and requires human approval.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
