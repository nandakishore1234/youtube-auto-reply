from dataclasses import dataclass
from enum import Enum

from app.ai.moderation_schema import (
    GroundingStatus,
    ModerationAssessment,
    RiskCategory,
    UncertaintyLevel,
)


class PolicyDecision(str, Enum):
    AUTO_PUBLISH = "auto_publish"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str
    policy_version: str = "1.0.0"


# These categories always require human review in the initial policy.
MANDATORY_REVIEW_RISKS = {
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
}

SUPPORTED_INTENTS = {
    "compliment",
    "question",
    "feedback",
    "criticism",
    "spam",
    "other",
}


def evaluate_reply_policy(
    *,
    assessment: ModerationAssessment,
    reply_text: str,
) -> PolicyResult:
    """Evaluate publishing eligibility without publishing anything."""

    def review(reason: str) -> PolicyResult:
        return PolicyResult(
            decision=PolicyDecision.HUMAN_REVIEW,
            reason=reason,
        )

    # Fail closed when the proposed reply is missing.
    if not reply_text or not reply_text.strip():
        return review("Reply is empty.")

    # Reject contradictory or unsupported assessment values.
    if assessment.intent not in SUPPORTED_INTENTS:
        return review("Unsupported intent.")

    risks = set(assessment.risk_categories)

    if not risks:
        return review("No risk assessment was provided.")

    if RiskCategory.NONE in risks and len(risks) > 1:
        return review("Contradictory risk categories were provided.")

    if risks.intersection(MANDATORY_REVIEW_RISKS):
        return review("A risk category requiring human review was detected.")

    # Uncertainty must be resolved before any publishing eligibility decision.
    if assessment.uncertainty != UncertaintyLevel.LOW:
        return review("Assessment uncertainty requires human review.")

    if assessment.requires_human_review:
        return review("The moderation assessment requests human review.")

    # An unsupported or unknown factual basis is not publishable automatically.
    if assessment.grounding in {
        GroundingStatus.PARTIALLY_SUPPORTED,
        GroundingStatus.UNSUPPORTED,
        GroundingStatus.UNKNOWN,
    }:
        return review("Reply grounding is insufficient or unknown.")

    if assessment.intent in {"spam", "other"}:
        return review("This intent is not eligible for automatic publishing.")

    # Dry-run guard: this module never authorizes real publishing yet.
    return review(
        "Dry-run mode: publishing eligibility has not been enabled."
    )
