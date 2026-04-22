from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.meeting import ParsedTranscript, TranscriptChunk
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectRecord,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import StudentProgress
from backend.services.project_memory_service import ProjectMemoryService
from backend.storage.lancedb_store import LanceDBStore
from backend.storage.sqlite_store import SQLiteStore


def build_transcript() -> ParsedTranscript:
    return ParsedTranscript(
        meeting_id="meeting-memory-001",
        chunks=[
            TranscriptChunk(
                chunk_id="chunk-0001",
                speaker="Alice",
                timestamp_start="00:05",
                text="Curriculum learning raised macro F1 on hard examples.",
            ),
            TranscriptChunk(
                chunk_id="chunk-0002",
                speaker="Prof. Chen",
                timestamp_start="00:25",
                text="Keep the hard-negative ablation in next week's plan.",
            ),
        ],
    )


def build_memory_service(tmp_path: Path) -> ProjectMemoryService:
    sqlite_store = SQLiteStore(tmp_path / "memory.sqlite3")
    vector_store = LanceDBStore(tmp_path / "lancedb")
    return ProjectMemoryService(sqlite_store=sqlite_store, vector_store=vector_store)


def test_project_memory_persists_and_retrieves_all_required_records() -> None:
    base_dir = Path.cwd() / "backend" / "storage" / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = base_dir / f"project-memory-{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = ProjectRecord(
        project_id="project-001",
        name="EvidenceFlow",
        description="Research planning assistant.",
        domain="nlp",
    )
    meeting = ProjectMeetingRecord(
        meeting_id="meeting-memory-001",
        project_id="project-001",
        title="Weekly lab meeting",
        summary="Alice reviewed the curriculum learning ablation plan.",
    )
    decisions = [
        ProjectDecision(
            id="decision-001",
            title="Focus next week on hard-negative curriculum learning.",
            rationale="It is the most direct way to validate the advisor idea.",
            decided_by="Prof. Chen",
        )
    ]
    action_items = [
        ActionItem(
            meeting_id="meeting-memory-001",
            student_name="Alice",
            title="Run the hard-negative curriculum ablation.",
            owner="Alice",
            deadline="Friday",
            priority="high",
            status="open",
        )
    ]
    claims = [
        Claim(
            id="claim-001",
            meeting_id="meeting-memory-001",
            text="Curriculum learning raised macro F1 on hard examples.",
            speaker="Alice",
            transcript_snippet="Curriculum learning raised macro F1 on hard examples.",
            claim_kind="factual",
            verification_status="supported",
        )
    ]
    advisor_ideas = [
        ResearchIdea(
            id="idea-001",
            meeting_id="meeting-memory-001",
            student_name="Alice",
            idea_text="Keep the hard-negative ablation in next week's plan.",
            suggested_by="Prof. Chen",
            expected_validation="Improve macro F1 on hard examples.",
            validation_metrics=["macro F1"],
        )
    ]
    student_progress = [
        StudentProgress(
            meeting_id="meeting-memory-001",
            student_name="Alice",
            completed_work=["Finished the first curriculum learning run."],
            current_result="Macro F1 improved on hard examples.",
            blockers=["Need a cleaner ablation table."],
            next_step_suggestion="Run one more controlled ablation before Friday.",
        )
    ]
    key_papers = [
        KeyPaperMemory(
            id="paper-001",
            title="Curriculum Learning for Robust Classification",
            source_url="https://example.org/paper",
            reason="Explains how to stage hard examples without hurting calibration.",
        )
    ]
    transcript = build_transcript()

    service = build_memory_service(tmp_path)
    service.remember_meeting(
        project,
        meeting,
        decisions=decisions,
        action_items=action_items,
        claims=claims,
        advisor_ideas=advisor_ideas,
        student_progress=student_progress,
        key_papers=key_papers,
        transcript=transcript,
    )

    reloaded_service = build_memory_service(tmp_path)
    snapshot = reloaded_service.load_project_memory(
        "project-001",
        query="hard-negative curriculum learning",
        limit=4,
    )

    assert snapshot.project is not None
    assert snapshot.project.name == "EvidenceFlow"
    assert len(snapshot.meetings) == 1
    assert snapshot.meetings[0].meeting_id == "meeting-memory-001"
    assert len(snapshot.decisions) == 1
    assert snapshot.decisions[0].decided_by == "Prof. Chen"
    assert len(snapshot.action_items) == 1
    assert snapshot.action_items[0].title == "Run the hard-negative curriculum ablation."
    assert len(snapshot.claims) == 1
    assert snapshot.claims[0].verification_status == "supported"
    assert len(snapshot.advisor_ideas) == 1
    assert snapshot.advisor_ideas[0].expected_validation == "Improve macro F1 on hard examples."
    assert len(snapshot.student_progress) == 1
    assert snapshot.student_progress[0].student_name == "Alice"
    assert len(snapshot.key_papers) == 1
    assert snapshot.key_papers[0].title == "Curriculum Learning for Robust Classification"
    assert snapshot.relevant_context
    assert any(
        hit.entry_type in {"meeting_chunk", "decision", "advisor_idea", "key_paper"}
        for hit in snapshot.relevant_context
    )


def test_project_memory_updates_action_item_status_and_refreshes_vector_memory() -> None:
    base_dir = Path.cwd() / "backend" / "storage" / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = base_dir / f"project-memory-{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True, exist_ok=True)

    project = ProjectRecord(
        project_id="project-002",
        name="EvidenceFlow",
        description="Research planning assistant.",
        domain="nlp",
    )
    meeting = ProjectMeetingRecord(
        meeting_id="meeting-memory-002",
        project_id="project-002",
        title="Weekly lab meeting",
        summary="Alice committed to a final ablation pass.",
    )
    action_item = ActionItem(
        meeting_id="meeting-memory-002",
        student_name="Alice",
        title="Run the hard-negative curriculum ablation",
        owner="Alice",
        deadline="Friday",
        priority="high",
        status="open",
    )

    service = build_memory_service(tmp_path)
    service.remember_meeting(
        project,
        meeting,
        action_items=[action_item],
        transcript=build_transcript(),
    )

    updated_action_item = service.update_action_item_status(
        "project-002",
        meeting_id="meeting-memory-002",
        title="Run the hard-negative curriculum ablation",
        owner="Alice",
        status="done",
    )

    assert updated_action_item is not None
    assert updated_action_item.status == "done"

    snapshot = service.load_project_memory("project-002")
    assert snapshot.action_items[0].status == "done"

    records_path = tmp_path / "lancedb" / "project_memory_records.json"
    vector_records = json.loads(records_path.read_text(encoding="utf-8"))
    action_record = next(
        record
        for record in vector_records
        if record["entry_type"] == "action_item"
        and "Run the hard-negative curriculum ablation" in record["text"]
    )
    assert action_record["metadata"]["status"] == "done"
