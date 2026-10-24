from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.reply_draft import ReplyDraft
from app.schemas.comment import CommentIngestRequest
from app.services.comment_service import (
    generate_and_save_draft,
    ingest_comment,
)


router = APIRouter(
    prefix="/api/v1/comments",
    tags=["Comments"],
)


@router.post("/ingest")
def ingest_and_draft(
    payload: CommentIngestRequest,
    db: Session = Depends(get_db),
):
    try:
        comment, created = ingest_comment(db, payload)

        if not created:
            existing_draft = db.query(ReplyDraft).filter_by(
                comment_id=comment.id
            ).first()

            return {
                "comment_id": comment.id,
                "youtube_comment_id": comment.youtube_comment_id,
                "status": comment.status,
                "duplicate": True,
                "draft": (
                    {
                        "reply": existing_draft.reply_text,
                        "intent": existing_draft.intent,
                        "status": existing_draft.status,
                        "needs_human_review": (
                            existing_draft.needs_human_review
                        ),
                    }
                    if existing_draft
                    else None
                ),
            }

        draft = generate_and_save_draft(db, comment, payload)

        return {
            "comment_id": comment.id,
            "youtube_comment_id": comment.youtube_comment_id,
            "status": comment.status,
            "duplicate": False,
            "draft": {
                "reply": draft.reply_text,
                "intent": draft.intent,
                "status": draft.status,
                "needs_human_review": draft.needs_human_review,
            },
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to process comment",
        ) from exc