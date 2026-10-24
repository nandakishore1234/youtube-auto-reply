from app.ai.llm import generate_reply_draft
from app.ai.schema import ReplyDraft, ReplyDraftRequest


def create_draft(request: ReplyDraftRequest) -> ReplyDraft:
    return generate_reply_draft(request)