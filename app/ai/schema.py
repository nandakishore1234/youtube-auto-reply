
from pydantic import BaseModel, Field
from typing import Literal


class ReplyDraft(BaseModel):
    reply: str = Field(
        description="The suggested public reply to the YouTube comment."
    )

    intent: Literal[
        "compliment",
        "question",
        "feedback",
        "criticism",
        "spam",
        "other",
    ] = Field(
        description="The primary intent of the incoming comment."
    )

    needs_human_review: bool = Field(
        description="Whether a human must review this draft before publishing."
    )

    reason: str = Field(
        description="A short explanation of the classification and review decision."
    )


class ReplyDraftRequest(BaseModel):
    comment_text: str = Field(min_length=1, max_length=1000)

    video_title: str = Field(default="", max_length=500)

    video_context: str = Field(default="", max_length=3000)

    channel_tone: str = Field(
        default="Friendly, natural, and respectful",
        max_length=500,
    )

    conversation_history: str = Field(
        default="No relevant previous conversation.",
        max_length=4000,
    )
