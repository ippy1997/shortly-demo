"""FastAPI application and its routes.

Only the health check exists so far; the link routes arrive with their own tasks.
"""

from fastapi import FastAPI

app = FastAPI(title="URL Shortener API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
