from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.action_item import ActionItem
from backend.schemas.claim import ClaimVerificationResult
from backend.schemas.meeting import (
    MeetingImportRequest,
    MeetingImportResponse,
    MeetingProcessResponse,
    MeetingRecord,
    ParsedTranscript,
)
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectRecord,
)
from backend.schemas.reading_recommendation import ReadingRecommendationBatch
from backend.schemas.research_idea import AdvisorIdeaCaptureResult, ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot
from backend.services.briefing_service import BriefingResult, BriefingService
from backend.services.claim_extraction_service import ClaimExtractionError, ClaimExtractionService
from backend.services.claim_verification_service import ClaimVerificationService
from backend.services.deliverable_service import DeliverableDocument, DeliverableService
from backend.services.evidence_retrieval_service import EvidenceRetrievalService
from backend.services.idea_capture_service import IdeaCaptureError, IdeaCaptureService
from backend.services.progress_extraction_service import (
    ProgressExtractionError,
    ProgressExtractionService,
)
from backend.services.project_memory_service import ProjectMemoryService
from backend.services.reading_recommendation_service import (
    ReadingRecommendationError,
    ReadingRecommendationService,
)
from backend.services.research_plan_service import (
    ResearchPlanError,
    ResearchPlanResult,
    ResearchPlanService,
)
from backend.services.transcription_service import (
    TranscriptionService,
    TranscriptionServiceError,
)

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def get_transcription_service() -> TranscriptionService:
    return TranscriptionService()


def get_progress_extraction_service() -> ProgressExtractionService:
    return ProgressExtractionService()


def get_idea_capture_service() -> IdeaCaptureService:
    return IdeaCaptureService()


def get_research_plan_service() -> ResearchPlanService:
    return ResearchPlanService()


def get_reading_recommendation_service() -> ReadingRecommendationService:
    return ReadingRecommendationService()


def get_claim_extraction_service() -> ClaimExtractionService:
    return ClaimExtractionService()


def get_claim_verification_service() -> ClaimVerificationService:
    return ClaimVerificationService(retrieval_service=EvidenceRetrievalService())


def get_project_memory_service() -> ProjectMemoryService:
    return ProjectMemoryService()


def get_briefing_service() -> BriefingService:
    return BriefingService()


def get_deliverable_service() -> DeliverableService:
    return DeliverableService()


class MeetingReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = "evidenceflow-demo-project"
    project_name: str = "EvidenceFlow Demo Project"
    project_description: str = "Single-workspace research cockpit for weekly meetings."
    project_domain: str = "research-automation"
    verify_claims: bool = True
    max_claims_to_verify: int = 1


class MeetingReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project: ProjectRecord
    meeting: MeetingRecord
    transcript: ParsedTranscript
    progress: MeetingProgressSnapshot
    ideas: AdvisorIdeaCaptureResult
    research_plan: ResearchPlanResult
    reading_recommendations: ReadingRecommendationBatch
    claims: list[ClaimVerificationResult] = Field(default_factory=list)
    briefing: BriefingResult
    deliverables: list[DeliverableDocument] = Field(default_factory=list)


