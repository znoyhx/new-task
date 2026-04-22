from __future__ import annotations

import asyncio
import os
import shutil
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from starlette.datastructures import Headers, UploadFile

from backend.api.meetings import (
    MeetingReviewRequest,
    import_audio_meeting,
    import_meeting,
    review_meeting,
)
from backend.config import load_settings
from backend.schemas.meeting import MeetingImportRequest
from backend.services.briefing_service import BriefingService
from backend.services.claim_extraction_service import ClaimExtractionService
from backend.services.claim_verification_service import ClaimVerificationService
from backend.services.deliverable_service import DeliverableService
from backend.services.evidence_retrieval_service import EvidenceRetrievalService
from backend.services.idea_capture_service import IdeaCaptureService
from backend.services.progress_extraction_service import ProgressExtractionService
from backend.services.project_memory_service import ProjectMemoryService
from backend.services.reading_recommendation_service import ReadingRecommendationService
from backend.services.research_plan_service import ResearchPlanService
from backend.services.transcription_service import TranscriptionService

LIVE_TRANSCRIPT = """
[00:00:05] Alice: This week I trained the baseline on 3k samples and reached 71 percent accuracy.
[00:00:18] Alice: The blocker is GPU memory. The 13B model runs out of memory at batch size four.
[00:00:31] Prof. Chen: Next week compare QLoRA with the smaller model and prepare a short result table by Friday.
[00:00:45] Prof. Chen: Read one paper on curriculum learning, one on small-model adaptation, and keep one evidence-sensitive claim visible in the dashboard.
[00:00:58] Bob: I reproduced the retrieval pipeline, but the citation parser still drops equations in long papers.
"""

LIVE_CONTINUITY_MEETING_A = """
[00:00:05] Alice: This week I reran the baseline and reached 71 percent macro F1 on the validation split.
[00:00:18] Alice: The blocker is that hard examples still fail and the ablation table is incomplete.
[00:00:31] Prof. Chen: Next week run a hard-negative ablation, prepare a clean comparison table, and keep the task visible until it is done.
[00:00:46] Prof. Chen: Read one paper on curriculum learning and one paper on imbalance-aware losses before the next meeting.
"""

LIVE_CONTINUITY_MEETING_B = """
[00:00:05] Alice: I finished one hard-negative rerun, but the comparison table is still incomplete and the carryover task is not closed.
[00:00:20] Alice: The macro F1 gain looks promising, but I still need one clean seed sweep before we can trust it.
[00:00:34] Prof. Chen: Keep the hard-negative ablation as an unfinished carryover task, make it the first item in next week's plan, and mention it in the briefing.
[00:00:50] Prof. Chen: Reuse last week's context so the next meeting starts from the unresolved ablation instead of summarizing from scratch.
"""

REAL_MODEL_STAGE_KEYS = {
    "progress-extraction",
    "idea-capture",
    "plan-generation",
    "reading-recommendation",
    "evidence-verification",
}


def load_live_settings_or_skip():
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        pytest.skip("Repository .env file is required for the DeepSeek live tests.")

    workspace = Path("backend/storage/.tmp") / f"live-review-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    settings = load_settings(
        env={
            "DATA_DIR": str(workspace),
            "SQLITE_PATH": str(workspace / "evidenceflow-live.sqlite3"),
            "LANCEDB_PATH": str(workspace / "lancedb"),
        },
        repo_root=Path.cwd(),
        dotenv_path=dotenv_path,
    )
    if not settings.deepseek_api_key:
        pytest.skip("DEEPSEEK_API_KEY is not configured.")
    return settings, workspace


def make_audio_upload_file(audio_path: Path) -> UploadFile:
    suffix = audio_path.suffix.lower()
    content_type = "audio/wav" if suffix == ".wav" else "application/octet-stream"
    return UploadFile(
        file=BytesIO(audio_path.read_bytes()),
        filename=audio_path.name,
        headers=Headers({"content-type": content_type}),
    )


