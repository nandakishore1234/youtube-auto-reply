
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_current_user
from app.ai.schema import ReplyDraft


class FakeUser:
    id = 2


app.dependency_overrides[get_current_user] = lambda: FakeUser()

client = TestClient(app)


def teardown_module():
    app.dependency_overrides.pop(get_current_user, None)


def test_draft_endpoint_returns_structured_reply():
    draft = ReplyDraft(
        reply="Thanks for watching!",
        intent="compliment",
        needs_human_review=False,
        reason="The viewer expressed positive feedback.",
    )

    with patch(
        "app.api.replies.create_draft",
        return_value=draft,
    ):
        response = client.post(
            "/api/v1/replies/draft",
            json={
                "comment_text": "Great video!",
                "video_title": "Gameplay",
                "video_context": "",
                "channel_tone": "Friendly",
            },
        )

    assert response.status_code == 200
    assert response.json()["reply"] == "Thanks for watching!"
    assert response.json()["intent"] == "compliment"
    assert response.json()["needs_human_review"] is False


def test_draft_endpoint_rejects_empty_comment():
    response = client.post(
        "/api/v1/replies/draft",
        json={"comment_text": ""},
    )

    assert response.status_code == 422


def test_draft_endpoint_handles_model_failure():
    with patch(
        "app.api.replies.create_draft",
        side_effect=RuntimeError("Model unavailable"),
    ):
        response = client.post(
            "/api/v1/replies/draft",
            json={"comment_text": "Great video!"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Unable to generate a reply draft"
    )
