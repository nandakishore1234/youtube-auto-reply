from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "youtube-ai-replier",
    }


def test_readiness_when_database_is_available(monkeypatch):
    monkeypatch.setattr(
        main,
        "check_database",
        lambda: None,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }


def test_readiness_when_database_is_unavailable(monkeypatch):
    def fail_database_check():
        raise RuntimeError("Connection failed")

    monkeypatch.setattr(
        main,
        "check_database",
        fail_database_check,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database unavailable",
    }