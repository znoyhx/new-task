from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from backend.config import load_settings
from backend.schemas.action_item import ActionItem
from backend.schemas.claim import ClaimVerificationResult
from backend.schemas.evidence_card import EvidenceCard
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectRecord,
)
from backend.services.briefing_service import BriefingService
from backend.services.claim_extraction_service import ClaimExtractionService
from backend.services.claim_verification_service import ClaimVerificationService
from backend.services.deliverable_service import DeliverableService
from backend.services.idea_capture_service import IdeaCaptureService
from backend.services.progress_extraction_service import ProgressExtractionService
from backend.services.project_memory_service import ProjectMemoryService
from backend.services.reading_recommendation_service import ReadingRecommendationService
from backend.services.research_plan_service import ResearchPlanService
from backend.services.transcript_parser_service import TranscriptParserService
from backend.services.transcription_service import TranscriptionService
from backend.storage.lancedb_store import LanceDBStore
from backend.storage.sqlite_store import SQLiteStore


class StubChatJsonClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def chat_json(self, prompt: str, **_: object) -> dict[str, object]:
        _ = prompt
        return self.payload


class StubAudioTranscriber:
    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text

    def transcribe_file(
        self,
        file_path: str | Path,
        *,
        language_hint: str | None = None,
    ) -> dict[str, object]:
        _ = (file_path, language_hint)
        return {
            "backend": "faster-whisper",
            "text": self.transcript_text,
            "segments": [
                {
                    "text": "Alice reran the curriculum learning baseline and saw higher macro F1 on hard examples.",
                    "start": 0.0,
                    "end": 11.0,
                },
                {
                    "text": "Professor Chen asked for the hard negative ablation and retrieval assisted logging.",
                    "start": 11.0,
                    "end": 22.0,
                },
                {
                    "text": "Professor Chen also wants evidence on the curriculum learning claim.",
                    "start": 22.0,
                    "end": 28.0,
                },
            ],
            "language": "en",
            "duration_seconds": 28.0,
            "elapsed_seconds": 0.21,
        }


def build_memory_service(workspace: Path) -> ProjectMemoryService:
    sqlite_store = SQLiteStore(workspace / "memory.sqlite3")
    vector_store = LanceDBStore(workspace / "lancedb")
    return ProjectMemoryService(sqlite_store=sqlite_store, vector_store=vector_store)


