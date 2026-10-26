
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.youtube_channel import YouTubeChannel
from app.models.oauth_credential import OAuthCredential
from app.services.token_crypto import decrypt_tokens, encrypt_tokens
from app.schemas.comment import CommentIngestRequest
from app.services.comment_service import (
    ingest_comment,
    generate_and_save_draft,
)

def get_youtube_client(db: Session, channel_id: int, user_id: int):
    """
    Load the selected channel's saved OAuth credentials
    and create an authenticated YouTube API client.

    channel_id: Internal youtube_channels.id
    user_id: Internal users.id
    """
    channel = db.scalar(
        select(YouTubeChannel).where(
            YouTubeChannel.id == channel_id,
            YouTubeChannel.user_id == user_id,
        )
    )

    if channel is None:
        raise ValueError("Channel not found for this user.")

    credential_record = db.scalar(
        select(OAuthCredential).where(
            OAuthCredential.channel_connection_id == channel.id,
            OAuthCredential.status == "active",
        )
    )

    if credential_record is None:
        raise ValueError("No active OAuth credentials for this channel.")

    token_data = decrypt_tokens(
        credential_record.encrypted_token_json
    )

    expiry = credential_record.expires_at

    if expiry is not None:
        if expiry.tzinfo is None:
            # PostgreSQL returned a timestamp without timezone information.
            expiry = expiry.replace(tzinfo=timezone.utc)
        else:
            # Normalize timezone-aware timestamps to UTC.
            expiry = expiry.astimezone(timezone.utc)

        # google-auth compares expiry against a naive UTC datetime.
        expiry = expiry.replace(tzinfo=None)

    credentials = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
        expiry=expiry,
    )

    if credentials.expired:
        if not credentials.refresh_token:
            credential_record.status = "expired"
            db.commit()
            raise ValueError(
                "YouTube authorization expired. Reconnect the channel."
            )

        credentials.refresh(Request())

        token_data.update({
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        })

        credential_record.encrypted_token_json = encrypt_tokens(token_data)
        credential_record.expires_at = credentials.expiry
        credential_record.status = "active"
        db.commit()

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    return youtube, channel


def fetch_recent_video_ids(youtube, max_videos: int = 5) -> list[str]:
    """Get IDs of the channel's most recent uploaded videos."""
    channel_response = youtube.channels().list(
        part="contentDetails",
        mine=True,
    ).execute()

    items = channel_response.get("items", [])
    if not items:
        return []

    uploads_playlist_id = (
        items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    playlist_response = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=uploads_playlist_id,
        maxResults=min(max_videos, 50),
    ).execute()

    return [
        item["contentDetails"]["videoId"]
        for item in playlist_response.get("items", [])
        if item.get("contentDetails", {}).get("videoId")
    ]




def fetch_video_comments(
    youtube,
    video_id: str,
    max_pages: int = 1,
    max_reply_pages: int = 1,
) -> list[dict]:
    """Fetch top-level comments and a bounded number of replies."""
    from googleapiclient.errors import HttpError

    comments = []
    page_token = None

    def extract_comment(item, parent_id=None):
        snippet = item.get("snippet", {})
        comment_id = item.get("id")
        text = (
            snippet.get("textOriginal")
            or snippet.get("textDisplay")
            or ""
        ).strip()

        if not comment_id or not text:
            return None

        return {
            "youtube_comment_id": comment_id,
            "youtube_video_id": video_id,
            "parent_youtube_comment_id": parent_id,
            "author_display_name": snippet.get("authorDisplayName"),
            "text": text,
        }

    for _ in range(max(0, max_pages)):
        try:
            response = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=page_token,
                textFormat="plainText",
            ).execute()
        except HttpError as exc:
            if exc.resp.status in (403, 404):
                break
            raise

        for thread in response.get("items", []):
            thread_snippet = thread.get("snippet", {})
            top_comment = thread_snippet.get("topLevelComment", {})
            top_id = top_comment.get("id")

            top_item = extract_comment(top_comment)
            if top_item is None:
                continue

            comments.append(top_item)

            # Fetch replies only when YouTube reports that replies exist.
            total_replies = thread_snippet.get("totalReplyCount", 0)
            if not top_id or total_replies <= 0:
                continue

            reply_token = None
            for _ in range(max(0, max_reply_pages)):
                try:
                    reply_response = youtube.comments().list(
                        part="snippet",
                        parentId=top_id,
                        maxResults=100,
                        pageToken=reply_token,
                        textFormat="plainText",
                    ).execute()
                except HttpError as exc:
                    if exc.resp.status in (403, 404):
                        break
                    raise

                for reply in reply_response.get("items", []):
                    reply_item = extract_comment(reply, parent_id=top_id)
                    if reply_item is not None:
                        comments.append(reply_item)

                reply_token = reply_response.get("nextPageToken")
                if not reply_token:
                    break

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments




def fetch_and_process_channel_comments(
    db: Session,
    channel_id: int,
    user_id: int,
    max_videos: int = 5,
    max_pages_per_video: int = 1,
) -> dict:
    """
    Fetch recent YouTube comments and send them through
    the existing database and LangChain draft pipeline.

    Replies are generated as drafts only; nothing is published.
    """
    youtube, channel = get_youtube_client(
        db=db,
        channel_id=channel_id,
        user_id=user_id,
    )

    video_ids = fetch_recent_video_ids(
        youtube,
        max_videos=max_videos,
    )

    fetched = 0
    processed = 0
    duplicates = 0
    failed = 0

    for video_id in video_ids:
        try:
            comments = fetch_video_comments(
                youtube,
                video_id,
                max_pages=max_pages_per_video,
            )
        except Exception:
            failed += 1
            continue

        for item in comments:
            fetched += 1

            try:
                payload = CommentIngestRequest(
                    channel_id=channel.id,
                    youtube_comment_id=item["youtube_comment_id"],
                    youtube_video_id=item["youtube_video_id"],
                    parent_youtube_comment_id=item["parent_youtube_comment_id"],
                    author_display_name=item["author_display_name"],
                    text=item["text"],
                    channel_tone="Friendly, natural, and respectful",
                )

                # Use the existing ingestion and deduplication logic.
                comment, is_new = ingest_comment(db, payload)

                if not is_new:
                    duplicates += 1
                    continue

                # Reuse your existing LangChain draft-generation pipeline.
                generate_and_save_draft(db, comment, payload)
                processed += 1

            except Exception:
                db.rollback()
                failed += 1

    return {
        "channel_id": channel.id,
        "channel_title": channel.title,
        "videos_checked": len(video_ids),
        "comments_fetched": fetched,
        "comments_processed": processed,
        "duplicates_skipped": duplicates,
        "failed": failed,
        "published": 0,
    }
