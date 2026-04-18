from __future__ import annotations

from fastapi import FastAPI

from backend.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="EvidenceFlow Agent API",
        version="0.1.0",
        description="Backend skeleton for meeting processing, research planning, and evidence-aware workflows."
    )

    @app.get("/")
    async def read_root() -> dict[str, str]:
        return {
            "name": app.title,
            "status": "ready",
            "stage": "task-1-task-2-skeleton"
        }

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "llm_provider": settings.llm_provider,
            "transcription_backend": settings.transcription_backend
        }

    return app


app = create_app()