def test_demo_flow_returns_stable_non_empty_outputs() -> None:
    transcript_path = Path("data/samples/demo_meeting_transcript.md")
    transcript_text = transcript_path.read_text(encoding="utf-8")
    parser = TranscriptParserService()
    transcript = parser.parse_transcript(transcript_text, meeting_id="demo-meeting-001")

    progress = ProgressExtractionService(
        client=StubChatJsonClient(
            {
                "summary": "Alice improved macro F1 on hard examples but still has calibration and logging blockers.",
                "student_progress": [
                    {
                        "student_name": "Alice",
                        "completed_work": [
                            "Reran the curriculum-learning baseline on the reviewer-comment benchmark."
                        ],
                        "current_result": "Macro F1 improved on hard examples, but calibration regressed after stage three.",
                        "blockers": [
                            "The ablation table is still incomplete.",
                            "Long-context runs fail when token-level logging is enabled.",
                        ],
                        "risks": [
                            {
                                "title": "Calibration regresses after the third curriculum stage",
                                "level": "high",
                                "description": "Calibration error still gets worse after the final stage.",
                                "owner": "Alice",
                            },
                            {
                                "title": "Retrieval logging fails on long-context runs",
                                "level": "medium",
                                "description": "The logging pipeline crashes before writing trace links.",
                                "owner": "Bob",
                            },
                        ],
                        "unresolved_questions": [
                            "Can we keep the hard-example gains without hurting calibration?"
                        ],
                        "next_step_suggestion": "Prepare a clean ablation table and isolate the logging failure.",
                        "action_items": [
                            {
                                "title": "Prepare the hard-negative curriculum ablation table",
                                "owner": "Alice",
                                "deadline": "Friday",
                                "priority": "high",
                                "status": "open",
                            },
                            {
                                "title": "Instrument retrieval-assisted logging for transcript traceability",
                                "owner": "Bob",
                                "deadline": "Tuesday",
                                "priority": "medium",
                                "status": "in_progress",
                            },
                            {
                                "title": "Share the failing trace logs with Bob",
                                "owner": "Alice",
                                "deadline": "Monday",
                                "priority": "medium",
                                "status": "open",
                            },
                        ],
                    }
                ],
            }
        )
    ).extract_progress(transcript, meeting_id="demo-meeting-001")

    ideas = IdeaCaptureService(
        client=StubChatJsonClient(
            {
                "summary": "The advisor wants one validation experiment and one workflow instrumentation experiment.",
                "ideas": [
                    {
                        "id": "demo-meeting-001-idea-01",
                        "student_name": "Alice",
                        "idea_text": "Keep the hard-negative curriculum ablation in next week's plan.",
                        "suggested_by": "Prof. Chen",
                        "expected_validation": "Improve macro F1 without hurting calibration.",
                        "validation_metrics": ["macro F1", "calibration error"],
                        "next_actions": [
                            {
                                "title": "Run the hard-negative ablation with a calibration report.",
                                "owner": "Alice",
                                "due_date": "Friday",
                                "priority": "high",
                            }
                        ],
                        "recommended_reading": [
                            {
                                "title": "Curriculum Learning for Robust Classification",
                                "source_url": "https://example.org/curriculum",
                                "reason": "Explains how to stage hard examples while tracking calibration.",
                                "priority": "high",
                            }
                        ],
                    },
                    {
                        "id": "demo-meeting-001-idea-02",
                        "student_name": "Bob",
                        "idea_text": "Test retrieval-assisted logging so every exported task maps back to a transcript slice.",
                        "suggested_by": "Prof. Chen",
                        "expected_validation": "Every action item keeps one traceable transcript anchor.",
                        "validation_metrics": ["trace coverage"],
                        "next_actions": [
                            {
                                "title": "Prototype trace-link logging on the failing run.",
                                "owner": "Bob",
                                "due_date": "Tuesday",
                                "priority": "medium",
                            }
                        ],
                        "recommended_reading": [
                            {
                                "title": "Grounded Meeting Agents With Retrieval Traces",
                                "source_url": "https://example.org/retrieval",
                                "reason": "Shows how to expose transcript-grounded evidence in agent outputs.",
                                "priority": "medium",
                            }
                        ],
                    },
                ],
            }
        )
    ).capture_ideas(transcript, meeting_id="demo-meeting-001").ideas

    research_plan = ResearchPlanService(
        client=StubChatJsonClient(
            {
                "summary": "The next week focuses on the hard-negative ablation and trace logging.",
                "tasks": [
                    {
                        "idea_id": "demo-meeting-001-idea-01",
                        "student_name": "Alice",
                        "title": "Finalize the hard-negative ablation and calibration report",
                        "owner": "Alice",
                        "due_date": "Friday",
                        "priority": "high",
                        "success_metrics": ["macro F1", "calibration error"],
                        "dependency_note": "Needs a clean ablation table.",
                        "rationale": "This is the main validation request from the advisor.",
                    },
                    {
                        "idea_id": "demo-meeting-001-idea-02",
                        "student_name": "Bob",
                        "title": "Enable retrieval-assisted logging on the failing long-context run",
                        "owner": "Bob",
                        "due_date": "Tuesday",
                        "priority": "medium",
                        "success_metrics": ["trace coverage"],
                        "dependency_note": "Requires Alice's failing traces.",
                        "rationale": "This unlocks transcript traceability for deliverables.",
                    },
                ],
                "questions_to_answer": [
                    "Can we keep the hard-example gain without worsening calibration?",
                    "Will retrieval-assisted logging survive the long-context failure mode?",
                ],
            }
        )
    ).generate_plan(transcript, ideas, progress=progress, meeting_id="demo-meeting-001")

    readings = ReadingRecommendationService(
        client=StubChatJsonClient(
            {
                "summary": "Three short readings support the two advisor ideas.",
                "recommendations": [
                    {
                        "idea_id": "demo-meeting-001-idea-01",
                        "student_name": "Alice",
                        "title": "Curriculum Learning for Robust Classification",
                        "source_url": "https://example.org/curriculum",
                        "reason": "Useful for planning the staged hard-negative experiment.",
                        "priority": "high",
                    },
                    {
                        "idea_id": "demo-meeting-001-idea-01",
                        "student_name": "Alice",
                        "title": "Calibration Under Distribution Shift",
                        "source_url": "https://example.org/calibration",
                        "reason": "Helps measure the calibration regression after stage three.",
                        "priority": "high",
                    },
                    {
                        "idea_id": "demo-meeting-001-idea-02",
                        "student_name": "Bob",
                        "title": "Grounded Meeting Agents With Retrieval Traces",
                        "source_url": "https://example.org/retrieval",
                        "reason": "Useful for transcript traceability and evidence links.",
                        "priority": "medium",
                    },
                ],
            }
        )
    ).generate_recommendations(transcript, ideas, progress=progress, meeting_id="demo-meeting-001")

    claims = ClaimExtractionService(
        client=StubChatJsonClient(
            {
                "summary": "One evidence-sensitive claim is worth tracking.",
                "claims": [
                    {
                        "id": "demo-meeting-001-claim-01",
                        "text": "Curriculum learning consistently improves hard-example macro F1 in small-data settings.",
                        "speaker": "Prof. Chen",
                        "timestamp_start": "00:01:39",
                        "transcript_snippet": "One claim we should verify is whether curriculum learning consistently improves hard-example macro F1 in small-data settings.",
                        "claim_kind": "factual",
                        "confidence": "medium",
                    }
                ],
            }
        )
    ).extract_claims(transcript, meeting_id="demo-meeting-001").claims

    verification = ClaimVerificationService(
        client=StubChatJsonClient(
            {
                "summary": "The evidence is still incomplete, so the claim needs verification.",
                "verdict": "needs_verification",
                "confidence": "medium",
                "gaps": ["Need a paper focused on small-data settings rather than general curriculum learning."],
                "evidence_assessments": [
                    {
                        "evidence_id": "demo-ev-01",
                        "stance": "needs_verification",
                        "reason": "The source is related but not specific enough to the small-data claim.",
                        "confidence": "medium",
                    }
                ],
            }
        )
    ).verify_claim(
        claims[0],
        [
            EvidenceCard(
                id="demo-ev-01",
                claim_id=claims[0].id,
                source_title="Curriculum Learning for Robust Classification",
                source_url="https://example.org/curriculum",
                source_type="paper",
                snippet="The paper reports gains on hard examples, but does not focus on small-data settings.",
            )
        ],
    )

    workspace = Path("backend/storage/.tmp") / f"demo-flow-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        memory_service = build_memory_service(workspace)
        action_items = list(progress.action_items)
        action_items.extend(
            [
                ActionItem(
                    meeting_id="demo-meeting-001",
                    student_name=task.student_name,
                    title=task.title,
                    owner=task.owner,
                    deadline=task.due_date,
                    priority=task.priority,
                    status="open",
                    dependency_note=task.dependency_note,
                )
                for task in research_plan.tasks
            ]
        )
        key_papers = [
            KeyPaperMemory(
                id=reading.id or f"paper-{index:02d}",
                project_id="project-demo-001",
                meeting_id="demo-meeting-001",
                title=reading.title,
                source_url=reading.source_url,
                reason=reading.reason,
            )
            for index, reading in enumerate(readings.recommendations, start=1)
        ]

        project = ProjectRecord(
            project_id="project-demo-001",
            name="EvidenceFlow Demo Project",
            description="Deterministic demo fixture for the stage-5 workflow.",
            domain="research-automation",
        )
        meeting = ProjectMeetingRecord(
            meeting_id="demo-meeting-001",
            project_id="project-demo-001",
            title="Demo Weekly Group Meeting",
            summary=progress.summary,
        )
        snapshot = memory_service.remember_meeting(
            project,
            meeting,
            decisions=[
                ProjectDecision(
                    id="decision-001",
                    title="Keep the hard-negative ablation and retrieval-assisted logging in the next sprint.",
                    rationale="Both items came directly from the advisor and unblock next week's demo.",
                    decided_by="Prof. Chen",
                )
            ],
            action_items=action_items,
            claims=[verification.claim],
            advisor_ideas=ideas,
            student_progress=progress.student_progress,
            key_papers=key_papers,
            transcript=transcript,
        )

        briefing = BriefingService().generate_briefing(snapshot)
        deliverable_service = DeliverableService()
        weekly_report = deliverable_service.generate_deliverable(
            "weekly_report",
            project_memory=snapshot,
            briefing=briefing,
        )
        next_week_plan = deliverable_service.generate_deliverable(
            "next_week_research_plan",
            project_memory=snapshot,
            briefing=briefing,
        )
        outline = deliverable_service.generate_deliverable(
            "presentation_outline",
            project_memory=snapshot,
            briefing=briefing,
        )

        assert transcript.chunks
        assert progress.student_progress
        assert ideas
        assert research_plan.tasks
        assert readings.recommendations
        assert claims
        assert isinstance(verification, ClaimVerificationResult)
        assert briefing.recommended_agenda
        assert "## Student Progress" in weekly_report.content_markdown
        assert "## Priority Tasks" in next_week_plan.content_markdown
        assert "## 5. Next-week execution plan" in outline.content_markdown
        assert "hard-negative ablation" in weekly_report.content_markdown.lower()
        assert "retrieval-assisted logging" in next_week_plan.content_markdown.lower()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_demo_audio_import_flow_returns_stable_non_empty_outputs() -> None:
    transcript_text = Path("data/samples/demo_meeting_transcript.md").read_text(encoding="utf-8")
    audio_bytes = Path("data/samples/demo_meeting_audio.wav").read_bytes()
    workspace = Path("backend/storage/.tmp") / f"demo-audio-flow-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        settings = load_settings(
            env={
                "DATA_DIR": str(workspace),
                "SQLITE_PATH": str(workspace / "demo-audio.sqlite3"),
                "LANCEDB_PATH": str(workspace / "lancedb"),
            },
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / ".env",
        )
        transcription_service = TranscriptionService(
            settings=settings,
            audio_transcriber=StubAudioTranscriber(transcript_text),
        )
        imported = transcription_service.import_uploaded_audio(
            file_bytes=audio_bytes,
            filename="demo_meeting_audio.wav",
            content_type="audio/wav",
            meeting_title="Demo Audio Meeting",
            language_hint="en",
        )
        transcript = transcription_service.load_transcript(imported.meeting.meeting_id)

        progress = ProgressExtractionService(
            client=StubChatJsonClient(
                {
                    "summary": "Audio import preserved Alice's progress, blockers, and advisor follow-ups.",
                    "student_progress": [
                        {
                            "student_name": "Alice",
                            "completed_work": [
                                "Reran the curriculum-learning baseline on the reviewer-comment benchmark."
                            ],
                            "current_result": "Hard-example macro F1 improved, but calibration still regresses.",
                            "blockers": [
                                "The ablation table is incomplete.",
                                "Long-context token logging still fails.",
                            ],
                            "risks": [
                                {
                                    "title": "Calibration still regresses after stage three",
                                    "level": "high",
                                    "description": "The audio-derived transcript still shows a calibration concern.",
                                }
                            ],
                            "next_step_suggestion": "Finish the ablation table and stabilize trace logging.",
                        }
                    ],
                }
            )
        ).extract_progress(transcript, meeting_id=imported.meeting.meeting_id)

        ideas = IdeaCaptureService(
            client=StubChatJsonClient(
                {
                    "summary": "Two advisor ideas survive the audio import path.",
                    "ideas": [
                        {
                            "id": f"{imported.meeting.meeting_id}-idea-01",
                            "student_name": "Alice",
                            "idea_text": "Keep the hard-negative curriculum ablation in next week's plan.",
                            "suggested_by": "Prof. Chen",
                            "expected_validation": "Improve macro F1 without hurting calibration.",
                            "validation_metrics": ["macro F1", "calibration error"],
                        },
                        {
                            "id": f"{imported.meeting.meeting_id}-idea-02",
                            "student_name": "Bob",
                            "idea_text": "Test retrieval-assisted logging for transcript traceability.",
                            "suggested_by": "Prof. Chen",
                            "expected_validation": "Every action item keeps one traceable chunk.",
                            "validation_metrics": ["trace coverage"],
                        },
                    ],
                }
            )
        ).capture_ideas(transcript, meeting_id=imported.meeting.meeting_id).ideas

        research_plan = ResearchPlanService(
            client=StubChatJsonClient(
                {
                    "summary": "The audio path still yields a concrete next-week plan.",
                    "tasks": [
                        {
                            "idea_id": f"{imported.meeting.meeting_id}-idea-01",
                            "student_name": "Alice",
                            "title": "Finalize the hard-negative ablation and calibration report",
                            "owner": "Alice",
                            "due_date": "Friday",
                            "priority": "high",
                            "success_metrics": ["macro F1", "calibration error"],
                            "dependency_note": "Needs a clean ablation table.",
                            "rationale": "This is the main advisor request carried through the audio flow.",
                        }
                    ],
                }
            )
        ).generate_plan(
            transcript,
            ideas,
            progress=progress,
            meeting_id=imported.meeting.meeting_id,
        )

        readings = ReadingRecommendationService(
            client=StubChatJsonClient(
                {
                    "summary": "Audio import still yields non-empty reading recommendations.",
                    "recommendations": [
                        {
                            "idea_id": f"{imported.meeting.meeting_id}-idea-01",
                            "student_name": "Alice",
                            "title": "Curriculum Learning for Robust Classification",
                            "source_url": "https://example.org/curriculum",
                            "reason": "Useful for planning the staged hard-negative experiment.",
                            "priority": "high",
                        }
                    ],
                }
            )
        ).generate_recommendations(
            transcript,
            ideas,
            progress=progress,
            meeting_id=imported.meeting.meeting_id,
        )

        assert imported.meeting.source_type == "audio"
        assert imported.meeting.transcription_status == "completed"
        assert transcript.chunks
        assert progress.student_progress
        assert ideas
        assert research_plan.tasks
        assert readings.recommendations
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
