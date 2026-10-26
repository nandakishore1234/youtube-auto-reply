
from dataclasses import dataclass
from enum import Enum


class PolicyDecision(str, Enum):
    AUTO_PUBLISH = "auto_publish"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str


RISKY_INTENTS = {"spam"}
REVIEW_REQUIRED_INTENTS = {"criticism", "other"}


def evaluate_reply_policy(
    *,
    intent: str,
    needs_human_review: bool,
    reply_text: str,
    reason: str = "",
) -> PolicyResult:
    """
    Decide whether a reply is eligible for automatic publishing.

    This function only evaluates eligibility. It never publishes anything.
    """
    if not reply_text or not reply_text.strip():
        return PolicyResult(
            PolicyDecision.HUMAN_REVIEW,
            "Reply is empty.",
        )

    normalized_intent = intent.strip().lower()

    if needs_human_review:
        return PolicyResult(
            PolicyDecision.HUMAN_REVIEW,
            reason or "The model flagged this reply for review.",
        )

    if normalized_intent in RISKY_INTENTS:
        return PolicyResult(
            PolicyDecision.HUMAN_REVIEW,
            "Spam or suspicious promotion requires review.",
        )

    if normalized_intent in REVIEW_REQUIRED_INTENTS:
        return PolicyResult(
            PolicyDecision.HUMAN_REVIEW,
            f"Intent '{normalized_intent}' requires review under the initial policy.",
        )

    if normalized_intent not in {"compliment", "question", "feedback"}:
        return PolicyResult(
            PolicyDecision.HUMAN_REVIEW,
            f"Unknown or unsupported intent: {normalized_intent!r}.",
        )

    return PolicyResult(
        PolicyDecision.HUMAN_REVIEW,
        "Dry-run only: automatic publishing is not enabled.",
    )
