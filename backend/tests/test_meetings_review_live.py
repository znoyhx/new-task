from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path
from uuid import uuid4

import pytest

from backend.api.meetings import MeetingReviewRequest, import_meeting, review_meeting
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
