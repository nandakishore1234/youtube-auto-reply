from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.ai.moderation_schema import ModerationAssessment


PROMPT_FILE = (
    Path(__file__).parent
    / "prompts"
    / "moderation_system.md"
)

MODERATION_SYSTEM_PROMPT = PROMPT_FILE.read_text(
    encoding="utf-8"
)

moderation_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", MODERATION_SYSTEM_PROMPT),
        (
            "human",
            """
Assess the following data.

<comment>
{comment_text}
</comment>

<video_title>
{video_title}
</video_title>

<video_context>
{video_context}
</video_context>

<proposed_reply>
{reply_text}
</proposed_reply>

Return the moderation assessment using the required schema.
""",
        ),
    ]
)

moderation_llm = ChatOllama(
    model="qwen2",
    temperature=0,
)

structured_moderation_llm = moderation_llm.with_structured_output(
    ModerationAssessment,
    method="json_schema",
)

moderation_chain = moderation_prompt | structured_moderation_llm


def assess_reply(
    *,
    comment_text: str,
    video_title: str,
    video_context: str,
    reply_text: str,
) -> ModerationAssessment:
    """Return a schema-validated assessment of a proposed reply."""

    result = moderation_chain.invoke(
        {
            "comment_text": comment_text,
            "video_title": video_title,
            "video_context": video_context,
            "reply_text": reply_text,
        }
    )

    if not isinstance(result, ModerationAssessment):
        raise ValueError("Moderation returned an invalid assessment")

    return result
