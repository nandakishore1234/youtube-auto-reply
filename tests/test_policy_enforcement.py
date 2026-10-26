
import pytest

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


@pytest.mark.parametrize(
    "risk",
    [
        RiskCategory.SPAM,
        RiskCategory.HARASSMENT,
        RiskCategory.THREAT,
        RiskCategory.SENSITIVE_PERSONAL_DATA,
        RiskCategory.SERIOUS_ALLEGATION,
        RiskCategory.SELF_HARM,
        RiskCategory.DANGEROUS_REQUEST,
        RiskCategory.LEGAL_OR_FINANCIAL,
        RiskCategory.MEDICAL,
        RiskCategory.PROMPT_INJECTION,
        RiskCategory.COPYRIGHT_OR_POLICY_DISPUTE,
        RiskCategory.OTHER,
    ],
)
def test_risky_categories_require_human_review(risk):
    assessment = make_assessment(risk_categories=[risk])

    result = evaluate_reply_policy(
        assessment=assessment,
        reply_text="Thanks for your comment.",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


@pytest.mark.parametrize(
    "uncertainty",
    [UncertaintyLevel.MEDIUM, UncertaintyLevel.HIGH],
)
def test_uncertain_assessment_requires_review(uncertainty):
    result = evaluate_reply_policy(
        assessment=make_assessment(uncertainty=uncertainty),
        reply_text="Thanks for watching!",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


@pytest.mark.parametrize(
    "grounding",
    [
        GroundingStatus.PARTIALLY_SUPPORTED,
        GroundingStatus.UNSUPPORTED,
        GroundingStatus.UNKNOWN,
    ],
)
def test_insufficient_grounding_requires_review(grounding):
    result = evaluate_reply_policy(
        assessment=make_assessment(grounding=grounding),
        reply_text="The event happened in 1998.",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW


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


def test_clean_reply_still_cannot_be_published_in_dry_run():
    result = evaluate_reply_policy(
        assessment=make_assessment(),
        reply_text="Thanks for watching!",
    )

    assert result.decision == PolicyDecision.HUMAN_REVIEW
    assert "Dry-run" in result.reason
