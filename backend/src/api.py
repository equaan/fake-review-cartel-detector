"""FastAPI application scaffold for the fake review cartel detector."""

from __future__ import annotations

from fastapi import FastAPI


app = FastAPI(title="Fake Review Cartel Detector API", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a simple health response."""
    return {"status": "ok"}