def _format_input_sources(stage) -> str:
    parts: list[str] = []
    for source in stage.input_sources:
        segment = source.label
        if source.detail:
            segment = f"{segment}: {source.detail}"
        parts.append(segment)
    return " | ".join(parts) if parts else "none"


def print_review_trace(prefix: str, reviewed) -> None:
    print(f"{prefix}_provider={reviewed.orchestration.llm_provider}")
    print(f"{prefix}_model={reviewed.orchestration.llm_model}")
    print(
        f"{prefix}_hit_real_deepseek="
        f"{reviewed.orchestration.llm_provider.lower() == 'deepseek'}"
    )
    if reviewed.orchestration.memory_usage is not None:
        print(
            f"{prefix}_memory_usage="
            f"prior_meetings={reviewed.orchestration.memory_usage.prior_meeting_count};"
            f"open_tasks={reviewed.orchestration.memory_usage.open_task_count};"
            f"recent_decisions={reviewed.orchestration.memory_usage.recent_decision_count};"
            f"relevant_context={reviewed.orchestration.memory_usage.relevant_context_count}"
        )

    for stage in reviewed.orchestration.stages:
        print(
            f"{prefix}_stage="
            f"{stage.stage_key}"
            f"|agent={stage.agent_name}"
            f"|status={stage.status}"
            f"|real_model_call={stage.stage_key in REAL_MODEL_STAGE_KEYS}"
            f"|goal={stage.goal}"
            f"|inputs={_format_input_sources(stage)}"
            f"|output={stage.output_summary or stage.output_target.label}"
            f"|fallback_used={stage.fallback.used}"
            f"|fallback={stage.fallback.summary}"
            f"|error={stage.error_detail or 'none'}"
        )


