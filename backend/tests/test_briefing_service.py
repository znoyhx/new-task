from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.api.deliverables import (
    DeliverableGenerationRequest,
    generate_deliverable as generate_deliverable_route,
)
from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectMeetingRecord,
    ProjectMemorySnapshot,
    ProjectRecord,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.risk import Risk
from backend.schemas.student_progress import StudentProgress
from backend.services.briefing_service import BriefingService
from backend.services.deliverable_service import DeliverableService


def fixed_time(hour: int) -> datetime:
    return datetime(2026, 4, 18, hour, 0, tzinfo=timezone.utc)


def build_project_memory() -> ProjectMemorySnapshot:
    return ProjectMemorySnapshot(
        project=ProjectRecord(
            project_id="project-briefing-001",
            name="EvidenceFlow Demo",
            description="Weekly research cockpit demo.",
            domain="mlsys",
            created_at=fixed_time(9),
        ),
        meetings=[
            ProjectMeetingRecord(
                meeting_id="meeting-001",
                project_id="project-briefing-001",
                title="Week 1",
                summary="Baseline checkpoint.",
                created_at=fixed_time(10),
            ),
            ProjectMeetingRecord(
                meeting_id="meeting-002",
                project_id="project-briefing-001",
                title="Week 2",
                summary="Curriculum learning review.",
                created_at=fixed_time(11),
            ),
        ],
        action_items=[
            ActionItem(
                meeting_id="meeting-002",
                student_name="Alice",
                title="Prepare the hard-negative ablation table",
                owner="Alice",
                deadline="Friday",
                priority="high",
                status="open",
            ),
            ActionItem(
                meeting_id="meeting-002",
                student_name="Bob",
                title="Instrument retrieval logging for transcript traceability",
                owner="Bob",
                deadline="Tuesday",
                priority="medium",
                status="in_progress",
            ),
            ActionItem(
                meeting_id="meeting-001",
                student_name="Alice",
                title="Archive the original baseline plots",
                owner="Alice",
                deadline="done",
                priority="low",
                status="done",
            ),
        ],
        claims=[
            Claim(
                id="claim-001",
                meeting_id="meeting-002",
                text="Curriculum learning consistently improves hard-example macro F1 in small-data settings.",
                speaker="Prof. Chen",
                verification_status="needs_verification",
            )
        ],
        advisor_ideas=[
            ResearchIdea(
                id="idea-001",
                meeting_id="meeting-002",
                student_name="Alice",
                idea_text="Keep the hard-negative curriculum ablation in next week's plan.",
                suggested_by="Prof. Chen",
                expected_validation="Improve macro F1 without hurting calibration.",
                validation_metrics=["macro F1", "calibration error"],
            ),
            ResearchIdea(
                id="idea-002",
                meeting_id="meeting-002",
                student_name="Bob",
                idea_text="Test retrieval-assisted logging for transcript traceability.",
                suggested_by="Prof. Chen",
                expected_validation="Every exported task links back to a transcript slice.",
                validation_metrics=["trace coverage"],
            ),
        ],
        student_progress=[
            StudentProgress(
                meeting_id="meeting-002",
                student_name="Alice",
                completed_work=["Reran the curriculum-learning baseline."],
                current_result="Macro F1 improved on hard examples, but calibration regressed.",
                blockers=["Still missing a clean ablation table."],
                risks=[
                    Risk(
                        meeting_id="meeting-002",
                        student_name="Alice",
                        title="Calibration regresses after stage three",
                        level="high",
                        description="The final curriculum stage still hurts calibration error.",
                        owner="Alice",
                    )
                ],
            )
        ],
        key_papers=[
            KeyPaperMemory(
                id="paper-001",
                project_id="project-briefing-001",
                meeting_id="meeting-002",
                title="Curriculum Learning for Robust Classification",
                source_url="https://example.org/curriculum",
                reason="Explains how to stage hard examples while tracking calibration.",
            )
        ],
    )


def test_briefing_service_includes_required_sections() -> None:
    project_memory = build_project_memory()
    service = BriefingService()

    briefing = service.generate_briefing(project_memory)

    assert briefing.project_id == "project-briefing-001"
    assert briefing.latest_meeting is not None
    assert briefing.latest_meeting.meeting_id == "meeting-002"
    assert briefing.last_advisor_ideas
    assert briefing.last_advisor_ideas[0].idea_text.startswith("Keep the hard-negative curriculum")
    assert briefing.student_commitments
    assert briefing.student_commitments[0].student_name == "Alice"
    assert briefing.open_tasks
    assert briefing.open_tasks[0].title == "Prepare the hard-negative ablation table"
    assert briefing.risks
    assert briefing.risks[0].title == "Calibration regresses after stage three"
    assert briefing.recommended_agenda
    assert any("top risk" in item.title.lower() for item in briefing.recommended_agenda)


def test_deliverable_service_generates_all_required_documents() -> None:
    project_memory = build_project_memory()
    briefing = BriefingService().generate_briefing(project_memory)
    service = DeliverableService()

    weekly_report = service.generate_deliverable(
        "weekly_report",
        project_memory=project_memory,
        briefing=briefing,
    )
    next_meeting = service.generate_deliverable(
        "next_meeting_briefing",
        project_memory=project_memory,
        briefing=briefing,
    )
    next_week = service.generate_deliverable(
        "next_week_research_plan",
        project_memory=project_memory,
        briefing=briefing,
    )
    outline = service.generate_deliverable(
        "presentation_outline",
        project_memory=project_memory,
        briefing=briefing,
    )

    assert "## Advisor Ideas" in weekly_report.content_markdown
    assert "## Recommended Agenda" in next_meeting.content_markdown
    assert "## Priority Tasks" in next_week.content_markdown
    assert "## 5. Next-week execution plan" in outline.content_markdown


class FakeProjectMemoryService:
    def load_project_memory(self, project_id: str, *, query: str | None = None, limit: int = 5) -> ProjectMemorySnapshot:
        assert project_id == "project-briefing-001"
        _ = (query, limit)
        return build_project_memory()


def test_deliverables_api_generates_markdown_document() -> None:
    response = asyncio.run(
        generate_deliverable_route(
            DeliverableGenerationRequest(
            project_id="project-briefing-001",
            deliverable_type="weekly_report",
            ),
            project_memory_service=FakeProjectMemoryService(),
            briefing_service=BriefingService(),
            deliverable_service=DeliverableService(),
        )
    )

    assert response.briefing.project_id == "project-briefing-001"
    assert response.document.deliverable_type == "weekly_report"
    assert "Weekly Report" in response.document.title
    assert "## Student Progress" in response.document.content_markdown
