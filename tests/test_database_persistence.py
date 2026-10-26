from uuid import uuid4

from sqlalchemy import select

from tests.db_test_utils import create_test_session
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft


def test_reply_draft_persists_in_postgres():
    engine, TestSession = create_test_session()
    token = uuid4().hex

    username = f"persistence_test_{token}"
    email = f"{username}@example.test"

    try:
        with TestSession() as db:
            user = User(
                username=username,
                email=email,
                password_hash=None,
            )
            db.add(user)
            db.flush()

            channel = YouTubeChannel(
                user_id=user.id,
                youtube_channel_id=f"test_channel_{token}",
                title="Persistence Test Channel",
            )
            db.add(channel)
            db.flush()

            comment = Comment(
                youtube_channel_id=channel.id,
                youtube_comment_id=f"test_comment_{token}",
                youtube_video_id=f"test_video_{token}",
                author_display_name="Test Author",
                text="This is a persistence test.",
            )
            db.add(comment)
            db.flush()

            draft = ReplyDraft(
                comment_id=comment.id,
                reply_text="Thank you for your comment!",
                intent="positive",
                needs_human_review=True,
                status="pending_approval",
                review_reason="Test draft; human approval required.",
            )
            db.add(draft)
            db.commit()

            comment_id = comment.id
            draft_id = draft.id

        # Verify persisted data in a separate session.
        with TestSession() as db:
            saved_draft = db.get(ReplyDraft, draft_id)

            assert saved_draft is not None
            assert saved_draft.comment_id == comment_id
            assert saved_draft.reply_text == "Thank you for your comment!"
            assert saved_draft.needs_human_review is True
            assert saved_draft.status == "pending_approval"

    finally:
        # Delete only records created by this test.
        with TestSession() as db:
            user = db.scalar(
                select(User).where(User.username == username)
            )
            if user is not None:
                channel_ids = list(
                    db.scalars(
                        select(YouTubeChannel.id).where(
                            YouTubeChannel.user_id == user.id
                        )
                    )
                )
                if channel_ids:
                    comment_ids = list(
                        db.scalars(
                            select(Comment.id).where(
                                Comment.youtube_channel_id.in_(channel_ids)
                            )
                        )
                    )
                    if comment_ids:
                        db.query(ReplyDraft).filter(
                            ReplyDraft.comment_id.in_(comment_ids)
                        ).delete(synchronize_session=False)
                        db.query(Comment).filter(
                            Comment.id.in_(comment_ids)
                        ).delete(synchronize_session=False)

                    db.query(YouTubeChannel).filter(
                        YouTubeChannel.id.in_(channel_ids)
                    ).delete(synchronize_session=False)

                db.delete(user)
                db.commit()

        engine.dispose()