@router.post("/import", response_model=MeetingImportResponse, status_code=status.HTTP_201_CREATED)
async def import_meeting(
    request: MeetingImportRequest,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
) -> MeetingImportResponse:
    try:
        return transcription_service.import_meeting(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TranscriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{meeting_id}/review", response_model=MeetingReviewResponse)
async def review_meeting(
    meeting_id: str,
    request: MeetingReviewRequest,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    progress_service: Annotated[ProgressExtractionService, Depends(get_progress_extraction_service)],
    idea_capture_service: Annotated[IdeaCaptureService, Depends(get_idea_capture_service)],
    research_plan_service: Annotated[ResearchPlanService, Depends(get_research_plan_service)],
    reading_service: Annotated[ReadingRecommendationService, Depends(get_reading_recommendation_service)],
    claim_extraction_service: Annotated[ClaimExtractionService, Depends(get_claim_extraction_service)],
    claim_verification_service: Annotated[ClaimVerificationService, Depends(get_claim_verification_service)],
    project_memory_service: Annotated[ProjectMemoryService, Depends(get_project_memory_service)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
    deliverable_service: Annotated[DeliverableService, Depends(get_deliverable_service)],
) -> MeetingReviewResponse:
    try:
        transcript = transcription_service.load_transcript(meeting_id)
        progress = progress_service.extract_progress(transcript, meeting_id=meeting_id)
        meeting = transcription_service.save_progress_snapshot(meeting_id, progress)
        ideas = idea_capture_service.capture_ideas(transcript, meeting_id=meeting_id)
        research_plan = research_plan_service.generate_plan(
            transcript,
            ideas.ideas,
            progress=progress,
            meeting_id=meeting_id,
        )
        reading_batch = reading_service.generate_recommendations(
            transcript,
            ideas.ideas,
            progress=progress,
            meeting_id=meeting_id,
        )
        verified_claims = _verify_claims(
            transcript=transcript,
            meeting_id=meeting_id,
            verify_claims=request.verify_claims,
            max_claims_to_verify=request.max_claims_to_verify,
            claim_extraction_service=claim_extraction_service,
            claim_verification_service=claim_verification_service,
        )

        project = ProjectRecord(
            project_id=request.project_id,
            name=request.project_name,
            description=request.project_description,
            domain=request.project_domain,
        )
        memory_snapshot = project_memory_service.remember_meeting(
            project,
            _build_project_meeting_record(meeting, request.project_id, progress.summary),
            decisions=_build_decisions(meeting_id, ideas.ideas),
            action_items=_build_action_items(progress, research_plan),
            claims=[claim_result.claim for claim_result in verified_claims],
            advisor_ideas=ideas.ideas,
            student_progress=progress.student_progress,
            key_papers=_build_key_papers(request.project_id, meeting_id, ideas, reading_batch),
            transcript=transcript,
        )
        briefing = briefing_service.generate_briefing(memory_snapshot)
        deliverables = deliverable_service.generate_all(
            project_memory=memory_snapshot,
            briefing=briefing,
        ).documents
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        ProgressExtractionError,
        IdeaCaptureError,
        ResearchPlanError,
        ReadingRecommendationError,
        ClaimExtractionError,
        TranscriptionServiceError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return MeetingReviewResponse(
        project=project,
        meeting=meeting,
        transcript=transcript,
        progress=progress,
        ideas=ideas,
        research_plan=research_plan,
        reading_recommendations=reading_batch,
        claims=verified_claims,
        briefing=briefing,
        deliverables=deliverables,
    )


def _verify_claims(
    *,
    transcript: ParsedTranscript,
    meeting_id: str,
    verify_claims: bool,
    max_claims_to_verify: int,
    claim_extraction_service: ClaimExtractionService,
    claim_verification_service: ClaimVerificationService,
) -> list[ClaimVerificationResult]:
    extracted = claim_extraction_service.extract_claims(transcript, meeting_id=meeting_id)
    if not verify_claims or max_claims_to_verify <= 0:
        return []

    verified_claims: list[ClaimVerificationResult] = []
    for claim in extracted.claims[:max_claims_to_verify]:
        verified_claims.append(claim_verification_service.verify_claim(claim))
    return verified_claims


def _build_project_meeting_record(
    meeting: MeetingRecord,
    project_id: str,
    summary: str,
) -> ProjectMeetingRecord:
    return ProjectMeetingRecord(
        meeting_id=meeting.meeting_id,
        project_id=project_id,
        title=meeting.meeting_title or "Imported meeting",
        summary=summary,
        created_at=meeting.created_at,
    )


def _build_decisions(
    meeting_id: str,
    ideas: list[ResearchIdea],
) -> list[ProjectDecision]:
    decisions: list[ProjectDecision] = []
    for index, idea in enumerate(ideas, start=1):
        decisions.append(
            ProjectDecision(
                id=f"{meeting_id}-decision-{index:02d}",
                meeting_id=meeting_id,
                title=idea.idea_text,
                rationale=idea.expected_validation,
                decided_by=idea.suggested_by,
            )
        )
    return decisions


def _build_action_items(
    progress: MeetingProgressSnapshot,
    research_plan: ResearchPlanResult,
) -> list[ActionItem]:
    action_items: list[ActionItem] = list(progress.action_items)
    seen_keys = {
        f"{item.title.lower()}::{(item.owner or 'unknown').lower()}"
        for item in action_items
    }
    for task in research_plan.tasks:
        dedupe_key = f"{task.title.lower()}::{task.owner.lower()}"
        if dedupe_key in seen_keys:
            continue
        action_items.append(
            ActionItem(
                meeting_id=task.meeting_id,
                student_name=task.student_name,
                title=task.title,
                owner=task.owner,
                deadline=task.due_date,
                priority=task.priority,
                status="open",
                dependency_note=task.dependency_note,
            )
        )
        seen_keys.add(dedupe_key)
    return action_items


def _build_key_papers(
    project_id: str,
    meeting_id: str,
    ideas: AdvisorIdeaCaptureResult,
    reading_batch: ReadingRecommendationBatch,
) -> list[KeyPaperMemory]:
    papers: list[KeyPaperMemory] = []
    seen_titles: set[str] = set()

    for idea in ideas.ideas:
        for reading in idea.recommended_reading:
            if reading.title in seen_titles:
                continue
            papers.append(
                KeyPaperMemory(
                    id=reading.id or f"{meeting_id}-paper-{len(papers) + 1:02d}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    title=reading.title,
                    source_url=reading.source_url,
                    reason=reading.reason,
                )
            )
            seen_titles.add(reading.title)

    for reading in reading_batch.recommendations:
        if reading.title in seen_titles:
            continue
        papers.append(
            KeyPaperMemory(
                id=reading.id or f"{meeting_id}-paper-{len(papers) + 1:02d}",
                project_id=project_id,
                meeting_id=meeting_id,
                title=reading.title,
                source_url=reading.source_url,
                reason=reading.reason,
            )
        )
        seen_titles.add(reading.title)
    return papers


@router.post("/{meeting_id}/process", response_model=MeetingProcessResponse)
async def process_meeting(
    meeting_id: str,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    progress_service: Annotated[ProgressExtractionService, Depends(get_progress_extraction_service)],
) -> MeetingProcessResponse:
    try:
        transcript = transcription_service.load_transcript(meeting_id)
        progress = progress_service.extract_progress(transcript, meeting_id=meeting_id)
        meeting = transcription_service.save_progress_snapshot(meeting_id, progress)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProgressExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TranscriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return MeetingProcessResponse(meeting=meeting, transcript=transcript, progress=progress)


@router.get("/{meeting_id}/progress", response_model=MeetingProgressSnapshot)
async def get_meeting_progress(
    meeting_id: str,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
) -> MeetingProgressSnapshot:
    try:
        return transcription_service.load_progress_snapshot(meeting_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
