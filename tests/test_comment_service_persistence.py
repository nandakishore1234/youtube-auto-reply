from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select

from tests.db_test_utils import create_test_session
from app.models.user import User
from app.models.youtube_channel import YouTubeChannel
from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft
from app.schemas.comment import CommentIngestRequest
from app.services.comment_service import generate_and_save_draft


def test_service_saves_generated_draft():
    engine, Session = create_test_session()
    token = uuid4().hex

    try:
        with Session() as db:
            user = User(
                username=f"svc_{token}",
                email=f"svc_{token}@example.test",
            )
            db.add(user)
            db.flush()

            channel = YouTubeChannel(
                user_id=user.id,
                youtube_channel_id=f"channel_{token}",
                title="Test Channel",
            )
            db.add(channel)
            db.flush()

            comment = Comment(
                youtube_channel_id=channel.id,
                youtube_comment_id=f"comment_{token}",
                youtube_video_id=f"video_{token}",
                text="Great video!",
                status="received",
            )
            db.add(comment)
            db.commit()

            comment_id = comment.id
            channel_id = channel.id
            user_id = user.id

            payload = CommentIngestRequest(
                channel_id=channel_id,
                youtube_comment_id=comment.youtube_comment_id,
                youtube_video_id=comment.youtube_video_id,
                text=comment.text,
                channel_tone="Friendly and respectful",
            )

            graph_result = {
                "draft": SimpleNamespace(
                    reply="Thank you for watching!",
                    intent="positive",
                    reason="",
                ),
                "error": None,
                "policy_reason": "Dry-run: human approval required.",
            }

            with patch(
                "app.ai.graph.reply_graph.invoke",
                return_value=graph_result,
            ) as mock_invoke:
                draft = generate_and_save_draft(db, comment, payload)

            assert draft.reply_text == "Thank you for watching!"
            assert draft.status == "pending_approval"
            assert draft.needs_human_review is True
            assert draft.review_reason == "Dry-run: human approval required."
            assert comment.status == "draft_ready"
            mock_invoke.assert_called_once()

        # A new session proves the draft was committed.
        with Session() as db:
            saved = db.scalar(
                select(ReplyDraft).where(
                    ReplyDraft.comment_id == comment_id
                )
            )
            assert saved is not None
            assert saved.reply_text == "Thank you for watching!"
            assert saved.status == "pending_approval"

    finally:
        with Session() as db:
            user = db.scalar(
                select(User).where(User.username == f"svc_{token}")
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


def test_existing_draft_is_returned_without_regeneration():
    engine, Session = create_test_session()
    token = uuid4().hex

    try:
        with Session() as db:
            user = User(
                username=f"dup_{token}",
                email=f"dup_{token}@example.test",
            )
            db.add(user)
            db.flush()

            channel = YouTubeChannel(
                user_id=user.id,
                youtube_channel_id=f"channel_{token}",
            )
            db.add(channel)
            db.flush()

            comment = Comment(
                youtube_channel_id=channel.id,
                youtube_comment_id=f"comment_{token}",
                youtube_video_id=f"video_{token}",
                text="Nice video!",
                status="draft_ready",
            )
            db.add(comment)
            db.flush()

            existing = ReplyDraft(
                comment_id=comment.id,
                reply_text="Previously saved reply",
                intent="positive",
                needs_human_review=True,
                status="pending_approval",
                review_reason="Waiting for approval",
            )
            db.add(existing)
            db.commit()

            existing_id = existing.id

            payload = CommentIngestRequest(
                channel_id=channel.id,
                youtube_comment_id=comment.youtube_comment_id,
                youtube_video_id=comment.youtube_video_id,
                text=comment.text,
                channel_tone="Friendly and respectful",
            )

            with patch(
                "app.ai.graph.reply_graph.invoke"
            ) as mock_invoke:
                result = generate_and_save_draft(db, comment, payload)

            assert result.id == existing_id
            assert result.reply_text == "Previously saved reply"
            mock_invoke.assert_not_called()

    finally:
        with Session() as db:
            user = db.scalar(
                select(User).where(User.username == f"dup_{token}")
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


def test_graph_failure_persists_failed_status_without_draft():
    engine, Session = create_test_session()
    token = uuid4().hex

    try:
        with Session() as db:
            user = User(
                username=f"fail_{token}",
                email=f"fail_{token}@example.test",
            )
            db.add(user)
            db.flush()

            channel = YouTubeChannel(
                user_id=user.id,
                youtube_channel_id=f"channel_{token}",
            )
            db.add(channel)
            db.flush()

            comment = Comment(
                youtube_channel_id=channel.id,
                youtube_comment_id=f"comment_{token}",
                youtube_video_id=f"video_{token}",
                text="Please explain this video.",
                status="received",
            )
            db.add(comment)
            db.commit()

            comment_id = comment.id
            channel_id = channel.id

            payload = CommentIngestRequest(
                channel_id=channel_id,
                youtube_comment_id=comment.youtube_comment_id,
                youtube_video_id=comment.youtube_video_id,
                text=comment.text,
                channel_tone="Friendly and respectful",
            )

            with patch(
                "app.ai.graph.reply_graph.invoke",
                return_value={
                    "draft": None,
                    "error": "Simulated graph failure",
                    "needs_review": True,
                },
            ):
                import pytest

                with pytest.raises(
                    RuntimeError,
                    match="Simulated graph failure",
                ):
                    generate_and_save_draft(db, comment, payload)

        # Verify failure state in a fresh session.
        with Session() as db:
            saved_comment = db.get(Comment, comment_id)
            assert saved_comment is not None
            assert saved_comment.status == "generation_failed"

            saved_draft = db.scalar(
                select(ReplyDraft).where(
                    ReplyDraft.comment_id == comment_id
                )
            )
            assert saved_draft is None

    finally:
        with Session() as db:
            user = db.scalar(
                select(User).where(User.username == f"fail_{token}")
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
