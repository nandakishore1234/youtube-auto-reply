from pydantic import BaseModel, Field


class CommentIngestRequest(BaseModel):
    channel_id: int = Field(gt=0)

    youtube_comment_id: str = Field(
        min_length=1,
        max_length=255,
    )

    youtube_video_id: str = Field(
        min_length=1,
        max_length=255,
    )

    parent_youtube_comment_id: str | None = Field(
        default=None,
        max_length=255,
    )

    author_display_name: str | None = Field(
        default=None,
        max_length=255,
    )

    text: str = Field(
        min_length=1,
        max_length=10000,
    )

    video_title: str = Field(
        default="",
        max_length=500,
    )

    video_context: str = Field(
        default="",
        max_length=3000,
    )

    channel_tone: str = Field(
        default="Friendly, natural, and respectful",
        max_length=500,
    )