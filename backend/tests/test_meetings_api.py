from __future__ import annotations

import asyncio
import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from backend.app import create_app
from backend.api.meetings import (
    MeetingReviewRequest,
    get_transcription_service,
    get_meeting_progress,
    import_audio_meeting,
    import_meeting,
    process_meeting,
    review_meeting,
)
from backend.schemas.claim import Claim, ClaimExtractionResult, ClaimVerificationResult
from backend.schemas.evidence_card import EvidenceCard
from backend.config import load_settings
from backend.schemas.meeting import MeetingImportRequest, ParsedTranscript, TranscriptChunk
from backend.schemas.project_memory import (
    ProjectMeetingRecord,
    ProjectMemorySnapshot,
    ProjectRecord,
)
from backend.schemas.reading_recommendation import ReadingRecommendationBatch
from backend.schemas.research_idea import AdvisorIdeaCaptureResult, ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot, StudentProgress
from backend.services.briefing_service import BriefingResult
from backend.services.deliverable_service import DeliverableBundle, DeliverableDocument
from backend.services.research_plan_service import ResearchPlanResult, ResearchPlanTask
from backend.services.transcription_service import TranscriptionService


class FakeAudioTranscriber:
    def __init__(self, *, text: str = "", segments: list[dict[str, object]] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.text = text
        self.segments = segments or []

    def transcribe_file(
        self,
        file_path: str | Path,
        *,
        language_hint: str | None = None,
    ) -> dict[str, object]:
        self.calls.append({"file_path": str(file_path), "language_hint": language_hint})
        return {
            "backend": "faster-whisper",
            "text": self.text,
            "segments": self.segments,
            "language": language_hint or "en",
            "warnings": ["Speaker diarization is disabled in P0."],
            "duration_seconds": 22.8,
            "elapsed_seconds": 0.47,
        }


class FakeProgressExtractionService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def extract_progress(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
    ) -> MeetingProgressSnapshot:
        resolved_meeting_id = meeting_id or transcript.meeting_id or "missing-meeting-id"
        self.calls.append(resolved_meeting_id)
        return MeetingProgressSnapshot(
            meeting_id=resolved_meeting_id,
            summary="Students reported progress and blockers.",
            student_progress=[
                StudentProgress(
                    meeting_id=resolved_meeting_id,
                    student_name="Alice",
                    completed_work=["Finished the baseline."],
                    current_result="Baseline is ready for review.",
                    blockers=["Need one more ablation."],
                )
            ],
        )


class FakeIdeaCaptureService:
    def capture_ideas(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
    ) -> AdvisorIdeaCaptureResult:
        resolved_meeting_id = meeting_id or transcript.meeting_id or "missing-meeting-id"
        return AdvisorIdeaCaptureResult(
            meeting_id=resolved_meeting_id,
            summary="One advisor idea is active.",
            ideas=[
                ResearchIdea(
                    id=f"{resolved_meeting_id}-idea-01",
                    meeting_id=resolved_meeting_id,
                    student_name="Alice",
                    idea_text="Run one more ablation before Friday.",
                    expected_validation="Validate the baseline change.",
                    validation_metrics=["macro F1"],
                )
            ],
        )


class FakeResearchPlanService:
    def generate_plan(
        self,
        transcript: ParsedTranscript,
        ideas: list[ResearchIdea],
        *,
        progress: MeetingProgressSnapshot | None = None,
        meeting_id: str | None = None,
    ) -> ResearchPlanResult:
        _ = (transcript, ideas, progress)
        resolved_meeting_id = meeting_id or "missing-meeting-id"
        return ResearchPlanResult(
            meeting_id=resolved_meeting_id,
            summary="One next-week task was generated.",
            tasks=[
                ResearchPlanTask(
                    meeting_id=resolved_meeting_id,
                    idea_id=f"{resolved_meeting_id}-idea-01",
                    student_name="Alice",
                    title="Run the follow-up ablation",
                    owner="Alice",
                    due_date="Friday",
                    priority="high",
                    success_metrics=["macro F1"],
                    dependency_note="Needs one more clean run.",
                    rationale="Advisor requested a tighter validation pass.",
                )
            ],
        )


class FakeReadingRecommendationService:
    def generate_recommendations(
        self,
        transcript: ParsedTranscript,
        ideas: list[ResearchIdea],
        *,
        progress: MeetingProgressSnapshot | None = None,
        meeting_id: str | None = None,
    ) -> ReadingRecommendationBatch:
        _ = (transcript, ideas, progress)
        resolved_meeting_id = meeting_id or "missing-meeting-id"
        return ReadingRecommendationBatch(
            meeting_id=resolved_meeting_id,
            summary="One paper is enough for this fake flow.",
            recommendations=[],
        )


class FakeClaimExtractionService:
    def extract_claims(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
    ) -> ClaimExtractionResult:
        _ = transcript
        resolved_meeting_id = meeting_id or "missing-meeting-id"
        return ClaimExtractionResult(
            meeting_id=resolved_meeting_id,
            summary="One claim extracted.",
            claims=[
                Claim(
                    id=f"{resolved_meeting_id}-claim-01",
                    meeting_id=resolved_meeting_id,
                    text="The baseline is ready for review.",
                    speaker="Alice",
                    transcript_snippet="Finished the baseline.",
                )
            ],
        )


class FakeClaimVerificationService:
    def verify_claim(self, claim: Claim) -> ClaimVerificationResult:
        return ClaimVerificationResult(
            claim=claim.model_copy(update={"verification_status": "supported"}),
            verdict="supported",
            confidence="high",
            summary="The fake evidence supports the claim.",
            evidence_cards=[
                EvidenceCard(
                    id=f"{claim.id}-evidence-01",
                    claim_id=claim.id,
                    source_title="Fake note",
                    source_type="project_note",
                    snippet="Finished the baseline.",
                    stance="support",
                    confidence="high",
                )
            ],
        )


class FakeProjectMemoryService:
    def remember_meeting(self, project: ProjectRecord, meeting: ProjectMeetingRecord, **_: object) -> ProjectMemorySnapshot:
        return ProjectMemorySnapshot(
            project=project,
            meetings=[meeting],
            action_items=[],
            claims=[],
            advisor_ideas=[],
            student_progress=[],
            key_papers=[],
        )


class FakeBriefingService:
    def generate_briefing(self, project_memory: ProjectMemorySnapshot) -> BriefingResult:
        assert project_memory.project is not None
        return BriefingResult(
            project_id=project_memory.project.project_id,
            project_name=project_memory.project.name,
            summary="Fake briefing summary.",
            focus_questions=["What changed since last week?"],
        )


class FakeDeliverableService:
    def generate_all(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> DeliverableBundle:
        assert project_memory.project is not None
        return DeliverableBundle(
            project_id=project_memory.project.project_id,
            documents=[
                DeliverableDocument(
                    deliverable_type="weekly_report",
                    title=f"Weekly Report - {briefing.project_name}",
                    content_markdown="# Weekly Report\n\nFake content.",
                )
            ],
        )


def make_workspace_temp_dir() -> Path:
    temp_root = Path("backend/tests/.tmp")
    temp_root.mkdir(parents=True, exist_ok=True)
    workspace = (temp_root / f"meetings-api-{uuid4().hex[:8]}").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def make_upload_file(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_meetings_api_import_process_and_get_progress() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(settings=settings)
        progress_service = FakeProgressExtractionService()

        async def run_flow() -> None:
            imported = await import_meeting(
                MeetingImportRequest(
                    source_type="transcript",
                    transcript_text=(
                        "[00:00:01] Alice: Finished the baseline.\n"
                        "[00:00:09] Prof. Chen: Add one more ablation before Friday."
                    ),
                ),
                transcription_service=transcription_service,
            )

            processed = await process_meeting(
                imported.meeting.meeting_id,
                transcription_service=transcription_service,
                progress_service=progress_service,
            )
            fetched = await get_meeting_progress(
                imported.meeting.meeting_id,
                transcription_service=transcription_service,
            )

            assert progress_service.calls == [imported.meeting.meeting_id]
            assert processed.meeting.status == "processed"
            assert fetched.summary == "Students reported progress and blockers."
            assert fetched.student_progress[0].student_name == "Alice"
            assert Path(imported.meeting.parsed_transcript_path).exists()

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def test_fake_progress_service_matches_expected_schema() -> None:
    parsed = ParsedTranscript(
        meeting_id="meeting-123",
        chunks=[
            TranscriptChunk(
                chunk_id="chunk-0001",
                speaker="Alice",
                text="Finished the baseline.",
            )
        ],
    )
    snapshot = FakeProgressExtractionService().extract_progress(parsed, meeting_id="meeting-123")

    assert snapshot.meeting_id == "meeting-123"
    assert snapshot.student_progress[0].current_result == "Baseline is ready for review."


def test_review_meeting_aggregates_pipeline_outputs() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(settings=settings)

        async def run_flow() -> None:
            imported = await import_meeting(
                MeetingImportRequest(
                    meeting_title="Integration Review",
                    source_type="transcript",
                    transcript_text=(
                        "[00:00:01] Alice: Finished the baseline.\n"
                        "[00:00:09] Prof. Chen: Add one more ablation before Friday."
                    ),
                ),
                transcription_service=transcription_service,
            )

            reviewed = await review_meeting(
                imported.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="project-001",
                    project_name="Integration Project",
                    verify_claims=True,
                    max_claims_to_verify=1,
                ),
                transcription_service=transcription_service,
                progress_service=FakeProgressExtractionService(),
                idea_capture_service=FakeIdeaCaptureService(),
                research_plan_service=FakeResearchPlanService(),
                reading_service=FakeReadingRecommendationService(),
                claim_extraction_service=FakeClaimExtractionService(),
                claim_verification_service=FakeClaimVerificationService(),
                project_memory_service=FakeProjectMemoryService(),
                briefing_service=FakeBriefingService(),
                deliverable_service=FakeDeliverableService(),
            )

            assert reviewed.project.project_id == "project-001"
            assert reviewed.meeting.status == "processed"
            assert reviewed.progress.summary == "Students reported progress and blockers."
            assert reviewed.ideas.ideas[0].idea_text == "Run one more ablation before Friday."
            assert reviewed.research_plan.tasks[0].title == "Run the follow-up ablation"
            assert reviewed.claims[0].verdict == "supported"
            assert reviewed.briefing.summary == "Fake briefing summary."
            assert reviewed.deliverables[0].deliverable_type == "weekly_report"

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def test_transcription_service_imports_uploaded_audio_and_persists_metadata() -> None:
    data_dir = make_workspace_temp_dir()
    transcriber = FakeAudioTranscriber(
        text="Alice finished the baseline. Prof. Chen requested one more ablation.",
        segments=[
            {"text": "Alice finished the baseline.", "start": 0.0, "end": 6.2, "speaker": "Unknown"},
            {"text": "Prof. Chen requested one more ablation.", "start": 6.2, "end": 12.5},
        ],
    )
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(
            settings=settings,
            audio_transcriber=transcriber,
        )

        response = transcription_service.import_uploaded_audio(
            file_bytes=b"RIFFdemo-audio",
            filename="demo-meeting.wav",
            content_type="audio/wav",
            meeting_title="Audio Demo Meeting",
            language_hint="en",
        )

        meeting = response.meeting
        metadata = transcription_service.load_transcription_metadata(meeting.meeting_id)

        assert meeting.source_type == "audio"
        assert meeting.transcription_status == "completed"
        assert meeting.transcription_backend == "faster-whisper"
        assert meeting.audio_filename == "demo-meeting.wav"
        assert meeting.audio_content_type == "audio/wav"
        assert meeting.audio_size_bytes == len(b"RIFFdemo-audio")
        assert Path(meeting.audio_path or "").exists()
        assert Path(meeting.transcription_metadata_path or "").exists()
        assert Path(meeting.transcript_path).exists()
        assert Path(meeting.parsed_transcript_path).exists()
        assert response.transcript.chunk_count == 2
        assert response.transcript.chunks[0].timestamp_start == "00:00"
        assert metadata.language_hint == "en"
        assert metadata.detected_language == "en"
        assert metadata.segment_count == 2
        assert metadata.warning_messages == ["Speaker diarization is disabled in P0."]
        assert transcriber.calls[0]["language_hint"] == "en"
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def test_import_audio_meeting_endpoint_rejects_unsupported_audio_format() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(
            settings=settings,
            audio_transcriber=FakeAudioTranscriber(),
        )

        async def run_flow() -> None:
            try:
                await import_audio_meeting(
                    transcription_service=transcription_service,
                    file=make_upload_file("meeting.flac", b"demo", "audio/flac"),
                    meeting_title="Bad Audio",
                )
            except HTTPException as exc:
                assert exc.status_code == 400
                assert "Unsupported audio format" in str(exc.detail)
            else:
                raise AssertionError("Unsupported audio upload should fail.")

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def test_audio_import_can_continue_into_review_pipeline() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(
            settings=settings,
            audio_transcriber=FakeAudioTranscriber(
                text="Alice finished the baseline. Prof. Chen requested a follow-up ablation.",
                segments=[
                    {"text": "Alice finished the baseline.", "start": 0.0, "end": 5.2},
                    {"text": "Prof. Chen requested a follow-up ablation.", "start": 5.2, "end": 11.9},
                ],
            ),
        )

        async def run_flow() -> None:
            imported = await import_audio_meeting(
                transcription_service=transcription_service,
                file=make_upload_file("demo.wav", b"RIFFdemo-audio", "audio/wav"),
                meeting_title="Audio Review",
                language_hint="en",
            )

            reviewed = await review_meeting(
                imported.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="audio-project",
                    project_name="Audio Project",
                    verify_claims=True,
                    max_claims_to_verify=1,
                ),
                transcription_service=transcription_service,
                progress_service=FakeProgressExtractionService(),
                idea_capture_service=FakeIdeaCaptureService(),
                research_plan_service=FakeResearchPlanService(),
                reading_service=FakeReadingRecommendationService(),
                claim_extraction_service=FakeClaimExtractionService(),
                claim_verification_service=FakeClaimVerificationService(),
                project_memory_service=FakeProjectMemoryService(),
                briefing_service=FakeBriefingService(),
                deliverable_service=FakeDeliverableService(),
            )

            assert reviewed.meeting.meeting_id == imported.meeting.meeting_id
            assert reviewed.meeting.status == "processed"
            assert reviewed.transcript.chunk_count == 2
            assert reviewed.progress.student_progress
            assert reviewed.research_plan.tasks
            assert reviewed.deliverables

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


def test_import_audio_route_accepts_multipart_upload() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        transcription_service = TranscriptionService(
            settings=settings,
            audio_transcriber=FakeAudioTranscriber(
                text="Alice finished the baseline. Prof. Chen requested one more ablation.",
                segments=[
                    {"text": "Alice finished the baseline.", "start": 0.0, "end": 6.2},
                    {"text": "Prof. Chen requested one more ablation.", "start": 6.2, "end": 12.5},
                ],
            ),
        )
        app = create_app()
        app.dependency_overrides[get_transcription_service] = lambda: transcription_service
        client = TestClient(app)

        response = client.post(
            "/api/meetings/import-audio",
            data={
                "meeting_title": "Multipart Audio Meeting",
                "language_hint": "en",
            },
            files={
                "file": ("demo.wav", b"RIFFdemo-audio", "audio/wav"),
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["meeting"]["source_type"] == "audio"
        assert payload["meeting"]["transcription_status"] == "completed"
        assert payload["meeting"]["audio_filename"] == "demo.wav"
        assert payload["transcript"]["chunk_count"] == 2
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)
