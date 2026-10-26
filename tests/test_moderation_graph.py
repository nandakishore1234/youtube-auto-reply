from unittest.mock import patch

from app.ai.graph import moderate_reply, validate_reply
from app.ai.moderation_schema import (
    GroundingStatus,
    ModerationAssessment,
    RiskCategory,
    UncertaintyLevel,
)
from app.ai.schema import ReplyDraft


def make_draft():
    return ReplyDraft(
        reply="Thanks for watching!",
        intent="compliment",
        needs_human_review=False,
        reason="Positive feedback.",
    )


def make_safe_assessment():
    return ModerationAssessment(
        intent="compliment",
        risk_categories=[RiskCategory.NONE],
        grounding=GroundingStatus.SUPPORTED,
        uncertainty=UncertaintyLevel.LOW,
        requires_human_review=False,
        rationale="No identified risk; reply is supported.",
    )


def make_state():
    return {
        "comment_text": "Great video!",
        "video_title": "Gameplay",
        "video_context": "A gameplay video.",
        "draft": make_draft(),
        "assessment": None,
        "moderation_error": None,
        "policy_reason": None,
        "needs_review": True,
        "error": None,
    }


def test_moderation_success_returns_assessment():
    state = make_state()
    assessment = make_safe_assessment()

    with patch(
        "app.ai.graph.assess_reply",
        return_value=assessment,
    ) as mock_assess:
        result = moderate_reply(state)

    assert result["assessment"] == assessment
    assert result["moderation_error"] is None
    mock_assess.assert_called_once_with(
        comment_text="Great video!",
        video_title="Gameplay",
        video_context="A gameplay video.",
        reply_text="Thanks for watching!",
    )


def test_moderation_failure_fails_closed():
    state = make_state()

    with patch(
        "app.ai.graph.assess_reply",
        side_effect=RuntimeError("Model unavailable"),
    ):
        result = moderate_reply(state)

    assert result["assessment"] is None
    assert result["needs_review"] is True
    assert result["moderation_error"] == (
        "Moderation failed. Human review is required."
    )


def test_moderation_without_draft_fails_closed():
    state = make_state()
    state["draft"] = None

    result = moderate_reply(state)

    assert result["assessment"] is None
    assert result["needs_review"] is True
    assert result["moderation_error"] == (
        "No draft available for moderation."
    )


def test_validation_without_assessment_requires_review():
    state = make_state()

    result = validate_reply(state)

    assert result["needs_review"] is True
    assert result["policy_reason"] == (
        "No valid moderation assessment is available."
    )


def test_valid_assessment_still_does_not_enable_publishing():
    state = make_state()
    state["assessment"] = make_safe_assessment()

    result = validate_reply(state)

    assert result["needs_review"] is True
    assert result["policy_reason"] == (
        "Dry-run mode: publishing eligibility has not been enabled."
    )

from app.ai.graph import (
    route_after_comment_load,
    route_after_video_load,
)


def test_comment_load_error_stops_workflow():
    assert route_after_comment_load(
        {"error": "Comment not found"}
    ) == "stop"


def test_successful_comment_load_continues():
    assert route_after_comment_load(
        {"error": None}
    ) == "continue"


def test_video_load_error_stops_workflow():
    assert route_after_video_load(
        {
            "error": "Video details could not be retrieved",
            "needs_review": True,
        }
    ) == "stop"


def test_video_load_review_flag_stops_workflow():
    assert route_after_video_load(
        {
            "error": None,
            "needs_review": True,
        }
    ) == "stop"


def test_video_load_success_continues():
    assert route_after_video_load(
        {
            "error": None,
            "needs_review": False,
        }
    ) == "continue"