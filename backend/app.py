from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deliverables import router as deliverables_router
from backend.api.meetings import router as meetings_router
from backend.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="EvidenceFlow Agent API",
        version="0.1.0",
        description="Backend skeleton for meeting processing, research planning, and evidence-aware workflows."
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meetings_router)
    app.include_router(deliverables_router)

    @app.get("/")
    async def read_root() -> dict[str, str]:
        return {
            "name": app.title,
            "status": "ready",
            "stage": "task-10-demo-ready"
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
