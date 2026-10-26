from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.comment import Comment
from app.models.reply_draft import ReplyDraft
from app.models.youtube_channel import YouTubeChannel
from app.schemas.comment import CommentIngestRequest
from app.services.comment_service import generate_and_save_draft


def make_test_objects():
    comment = SimpleNamespace(
        id=123,
        youtube_channel_id=45,
        youtube_comment_id="test-comment-123",
        youtube_video_id="test-video-123",
        parent_youtube_comment_id=None,
        author_display_name="Test viewer",
        text="Great video!",
        status="received",
    )

    channel = SimpleNamespace(
        id=45,
        user_id=2,
    )

    payload = CommentIngestRequest(
        channel_id=45,
        youtube_comment_id="test-comment-123",
        youtube_video_id="test-video-123",
        parent_youtube_comment_id=None,
        author_display_name="Test viewer",
        text="Great video!",
        channel_tone="Friendly, natural, and respectful",
    )

    return comment, channel, payload


def test_missing_graph_draft_marks_comment_failed():
    comment, channel, payload = make_test_objects()
    db = MagicMock()

    # No existing draft; channel lookup succeeds.
    db.scalar.return_value = None
    db.get.side_effect = [channel, comment]

    # Simulate a graph that stopped early without generating a draft.
    graph_result = {
        "draft": None,
        "error": None,
        "needs_review": True,
    }

    with patch(
        "app.ai.graph.reply_graph.invoke",
        return_value=graph_result,
    ):
        with pytest.raises(
            RuntimeError,
            match="LangGraph completed without generating a reply",
        ):
            generate_and_save_draft(
                db=db,
                comment=comment,
                payload=payload,
            )

    assert comment.status == "generation_failed"
    db.rollback.assert_called_once()
    db.add.assert_not_called()


def test_graph_error_marks_comment_failed():
    comment, channel, payload = make_test_objects()
    db = MagicMock()

    db.scalar.return_value = None
    db.get.side_effect = [channel, comment]

    graph_result = {
        "draft": None,
        "error": "Comment could not be loaded",
        "needs_review": True,
    }

    with patch(
        "app.ai.graph.reply_graph.invoke",
        return_value=graph_result,
    ):
        with pytest.raises(
            RuntimeError,
            match="Comment could not be loaded",
        ):
            generate_and_save_draft(
                db=db,
                comment=comment,
                payload=payload,
            )

    assert comment.status == "generation_failed"
    db.rollback.assert_called_once()
    db.add.assert_not_called()
