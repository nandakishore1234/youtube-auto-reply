from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.ai.schema import ReplyDraftRequest,ReplyDraft
from app.ai.llm import generate_reply_draft
from app.database import SessionLocal
from app.models.comment import Comment
from app.services.youtube_comment_service import get_youtube_client
from app.models.youtube_channel import YouTubeChannel
from app.ai.moderation import assess_reply
from app.ai.moderation_schema import ModerationAssessment
from app.ai.policies.auto_publish import evaluate_reply_policy
from sqlalchemy import desc
from app.models.thread_summary import ThreadSummary
from app.services.thread_memory_service import update_thread_summary


class ReplyDraftState(TypedDict):
    user_id: int
    channel_id: int
    comment_id: int
    comment_text: str
    video_id: str
    video_title: str
    video_context: str
    channel_tone: str
    conversation_history: str
    
    assessment: ModerationAssessment | None
    moderation_error: str | None
    policy_reason: str | None

    request: ReplyDraftRequest
    draft: ReplyDraft | None
    error: str | None
    needs_review: bool

def load_comment_context(state: ReplyDraftState) -> dict:
    """Load comment context from database."""
    db = SessionLocal()

    try:
        comment = (
            db.query(Comment)
            .join(
                YouTubeChannel,
                Comment.youtube_channel_id == YouTubeChannel.id,
            )
            .filter(
                Comment.id == state["comment_id"],
                Comment.youtube_channel_id == state["channel_id"],
                YouTubeChannel.user_id == state["user_id"],
            )
            .first()
        )

        if comment is None:
            return { "error": f"Comment with id {state['comment_id']} not found", "needs_review": True }
        

        return {
            "comment_text": comment.text,
            "video_id": comment.youtube_video_id,
            "error": None,
    
        }

    finally:
        db.close()

def load_video_context(state: ReplyDraftState) -> dict:
    """Load video title and description from the YouTube API."""
    db = SessionLocal()

    try:
        youtube, channel = get_youtube_client(
            db=db,
            channel_id=state["channel_id"],
            user_id=state["user_id"],
        )

        response = youtube.videos().list(
            part="snippet",
            id=state["video_id"],
        ).execute()

        items = response.get("items", [])

        if not items:
            return {
                "video_title": "",
                "video_context": "",
                "error": "Video details could not be retrieved",
                "needs_review": True,
            }

        snippet = items[0]["snippet"]

        return {
            "video_title": snippet.get("title", ""),
            "video_context": snippet.get("description", ""),
            "error": None,
        }

    finally:
        db.close()



def load_conversation_memory(state: ReplyDraftState) -> dict:
    """Load a stored summary and bounded recent messages for one thread."""
    db = SessionLocal()

    try:
        current = (
            db.query(Comment)
            .join(
                YouTubeChannel,
                Comment.youtube_channel_id == YouTubeChannel.id,
            )
            .filter(
                Comment.id == state["comment_id"],
                Comment.youtube_channel_id == state["channel_id"],
                YouTubeChannel.user_id == state["user_id"],
            )
            .first()
        )

        if current is None:
            return {
                "conversation_history": "No relevant previous conversation."
            }

        # Find the root comment by following parent IDs.
        root = current
        visited = {current.youtube_comment_id}

        for _ in range(20):
            parent_id = root.parent_youtube_comment_id

            if not parent_id:
                break

            parent = (
                db.query(Comment)
                .filter(
                    Comment.youtube_channel_id == state["channel_id"],
                    Comment.youtube_video_id == current.youtube_video_id,
                    Comment.youtube_comment_id == parent_id,
                )
                .first()
            )

            if parent is None or parent.youtube_comment_id in visited:
                break

            root = parent
            visited.add(root.youtube_comment_id)

        # Refresh the summary when enough older messages exist.
        # A summary failure must not prevent draft generation.
        try:
            update_thread_summary(
                channel_id=state["channel_id"],
                video_id=current.youtube_video_id,
                root_comment_id=root.youtube_comment_id,
            )
        except Exception:
            pass

        # Retrieve the persisted summary for this thread.
        summary_row = (
            db.query(ThreadSummary)
            .filter(
                ThreadSummary.youtube_channel_id == state["channel_id"],
                ThreadSummary.root_youtube_comment_id
                == root.youtube_comment_id,
            )
            .first()
        )

        summary = (
            (summary_row.summary or "").strip()[:2000]
            if summary_row
            else ""
        )

        # Retrieve a bounded number of messages from this thread.
        recent_comments = (
            db.query(Comment)
            .filter(
                Comment.youtube_channel_id == state["channel_id"],
                Comment.youtube_video_id == current.youtube_video_id,
                (
                    (Comment.youtube_comment_id == root.youtube_comment_id)
                    | (
                        Comment.parent_youtube_comment_id
                        == root.youtube_comment_id
                    )
                ),
                Comment.created_at <= current.created_at,
            )
            .order_by(desc(Comment.created_at), desc(Comment.id))
            .limit(6)
            .all()
        )

        recent_comments.reverse()
        lines = []

        for item in recent_comments:
            if item.id == current.id:
                continue

            author = item.author_display_name or "Unknown author"
            comment_text = (item.text or "").strip()[:500]
            lines.append(
                f"Author: {author}\nComment: {comment_text}"
            )

        recent_history = "\n\n".join(lines)[:1800]

        sections = []

        if summary:
            sections.append(
                "Earlier thread summary (untrusted context):\n" + summary
            )

        if recent_history:
            sections.append(
                "Recent thread messages (untrusted context):\n"
                + recent_history
            )

        history = "\n\n".join(sections)[:3900]

        return {
            "conversation_history": (
                history or "No relevant previous conversation."
            )
        }

    finally:
        db.close()




