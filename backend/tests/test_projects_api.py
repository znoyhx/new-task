from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api.projects import get_briefing_service, get_project_memory_service
from backend.app import create_app
from backend.schemas.action_item import ActionItem
from backend.schemas.project_memory import ProjectDecision, ProjectMeetingRecord, ProjectRecord
from backend.services.briefing_service import BriefingService
from backend.services.project_memory_service import ProjectMemoryService
from backend.storage.lancedb_store import LanceDBStore
from backend.storage.sqlite_store import SQLiteStore


def make_workspace_temp_dir() -> Path:
    temp_root = Path("backend/tests/.tmp")
    temp_root.mkdir(parents=True, exist_ok=True)
    workspace = (temp_root / f"projects-api-{uuid4().hex[:8]}").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def build_memory_service(workspace: Path) -> ProjectMemoryService:
    sqlite_store = SQLiteStore(workspace / "memory.sqlite3")
    vector_store = LanceDBStore(workspace / "lancedb")
    service = ProjectMemoryService(sqlite_store=sqlite_store, vector_store=vector_store)

    project = ProjectRecord(
        project_id="continuity-project",
        name="Continuity Project",
        description="Memory reuse demo.",
        domain="nlp",
    )
    history_meeting = ProjectMeetingRecord(
        meeting_id="meeting-a",
        project_id="continuity-project",
        title="Meeting A",
        summary="Defined the original ablation task.",
    )
    current_meeting = ProjectMeetingRecord(
        meeting_id="meeting-b",
        project_id="continuity-project",
        title="Meeting B",
        summary="Reviewed progress and status updates.",
    )

    service.remember_meeting(
        project,
        history_meeting,
        decisions=[
            ProjectDecision(
                id="decision-a",
                title="Keep the follow-up ablation in scope.",
                rationale="It is the fastest validation path.",
                decided_by="Prof. Chen",
            )
        ],
        action_items=[
            ActionItem(
                meeting_id="meeting-a",
                student_name="Alice",
                title="Run the follow-up ablation",
                owner="Alice",
                deadline="Friday",
                priority="high",
                status="open",
            )
        ],
    )
    service.remember_meeting(
        project,
        current_meeting,
        decisions=[
            ProjectDecision(
                id="decision-b",
                title="Close the logging blocker before next week.",
                rationale="The demo depends on transcript traceability.",
                decided_by="Prof. Chen",
            )
        ],
        action_items=[
            ActionItem(
                meeting_id="meeting-b",
                student_name="Bob",
                title="Fix retrieval-assisted logging",
                owner="Bob",
                deadline="Tuesday",
                priority="medium",
                status="in_progress",
            )
        ],
    )
    return service


def test_get_project_memory_returns_snapshot_and_briefing_context() -> None:
    workspace = make_workspace_temp_dir()
    try:
        service = build_memory_service(workspace)
        app = create_app()
        app.dependency_overrides[get_project_memory_service] = lambda: service
        app.dependency_overrides[get_briefing_service] = lambda: BriefingService()
        client = TestClient(app)

        response = client.get("/api/projects/continuity-project/memory")

        assert response.status_code == 200
        payload = response.json()
        assert payload["project_memory"]["project"]["project_id"] == "continuity-project"
        assert len(payload["project_memory"]["meetings"]) == 2
        assert len(payload["project_memory"]["decisions"]) == 2
        assert len(payload["project_memory"]["action_items"]) == 2
        assert payload["briefing"]["summary"]
        assert any(
            item["origin_layer"] == "history_memory"
            for item in payload["briefing_items"]
        )
        assert any(
            task["title"] == "Run the follow-up ablation"
            for task in payload["briefing"]["carryover_tasks"]
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_get_project_memory_returns_404_for_missing_project() -> None:
    workspace = make_workspace_temp_dir()
    try:
        service = build_memory_service(workspace)
        app = create_app()
        app.dependency_overrides[get_project_memory_service] = lambda: service
        app.dependency_overrides[get_briefing_service] = lambda: BriefingService()
        client = TestClient(app)

        response = client.get("/api/projects/missing-project/memory")

        assert response.status_code == 404
        assert "missing-project" in response.json()["detail"]
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_patch_action_item_status_updates_memory_and_briefing() -> None:
    workspace = make_workspace_temp_dir()
    try:
        service = build_memory_service(workspace)
        app = create_app()
        app.dependency_overrides[get_project_memory_service] = lambda: service
        app.dependency_overrides[get_briefing_service] = lambda: BriefingService()
        client = TestClient(app)

        response = client.patch(
            "/api/projects/continuity-project/action-items/status",
            json={
                "meeting_id": "meeting-a",
                "title": "Run the follow-up ablation",
                "owner": "Alice",
                "status": "done",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["updated_action_item"]["status"] == "done"
        updated_task = next(
            item
            for item in payload["project_memory"]["action_items"]
            if item["meeting_id"] == "meeting-a" and item["title"] == "Run the follow-up ablation"
        )
        assert updated_task["status"] == "done"
        assert all(
            task["title"] != "Run the follow-up ablation"
            for task in payload["briefing"]["carryover_tasks"]
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
