from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.ai.schema import ReplyDraftRequest,ReplyDraft
from app.ai.llm import generate_reply_draft
from app.database import SessionLocal
from app.models.comment import Comment
from app.services.youtube_comment_service import get_youtube_client
from app.models.youtube_channel import YouTubeChannel

class ReplyDraftState(TypedDict):
    user_id: int
    channel_id: int
    comment_id: int
    comment_text: str
    video_id: str
    video_title: str
    video_context: str
    channel_tone: str

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

def route_after_comment_load(state: ReplyDraftState) -> str:
    """Decide whether to continue after loading the comment."""

    if state.get("error"):
        return "stop"

    return "continue"


def generate_reply(state: ReplyDraftState) -> dict:
    """Generate a reply using the loaded comment context"""
    request = ReplyDraftRequest(
        comment_text=state["comment_text"],
        video_title=state.get("video_title", ""),
        video_context=state.get("video_context", ""),
        channel_tone=state.get(
            "channel_tone",
            "Friendly, natural, and respectful",
        ),
    )
    draft = generate_reply_draft(request)

    return {
        "request": request,
        "draft": draft,
        "needs_review": draft.needs_human_review,
        "error": None,
    }

def validate_reply(state: ReplyDraftState) -> dict:
    """Apply deterministic review rules to the generated draft."""

    draft = state.get("draft")

    if draft is None:
        return {
            "needs_review": True,
            "error": state.get("error") or "No draft generated",
        }

    needs_review = (
        True  # Every draft requires human approval in this version.
        or draft.needs_human_review
        or draft.intent in {"spam", "criticism"}
    )

    return {
        "needs_review": needs_review,
        "error": None,
    }

builder = StateGraph(ReplyDraftState)

builder.add_node("load_comment_context", load_comment_context)
builder.add_node("load_video_context", load_video_context)
builder.add_node("generate_reply", generate_reply)
builder.add_node("validate_reply", validate_reply)

builder.add_edge(START, "load_comment_context")

builder.add_conditional_edges(
    "load_comment_context",
    route_after_comment_load,
    {
        "continue": "load_video_context",
        "stop": END,
    },
)

builder.add_edge("load_video_context", "generate_reply")
builder.add_edge("generate_reply", "validate_reply")
builder.add_edge("validate_reply", END)

reply_graph = builder.compile()

