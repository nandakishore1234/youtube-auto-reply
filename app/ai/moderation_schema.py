from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskCategory(str, Enum):
    NONE = "none"
    SPAM = "spam"
    HARASSMENT = "harassment"
    THREAT = "threat"
    SENSITIVE_PERSONAL_DATA = "sensitive_personal_data"
    SERIOUS_ALLEGATION = "serious_allegation"
    SELF_HARM = "self_harm"
    DANGEROUS_REQUEST = "dangerous_request"
    LEGAL_OR_FINANCIAL = "legal_or_financial"
    MEDICAL = "medical"
    PROMPT_INJECTION = "prompt_injection"
    COPYRIGHT_OR_POLICY_DISPUTE = "copyright_or_policy_dispute"
    OTHER = "other"


class GroundingStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class UncertaintyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModerationAssessment(BaseModel):
    """Structured assessment of a comment and its proposed reply.

    This is an assessment, not permission to publish.
    """

    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "compliment",
        "question",
        "feedback",
        "criticism",
        "spam",
        "other",
    ] = Field(description="Primary intent of the comment.")

    risk_categories: list[RiskCategory] = Field(
        min_length=1,
        description=(
            "Detected risk categories. Use none only when no listed risk "
            "is detected. Include every applicable category."
        ),
    )

    grounding: GroundingStatus = Field(
        description="Whether factual claims in the proposed reply are supported by available context."
    )

    uncertainty: UncertaintyLevel = Field(
        description="How uncertain the assessment is, not a calibrated probability."
    )

    requires_human_review: bool = Field(
        description="Whether the case should be reviewed by a person."
    )

    rationale: str = Field(
        min_length=1,
        max_length=1000,
        description="Brief explanation of the detected risks and uncertainty.",
    )