def test_live_review_meeting_pipeline_with_deepseek() -> None:
    settings, workspace = load_live_settings_or_skip()
    try:
        transcription_service = TranscriptionService(settings=settings)
        progress_service = ProgressExtractionService()
        idea_service = IdeaCaptureService()
        research_plan_service = ResearchPlanService()
        reading_service = ReadingRecommendationService()
        claim_extraction_service = ClaimExtractionService()
        claim_verification_service = ClaimVerificationService(
            retrieval_service=EvidenceRetrievalService()
        )
        project_memory_service = ProjectMemoryService(settings=settings)
        briefing_service = BriefingService()
        deliverable_service = DeliverableService()

        async def run_flow():
            imported = await import_meeting(
                MeetingImportRequest(
                    meeting_title="Live Review Meeting",
                    source_type="transcript",
                    transcript_text=LIVE_TRANSCRIPT,
                ),
                transcription_service=transcription_service,
            )

            started_at = time.time()
            reviewed = await review_meeting(
                imported.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="live-review-project",
                    project_name="Live Review Project",
                    verify_claims=True,
                    max_claims_to_verify=1,
                ),
                transcription_service=transcription_service,
                progress_service=progress_service,
                idea_capture_service=idea_service,
                research_plan_service=research_plan_service,
                reading_service=reading_service,
                claim_extraction_service=claim_extraction_service,
                claim_verification_service=claim_verification_service,
                project_memory_service=project_memory_service,
                briefing_service=briefing_service,
                deliverable_service=deliverable_service,
            )
            elapsed_seconds = time.time() - started_at

            print(f"live_review_elapsed_seconds={elapsed_seconds:.2f}")
            print(f"live_review_progress_summary={reviewed.progress.summary}")
            print(f"live_review_idea_count={len(reviewed.ideas.ideas)}")
            print(f"live_review_task_count={len(reviewed.research_plan.tasks)}")
            print(f"live_review_reading_count={len(reviewed.reading_recommendations.recommendations)}")
            print(f"live_review_claim_count={len(reviewed.claims)}")
            print(f"live_review_deliverable_count={len(reviewed.deliverables)}")
            print_review_trace("live_review", reviewed)

            assert reviewed.project.project_id == "live-review-project"
            assert reviewed.meeting.status == "processed"
            assert reviewed.progress.student_progress
            assert reviewed.ideas.ideas
            assert reviewed.research_plan.tasks
            assert reviewed.reading_recommendations.recommendations
            assert reviewed.deliverables

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_live_audio_review_pipeline_with_deepseek() -> None:
    settings, workspace = load_live_settings_or_skip()
    sample_audio_path = Path("data/samples/demo_meeting_audio.wav")
    if not sample_audio_path.exists():
        pytest.skip("Audio sample is required for the audio live review test.")

    original_model_size = os.environ.get("FASTER_WHISPER_MODEL_SIZE")
    os.environ["FASTER_WHISPER_MODEL_SIZE"] = original_model_size or "tiny.en"
    try:
        transcription_service = TranscriptionService(settings=settings)
        progress_service = ProgressExtractionService()
        idea_service = IdeaCaptureService()
        research_plan_service = ResearchPlanService()
        reading_service = ReadingRecommendationService()
        claim_extraction_service = ClaimExtractionService()
        claim_verification_service = ClaimVerificationService(
            retrieval_service=EvidenceRetrievalService()
        )
        project_memory_service = ProjectMemoryService(settings=settings)
        briefing_service = BriefingService()
        deliverable_service = DeliverableService()

        async def run_flow():
            imported = await import_audio_meeting(
                transcription_service=transcription_service,
                file=make_audio_upload_file(sample_audio_path),
                meeting_title="Live Audio Review Meeting",
                language_hint="en",
            )

            started_at = time.time()
            reviewed = await review_meeting(
                imported.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="live-audio-project",
                    project_name="Live Audio Project",
                    verify_claims=False,
                    max_claims_to_verify=0,
                ),
                transcription_service=transcription_service,
                progress_service=progress_service,
                idea_capture_service=idea_service,
                research_plan_service=research_plan_service,
                reading_service=reading_service,
                claim_extraction_service=claim_extraction_service,
                claim_verification_service=claim_verification_service,
                project_memory_service=project_memory_service,
                briefing_service=briefing_service,
                deliverable_service=deliverable_service,
            )
            elapsed_seconds = time.time() - started_at

            print(f"live_audio_review_elapsed_seconds={elapsed_seconds:.2f}")
            print(f"live_audio_transcript_chunk_count={reviewed.transcript.chunk_count}")
            print(f"live_audio_progress_summary={reviewed.progress.summary}")
            print(f"live_audio_idea_count={len(reviewed.ideas.ideas)}")
            print(f"live_audio_task_count={len(reviewed.research_plan.tasks)}")
            print(f"live_audio_reading_count={len(reviewed.reading_recommendations.recommendations)}")
            print(f"live_audio_deliverable_count={len(reviewed.deliverables)}")
            print_review_trace("live_audio", reviewed)

            assert reviewed.project.project_id == "live-audio-project"
            assert reviewed.meeting.source_type == "audio"
            assert reviewed.meeting.status == "processed"
            assert reviewed.meeting.transcription_status == "completed"
            assert reviewed.transcript.chunks
            assert reviewed.progress.student_progress
            assert reviewed.ideas.ideas
            assert reviewed.research_plan.tasks
            assert reviewed.reading_recommendations.recommendations
            assert reviewed.deliverables

        asyncio.run(run_flow())
    finally:
        if original_model_size is None:
            os.environ.pop("FASTER_WHISPER_MODEL_SIZE", None)
        else:
            os.environ["FASTER_WHISPER_MODEL_SIZE"] = original_model_size
        shutil.rmtree(workspace, ignore_errors=True)


