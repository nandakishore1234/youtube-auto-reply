from app.ai.moderation_schema import (
    GroundingStatus,
    ModerationAssessment,
    RiskCategory,
    UncertaintyLevel,
)
from app.ai.policies.auto_publish import (
    PolicyDecision,
    evaluate_reply_policy,
)


def make_assessment(**overrides):
    values = {
        "intent": "compliment",
        "risk_categories": [RiskCategory.NONE],
        "grounding": GroundingStatus.NOT_APPLICABLE,
        "uncertainty": UncertaintyLevel.LOW,
        "requires_human_review": False,
        "rationale": "Ordinary positive comment.",
    }
    values.update(overrides)
    return ModerationAssessment(**values)


def test_compliment_stays_in_review_during_dry_run():
    result = evaluate_reply_policy(
        assessment=make_assessment(),
        reply_text="Thanks for your comment!",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert "Dry-run" in result.reason


def test_question_stays_in_review_during_dry_run():
    result = evaluate_reply_policy(
        assessment=make_assessment(intent="question"),
        reply_text="The details are in the description.",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


def test_ordinary_criticism_is_not_mislabeled_as_a_risk():
    assessment = make_assessment(
        intent="criticism",
        rationale="Ordinary feedback.",
    )

    result = evaluate_reply_policy(
        assessment=assessment,
        reply_text="Thanks for sharing your feedback.",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert "Dry-run" in result.reason


def test_model_review_recommendation_is_enforced():
    result = evaluate_reply_policy(
        assessment=make_assessment(requires_human_review=True),
        reply_text="Thanks!",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


def test_empty_reply_requires_review():
    result = evaluate_reply_policy(
        assessment=make_assessment(),
        reply_text="   ",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert result.reason == "Reply is empty."


def test_contradictory_risk_categories_require_review():
    assessment = make_assessment(
        risk_categories=[RiskCategory.NONE, RiskCategory.THREAT],
    )

    result = evaluate_reply_policy(
        assessment=assessment,
        reply_text="Thanks!",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert "Contradictory" in result.reason


def test_unknown_grounding_requires_review():
    result = evaluate_reply_policy(
        assessment=make_assessment(grounding=GroundingStatus.UNKNOWN),
        reply_text="This happened in 1998.",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


def test_unknown_intent_is_rejected_by_schema():
    try:
        make_assessment(intent="unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported intent should fail schema validation")
