"""Health check: the app builds and serves.

Covers TASKS.md task 1 ("Project skeleton"): the FastAPI app exists, `GET /health`
returns `{"status": "ok"}` with 200, and the app is a real FastAPI application
(schema served, docs served, unmodeled routes/methods behave the way FastAPI's
default routing contract says they should).
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    """TC-001: GET /health returns 200 with the exact ok body."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_response_is_json() -> None:
    """TC-002: the /health response is served as JSON."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.headers["content-type"].startswith("application/json")


def test_health_rejects_post() -> None:
    """TC-003: only GET is wired for /health; POST is method-not-allowed."""
    client = TestClient(app)

    response = client.post("/health")

    assert response.status_code == 405


def test_unknown_path_returns_404() -> None:
    """TC-004: the skeleton defines no routes beyond /health, so others 404."""
    client = TestClient(app)

    response = client.get("/does-not-exist")

    assert response.status_code == 404


def test_openapi_schema_is_served() -> None:
    """TC-005: the app builds as a real FastAPI app exposing its schema."""
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "URL Shortener API"
    assert "/health" in response.json()["paths"]


def test_docs_are_served() -> None:
    """TC-006: FastAPI's interactive docs (Swagger UI) are reachable."""
    client = TestClient(app)

    response = client.get("/docs")

    assert response.status_code == 200
