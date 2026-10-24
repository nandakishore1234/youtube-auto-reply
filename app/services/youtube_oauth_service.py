
from datetime import timezone

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.oauth_credential import OAuthCredential
from app.models.youtube_channel import YouTubeChannel
from app.services.token_crypto import encrypt_tokens, decrypt_tokens


SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def create_oauth_flow(state: str | None = None) -> Flow:
    settings = get_settings()

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.google_redirect_uri,
    )


def exchange_code_for_channel(
    db: Session,
    user_id: int,
    authorization_response: str,
    state: str,
    code_verifier: str,
) -> YouTubeChannel:
    if not code_verifier:
        raise ValueError("Missing OAuth PKCE code verifier")

    # Re-create the flow using the original state and restore
    # the verifier created before redirecting the user to Google.
    flow = create_oauth_flow(state=state)
    flow.code_verifier = code_verifier

    flow.fetch_token(
        authorization_response=authorization_response,
        code_verifier=code_verifier,
    )

    credentials = flow.credentials

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    response = youtube.channels().list(
        part="id,snippet",
        mine=True,
    ).execute()

    items = response.get("items", [])

    if not items:
        raise ValueError(
            "No YouTube channel was found for this Google account."
        )

    saved_channel = None

    for item in items:
        youtube_channel_id = item["id"]
        title = item.get("snippet", {}).get("title", "")

        channel = db.scalar(
            select(YouTubeChannel).where(
                YouTubeChannel.user_id == user_id,
                YouTubeChannel.youtube_channel_id
                == youtube_channel_id,
            )
        )

        if channel is None:
            channel = YouTubeChannel(
                user_id=user_id,
                youtube_channel_id=youtube_channel_id,
                title=title,
                status="connected",
            )
            db.add(channel)
            db.flush()
        else:
            channel.title = title
            channel.status = "connected"

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        existing_credential = db.scalar(
            select(OAuthCredential).where(
                OAuthCredential.channel_connection_id == channel.id
            )
        )

        if existing_credential is None:
            existing_credential = OAuthCredential(
                channel_connection_id=channel.id,
                encrypted_token_json=encrypt_tokens(token_data),
                scopes=credentials.scopes or [],
                expires_at=normalize_expiry(credentials.expiry),
                status="active",
            )
            db.add(existing_credential)

        else:
            # Keep the existing refresh token if Google omits it
            # from a subsequent authorization response.
            if not credentials.refresh_token:
                previous = decrypt_tokens(
                    existing_credential.encrypted_token_json
                )
                token_data["refresh_token"] = previous.get(
                    "refresh_token"
                )

            existing_credential.encrypted_token_json = (
                encrypt_tokens(token_data)
            )
            existing_credential.scopes = credentials.scopes or []
            existing_credential.expires_at = normalize_expiry(
                credentials.expiry
            )
            existing_credential.status = "active"

        saved_channel = channel

    if saved_channel is None:
        raise ValueError("No channel could be saved.")

    db.commit()
    db.refresh(saved_channel)

    return saved_channel


def normalize_expiry(expiry):
    if expiry is None:
        return None

    if expiry.tzinfo is None:
        return expiry.replace(tzinfo=timezone.utc)

    return expiry