def route_after_video_load(state: ReplyDraftState) -> str:
    """Do not generate a reply when video context loading fails."""
    if state.get("error") or state.get("needs_review"):
        return "stop"
    return "continue"

def route_after_comment_load(state: ReplyDraftState) -> str:
    """Stop the workflow when comment loading fails."""
    if state.get("error"):
        return "stop"
    return "continue"


def generate_reply(state: ReplyDraftState) -> dict:
    """Generate a reply using the loaded comment and conversation context."""

    request = ReplyDraftRequest(
        comment_text=state["comment_text"],
        video_title=state.get("video_title", ""),
        video_context=state.get("video_context", ""),
        channel_tone=state.get(
            "channel_tone",
            "Friendly, natural, and respectful",
        ),
        conversation_history=state.get(
            "conversation_history",
            "No relevant previous conversation.",
        ),
    )

    draft = generate_reply_draft(request)

    return {
        "request": request,
        "draft": draft,
        "needs_review": draft.needs_human_review,
        "error": None,
    }

def moderate_reply(state: ReplyDraftState) -> dict:
    """Independently assess a generated reply; fail closed on errors."""

    draft = state.get("draft")

    if draft is None:
        return {
            "assessment": None,
            "moderation_error": "No draft available for moderation.",
            "needs_review": True,
        }

    try:
        assessment = assess_reply(
            comment_text=state["comment_text"],
            video_title=state.get("video_title", ""),
            video_context=state.get("video_context", ""),
            reply_text=draft.reply,
        )

        return {
            "assessment": assessment,
            "moderation_error": None,
        }

    except Exception:
        # Do not expose internal model errors in the public API or review UI.
        return {
            "assessment": None,
            "moderation_error": (
                "Moderation failed. Human review is required."
            ),
            "needs_review": True,
        }

def validate_reply(state: ReplyDraftState) -> dict:
    """Apply the publishing policy after moderation."""

    draft = state.get("draft")
    assessment = state.get("assessment")

    if draft is None:
        return {
            "needs_review": True,
            "policy_reason": "No draft was generated.",
        }

    if assessment is None:
        return {
            "needs_review": True,
            "policy_reason": (
                state.get("moderation_error")
                or "No valid moderation assessment is available."
            ),
        }

    policy_result = evaluate_reply_policy(
        assessment=assessment,
        reply_text=draft.reply,
    )

    # Automatic publishing remains disabled.
    return {
        "needs_review": True,
        "policy_reason": policy_result.reason,
    }

builder = StateGraph(ReplyDraftState)

builder.add_node("load_comment_context", load_comment_context)
builder.add_node("load_video_context", load_video_context)
builder.add_node("generate_reply", generate_reply)
builder.add_node("validate_reply", validate_reply)
builder.add_node("moderate_reply", moderate_reply)
builder.add_node("load_conversation_memory", load_conversation_memory)

builder.add_edge(START, "load_comment_context")

builder.add_conditional_edges(
    "load_comment_context",
    route_after_comment_load,
    {
        "continue": "load_video_context",
        "stop": END,
    },
)
builder.add_conditional_edges(
    "load_video_context",
    route_after_video_load,
    {
        "continue": "load_conversation_memory",
        "stop": END,
    },
)

builder.add_edge("load_conversation_memory", "generate_reply")
builder.add_edge("generate_reply", "moderate_reply")
builder.add_edge("moderate_reply", "validate_reply")
builder.add_edge("validate_reply", END)

reply_graph = builder.compile()