def test_live_review_meeting_continuity_with_deepseek() -> None:
    settings, workspace = load_live_settings_or_skip()
    try:
        transcription_service = TranscriptionService(settings=settings)
        progress_service = ProgressExtractionService()
        idea_service = IdeaCaptureService()
        research_plan_service = ResearchPlanService()
        reading_service = ReadingRecommendationService()
        claim_extraction_service = ClaimExtractionService()
        claim_verification_service = ClaimVerificationService(
            retrieval_service=EvidenceRetrievalService()
        )
        project_memory_service = ProjectMemoryService(settings=settings)
        briefing_service = BriefingService()
        deliverable_service = DeliverableService()

        async def run_flow():
            imported_a = await import_meeting(
                MeetingImportRequest(
                    meeting_title="Live Continuity Meeting A",
                    source_type="transcript",
                    transcript_text=LIVE_CONTINUITY_MEETING_A,
                ),
                transcription_service=transcription_service,
            )

            reviewed_a = await review_meeting(
                imported_a.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="live-continuity-project",
                    project_name="Live Continuity Project",
                    verify_claims=False,
                    max_claims_to_verify=0,
                ),
                transcription_service=transcription_service,
                progress_service=progress_service,
                idea_capture_service=idea_service,
                research_plan_service=research_plan_service,
                reading_service=reading_service,
                claim_extraction_service=claim_extraction_service,
                claim_verification_service=claim_verification_service,
                project_memory_service=project_memory_service,
                briefing_service=briefing_service,
                deliverable_service=deliverable_service,
            )

            imported_b = await import_meeting(
                MeetingImportRequest(
                    meeting_title="Live Continuity Meeting B",
                    source_type="transcript",
                    transcript_text=LIVE_CONTINUITY_MEETING_B,
                ),
                transcription_service=transcription_service,
            )

            started_at = time.time()
            reviewed_b = await review_meeting(
                imported_b.meeting.meeting_id,
                MeetingReviewRequest(
                    project_id="live-continuity-project",
                    project_name="Live Continuity Project",
                    verify_claims=False,
                    max_claims_to_verify=0,
                ),
                transcription_service=transcription_service,
                progress_service=progress_service,
                idea_capture_service=idea_service,
                research_plan_service=research_plan_service,
                reading_service=reading_service,
                claim_extraction_service=claim_extraction_service,
                claim_verification_service=claim_verification_service,
                project_memory_service=project_memory_service,
                briefing_service=briefing_service,
                deliverable_service=deliverable_service,
            )
            elapsed_seconds = time.time() - started_at

            print(f"live_continuity_elapsed_seconds={elapsed_seconds:.2f}")
            print(
                f"live_continuity_hit_real_deepseek="
                f"{reviewed_b.orchestration.llm_provider.lower() == 'deepseek'}"
            )
            print(
                f"live_continuity_meeting_a_tasks="
                f"{len(reviewed_a.research_plan.tasks)}"
            )
            print(
                f"live_continuity_meeting_b_tasks="
                f"{len(reviewed_b.research_plan.tasks)}"
            )
            print(
                f"live_continuity_briefing_carryover="
                f"{len(reviewed_b.briefing.carryover_tasks)}"
            )
            print_review_trace("live_continuity_a", reviewed_a)
            print_review_trace("live_continuity_b", reviewed_b)

            weekly_report_b = next(
                document
                for document in reviewed_b.deliverables
                if document.deliverable_type == "weekly_report"
            )
            briefing_b = next(
                document
                for document in reviewed_b.deliverables
                if document.deliverable_type == "next_meeting_briefing"
            )

            assert reviewed_a.orchestration.memory_usage is not None
            assert reviewed_a.orchestration.memory_usage.prior_meeting_count == 0
            assert reviewed_b.orchestration.memory_usage is not None
            assert reviewed_b.orchestration.memory_usage.prior_meeting_count >= 1
            assert reviewed_b.briefing.carryover_tasks
            assert reviewed_b.explanations.briefing_items
            assert any(
                item.origin_layer == "history_memory"
                for item in reviewed_b.explanations.briefing_items
            )
            assert "## Carryover From Earlier Meetings" in weekly_report_b.content_markdown
            assert "No unfinished work is being carried over." not in weekly_report_b.content_markdown
            assert "## Carryover From Earlier Meetings" in briefing_b.content_markdown
            assert "No carryover items were detected." not in briefing_b.content_markdown

        asyncio.run(run_flow())
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
