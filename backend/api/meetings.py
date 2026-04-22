from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from backend.agents.orchestrator_agent import ReviewOrchestrator
from backend.config import get_settings
from backend.schemas.action_item import ActionItem
from backend.schemas.claim import ClaimVerificationResult
from backend.schemas.meeting import (
    MeetingImportRequest,
    MeetingImportResponse,
    MeetingProcessResponse,
    MeetingRecord,
    ParsedTranscript,
)
from backend.schemas.orchestration import (
    ActionItemInsight,
    AgentInputSource,
    AgentOutputTarget,
    ArtifactAttribution,
    BriefingItemInsight,
    ClaimInsight,
    ReadingInsight,
    ReviewExplanationBundle,
    ReviewOrchestrationSummary,
)
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectMemorySnapshot,
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
from backend.services.response_language import ResponseLanguage, is_chinese, localize_text
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


class ReviewPipelineError(RuntimeError):
    def __init__(
        self,
        *,
        stage_key: str,
        agent_name: str,
        message: str,
        fallback: str,
    ) -> None:
        super().__init__(message)
        self.stage_key = stage_key
        self.agent_name = agent_name
        self.message = message
        self.fallback = fallback


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
    response_language: ResponseLanguage = "en"


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
    orchestration: ReviewOrchestrationSummary
    explanations: ReviewExplanationBundle


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


@router.post("/import-audio", response_model=MeetingImportResponse, status_code=status.HTTP_201_CREATED)
async def import_audio_meeting(
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    file: Annotated[UploadFile, File(...)],
    meeting_title: Annotated[str | None, Form()] = None,
    language_hint: Annotated[str | None, Form()] = None,
) -> MeetingImportResponse:
    try:
        file_bytes = await file.read()
        return transcription_service.import_uploaded_audio(
            file_bytes=file_bytes,
            filename=file.filename or "",
            content_type=file.content_type,
            meeting_title=meeting_title,
            language_hint=language_hint,
        )
    except TranscriptionServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()


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
    settings = get_settings()
    response_language = request.response_language
    zh = is_chinese(response_language)
    orchestrator = ReviewOrchestrator(
        settings=settings,
        project_id=request.project_id,
        response_language=response_language,
    )
    try:
        transcript = transcription_service.load_transcript(meeting_id)
        meeting = transcription_service.load_meeting(meeting_id)
        orchestrator.record_stage(
            stage_key="controller-intake",
            stage_label="主控接入" if zh else "Controller intake",
            capability="review_orchestration",
            agent_key="controller",
            goal=(
                "确认当前导入材料已经可以进入“转成下周执行”的主链路。"
                if zh
                else "Confirm that the imported meeting is ready to be turned into next-week execution."
            ),
            input_sources=_build_intake_sources(
                meeting,
                transcript,
                output_language=response_language,
            ),
            output_target=AgentOutputTarget(
                kind="review_pipeline",
                label="可执行的组会 review 流程" if zh else "Ready-to-run meeting review pipeline",
                detail=(
                    "主控 Agent 已拿到当前 transcript 和源数据元信息。"
                    if zh
                    else "The controller has the current meeting transcript and source metadata."
                ),
            ),
            output_summary=(
                (
                    f"已从 {meeting.source_type} 类型的导入中加载 {transcript.chunk_count} 个 transcript chunk。"
                    if zh
                    else f"Loaded {transcript.chunk_count} transcript chunk(s) from a {meeting.source_type} meeting import."
                )
            ),
        )

        prior_memory = project_memory_service.load_project_memory(
            request.project_id,
            query=_build_memory_query(transcript),
        )
        memory_usage = orchestrator.summarize_memory(prior_memory, current_meeting_id=meeting_id)
        memory_fallback_used = prior_memory.project is None and not prior_memory.meetings
        orchestrator.record_stage(
            stage_key="memory-load",
            stage_label="记忆加载" if zh else "Memory load",
            capability="project_memory_lookup",
            agent_key="memory_steward",
            goal=(
                "在决定哪些事项要推进到下周之前，先加载可复用的项目长期记忆。"
                if zh
                else "Load reusable project memory before deciding what has to move into next week."
            ),
            input_sources=[
                AgentInputSource(
                    kind="project_id",
                    label=request.project_id,
                    detail=(
                        f"项目名称：{request.project_name}"
                        if zh
                        else f"Project name: {request.project_name}"
                    ),
                ),
                AgentInputSource(
                    kind="memory_query",
                    label="从 transcript 派生的检索 query" if zh else "Transcript-derived lookup query",
                    detail=_build_memory_query(transcript),
                ),
            ],
            output_target=AgentOutputTarget(
                kind="memory_snapshot",
                label="历史项目记忆快照" if zh else "Historical project memory snapshot",
                detail=(
                    "包含更早组会、未完成任务、历史决策，以及相关的本地 memory 命中。"
                    if zh
                    else "Carries earlier meetings, open tasks, decisions, and relevant local memory hits."
                ),
            ),
            output_summary=_describe_memory_usage(memory_usage, output_language=response_language),
            fallback_used=memory_fallback_used,
            fallback_detail=(
                "没有历史 memory，因此当前 review 以首次组会模式继续。"
                if zh
                else "No prior memory existed, so the review continues in first-meeting mode."
                if memory_fallback_used
                else ""
            ),
        )

        try:
            progress = progress_service.extract_progress(
                transcript,
                meeting_id=meeting_id,
                output_language=response_language,
            )
            meeting = transcription_service.save_progress_snapshot(meeting_id, progress)
        except (ProgressExtractionError, TranscriptionServiceError, ValueError) as exc:
            raise ReviewPipelineError(
                stage_key="progress-extraction",
                agent_name="推进 Agent",
                message=str(exc),
                fallback=(
                    "停止当前运行并保留 transcript 可审阅状态，因为 progress extraction 是后续规划的前置条件。"
                    if zh
                    else "Stop the run and keep the transcript reviewable, because progress extraction is required before planning."
                ),
            ) from exc

        orchestrator.record_stage(
            stage_key="progress-extraction",
            stage_label="进展提取" if zh else "Progress extraction",
            capability="weekly_progress_extraction",
            agent_key="execution_driver",
            goal=(
                "把组会内容转成结构化 progress、blocker、risk 和可跟进事项。"
                if zh
                else "Turn the meeting into structured progress, blockers, risks, and follow-up tasks."
            ),
            input_sources=[
                AgentInputSource(
                    kind="parsed_transcript",
                    label="已解析 transcript" if zh else "Parsed transcript",
                    detail=(
                        f"{transcript.chunk_count} 个标准化 transcript chunk。"
                        if zh
                        else f"{transcript.chunk_count} normalized transcript chunk(s)."
                    ),
                )
            ],
            output_target=AgentOutputTarget(
                kind="progress_snapshot",
                label="结构化周进展快照" if zh else "Structured weekly progress snapshot",
                detail=(
                    "包含学生进展、blocker、risk、未解决问题，以及直接任务候选。"
                    if zh
                    else "Student progress, blockers, risks, unresolved questions, and direct task candidates."
                ),
            ),
            output_summary=(
                (
                    f"已结构化 {len(progress.student_progress)} 条学生进展，以及 {len(progress.action_items)} 个直接 follow-up action item。"
                    if zh
                    else f"Structured {len(progress.student_progress)} student progress snapshot(s) and "
                    f"{len(progress.action_items)} direct follow-up action item(s)."
                )
            ),
        )

        try:
            ideas = idea_capture_service.capture_ideas(
                transcript,
                meeting_id=meeting_id,
                output_language=response_language,
            )
        except IdeaCaptureError as exc:
            raise ReviewPipelineError(
                stage_key="idea-capture",
                agent_name="推进 Agent",
                message=str(exc),
                fallback=(
                    "停止当前运行并展示 transcript，因为没有 advisor ideas 就无法把执行计划真正落地。"
                    if zh
                    else "Stop the run and surface the transcript, because next-week execution cannot be grounded without advisor ideas."
                ),
            ) from exc

        orchestrator.record_stage(
            stage_key="idea-capture",
            stage_label="导师思路捕获" if zh else "Idea capture",
            capability="advisor_idea_capture",
            agent_key="execution_driver",
            goal=(
                "捕获应该真正转成下周研究动作的导师指导意见。"
                if zh
                else "Capture advisor guidance that should become next week's concrete research moves."
            ),
            input_sources=[
                AgentInputSource(
                    kind="parsed_transcript",
                    label="当前组会 transcript" if zh else "Current meeting transcript",
                    detail=(
                        "来自当前组会的导师和学生发言。"
                        if zh
                        else "Advisor and student turns from the current meeting."
                    ),
                )
            ],
            output_target=AgentOutputTarget(
                kind="advisor_ideas",
                label="带验证意图的导师 ideas" if zh else "Advisor ideas with validation intent",
                detail=(
                    "结构化 ideas、next-actions、validation metrics，以及与 idea 关联的阅读。"
                    if zh
                    else "Structured ideas, next-actions, validation metrics, and idea-linked readings."
                ),
            ),
            output_summary=(
                f"已为下一轮执行周期捕获 {len(ideas.ideas)} 条 advisor idea。"
                if zh
                else f"Captured {len(ideas.ideas)} advisor idea(s) for the next execution cycle."
            ),
        )

        research_plan, plan_fallback_used, plan_fallback_detail = _generate_research_plan(
            transcript=transcript,
            ideas=ideas.ideas,
            progress=progress,
            meeting_id=meeting_id,
            research_plan_service=research_plan_service,
            output_language=response_language,
        )
        orchestrator.record_stage(
            stage_key="plan-generation",
            stage_label="计划生成" if zh else "Plan generation",
            capability="next_week_plan_generation",
            agent_key="execution_driver",
            goal=(
                "生成真正把这次组会推进到下周执行的 action items。"
                if zh
                else "Produce next-week action items that move the meeting toward concrete research execution."
            ),
            input_sources=[
                AgentInputSource(
                    kind="advisor_ideas",
                    label="导师 ideas" if zh else "Advisor ideas",
                    detail=(
                        f"{len(ideas.ideas)} 条已捕获 idea，包含 validation metrics。"
                        if zh
                        else f"{len(ideas.ideas)} captured idea(s) with validation metrics."
                    ),
                ),
                AgentInputSource(
                    kind="student_progress",
                    label="当前 blockers" if zh else "Current blockers",
                    detail=(
                        f"来自当前 transcript 的 {len(progress.student_progress)} 条 progress snapshot。"
                        if zh
                        else f"{len(progress.student_progress)} progress snapshot(s) from the current transcript."
                    ),
                ),
                AgentInputSource(
                    kind="project_memory",
                    label="正在使用的历史 memory" if zh else "Historical memory in use",
                    detail=_describe_memory_usage(memory_usage, output_language=response_language),
                ),
            ],
            output_target=AgentOutputTarget(
                kind="research_plan",
                label="下周研究计划" if zh else "Next-week research plan",
                detail=(
                    "包含 owner、due date、success metric 和 rationale 的 action items。"
                    if zh
                    else "Action items with owners, due dates, success metrics, and rationale."
                ),
            ),
            output_summary=(
                (
                    f"已准备 {len(research_plan.tasks)} 个计划任务，以及 {len(research_plan.questions_to_answer)} 个下周需要关闭的问题。"
                    if zh
                    else f"Prepared {len(research_plan.tasks)} plan task(s) and "
                    f"{len(research_plan.questions_to_answer)} question(s) to close next week."
                )
            ),
            fallback_used=plan_fallback_used,
            fallback_detail=plan_fallback_detail,
        )

        reading_batch, reading_fallback_used, reading_fallback_detail = _generate_reading_batch(
            transcript=transcript,
            ideas=ideas.ideas,
            progress=progress,
            meeting_id=meeting_id,
            reading_service=reading_service,
            output_language=response_language,
        )
        orchestrator.record_stage(
            stage_key="reading-recommendation",
            stage_label="推荐阅读生成" if zh else "Reading recommendation",
            capability="reading_recommendation_generation",
            agent_key="reading_specialist",
            goal=(
                "推荐能以最小集合解除下周执行阻塞的阅读材料。"
                if zh
                else "Recommend the smallest reading set that can unblock next week's execution."
            ),
            input_sources=[
                AgentInputSource(
                    kind="advisor_ideas",
                    label="导师 ideas" if zh else "Advisor ideas",
                    detail=(
                        f"{len(ideas.ideas)} 条与下周执行相关的 idea。"
                        if zh
                        else f"{len(ideas.ideas)} idea(s) linked to next-week work."
                    ),
                ),
                AgentInputSource(
                    kind="student_progress",
                    label="当前 blockers" if zh else "Current blockers",
                    detail=(
                        f"当前组会共识别到 {sum(len(student.blockers) for student in progress.student_progress)} 个 blocker。"
                        if zh
                        else f"{sum(len(student.blockers) for student in progress.student_progress)} blocker(s) across the current meeting."
                    ),
                ),
                AgentInputSource(
                    kind="project_memory",
                    label="正在使用的历史 memory" if zh else "Historical memory in use",
                    detail=_describe_memory_usage(memory_usage, output_language=response_language),
                ),
            ],
            output_target=AgentOutputTarget(
                kind="reading_recommendations",
                label="优先级阅读列表" if zh else "Prioritized reading list",
                detail=(
                    "与 ideas 或 blockers 关联、面向执行的短阅读列表。"
                    if zh
                    else "Short, execution-oriented readings linked to ideas or blockers."
                ),
            ),
            output_summary=(
                f"已准备 {len(reading_batch.recommendations)} 条推荐阅读。"
                if zh
                else f"Prepared {len(reading_batch.recommendations)} reading recommendation(s)."
            ),
            fallback_used=reading_fallback_used,
            fallback_detail=reading_fallback_detail,
        )

        verified_claims, claim_stage = _verify_claims(
            transcript=transcript,
            meeting_id=meeting_id,
            verify_claims=request.verify_claims,
            max_claims_to_verify=request.max_claims_to_verify,
            claim_extraction_service=claim_extraction_service,
            claim_verification_service=claim_verification_service,
            output_language=response_language,
        )
        orchestrator.record_stage(
            stage_key="evidence-verification",
            stage_label="证据核验" if zh else "Evidence verification",
            capability="claim_extraction_and_verification",
            agent_key="evidence_hunter",
            goal=(
                "只对那些会影响下周执行或导师判断的关键 claim 触发证据核验。"
                if zh
                else "Verify only the claims that matter for next-week research execution or advisor scrutiny."
            ),
            input_sources=[
                AgentInputSource(
                    kind="parsed_transcript",
                    label="当前 transcript" if zh else "Current transcript",
                    detail=(
                        f"{transcript.chunk_count} 个标准化 chunk。"
                        if zh
                        else f"{transcript.chunk_count} normalized chunk(s)."
                    ),
                ),
                AgentInputSource(
                    kind="verification_policy",
                    label="核验策略" if zh else "Verification policy",
                    detail=(
                        "当前 review 已显式开启核验。"
                        if zh and request.verify_claims
                        else "当前 review 未开启核验。"
                        if zh
                        else "Explicitly enabled for this review."
                        if request.verify_claims
                        else "Disabled for this review."
                    ),
                ),
            ],
            output_target=AgentOutputTarget(
                kind="claim_verifications",
                label="需要证据敏感判断的 claims" if zh else "Evidence-sensitive claims",
                detail=(
                    "包含 claim verdict、evidence cards，以及剩余 gap。"
                    if zh
                    else "Claim verdicts, evidence cards, and remaining gaps when applicable."
                ),
            ),
            output_summary=claim_stage["output_summary"],
            trigger_reason=claim_stage["trigger_reason"],
            triggered=claim_stage["triggered"],
            status=claim_stage["status"],
            fallback_used=claim_stage["fallback_used"],
            fallback_detail=claim_stage["fallback_detail"],
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
        orchestrator.record_stage(
            stage_key="memory-write",
            stage_label="记忆写回" if zh else "Memory writeback",
            capability="project_memory_persistence",
            agent_key="memory_steward",
            goal=(
                "把本次组会持久化，让下一次 review 能继承未完成事项和项目长期记忆。"
                if zh
                else "Persist this meeting so the next review can inherit unfinished work and project memory."
            ),
            input_sources=[
                AgentInputSource(
                    kind="current_meeting_outputs",
                    label="当前组会产物" if zh else "Current meeting outputs",
                    detail=(
                        (
                            f"{len(progress.student_progress)} 条 progress snapshot、{len(research_plan.tasks)} 个计划任务、"
                            f"{len(verified_claims)} 个 claim verdict，以及 {len(reading_batch.recommendations)} 条阅读建议。"
                        )
                        if zh
                        else f"{len(progress.student_progress)} progress snapshot(s), {len(research_plan.tasks)} plan task(s), "
                        f"{len(verified_claims)} claim verdict(s), and {len(reading_batch.recommendations)} reading suggestion(s)."
                    ),
                )
            ],
            output_target=AgentOutputTarget(
                kind="project_memory",
                label="更新后的本地项目记忆" if zh else "Updated local project memory",
                detail=(
                    "组会记忆已写入本地 SQLite 和本地向量存储。"
                    if zh
                    else "Meeting memory is written to local SQLite and local vector storage."
                ),
            ),
            output_summary=(
                (
                    f"已持久化 meeting {meeting_id}，并刷新项目 memory snapshot；当前共跟踪 {len(memory_snapshot.action_items)} 个 action item。"
                    if zh
                    else f"Persisted meeting {meeting_id} and refreshed the project memory snapshot with "
                    f"{len(memory_snapshot.action_items)} tracked action item(s)."
                )
            ),
        )
        briefing = briefing_service.generate_briefing(
            memory_snapshot,
            output_language=response_language,
        )
        deliverables = deliverable_service.generate_all(
            project_memory=memory_snapshot,
            briefing=briefing,
            output_language=response_language,
        ).documents
        orchestrator.record_stage(
            stage_key="briefing-deliverables",
            stage_label="Briefing 与交付物" if zh else "Briefing and deliverables",
            capability="briefing_and_markdown_delivery",
            agent_key="execution_driver",
            goal=(
                "把组会结果滚入 briefing，并产出可导出的 Markdown deliverables。"
                if zh
                else "Roll the meeting into briefing-ready follow-up and exportable Markdown deliverables."
            ),
            input_sources=[
                AgentInputSource(
                    kind="project_memory",
                    label="更新后的项目 memory" if zh else "Updated project memory",
                    detail=(
                        "包含刚写入的组会，以及历史 carryover tasks。"
                        if zh
                        else "The persisted meeting plus historical carryover tasks."
                    ),
                ),
                AgentInputSource(
                    kind="research_plan",
                    label="下周计划" if zh else "Next-week plan",
                    detail=(
                        f"{len(research_plan.tasks)} 个可直接导出的任务。"
                        if zh
                        else f"{len(research_plan.tasks)} task(s) ready for export."
                    ),
                ),
            ],
            output_target=AgentOutputTarget(
                kind="deliverables",
                label="Briefing 与 Markdown 交付物" if zh else "Briefing and Markdown artifacts",
                detail=(
                    "包括周报、下次组会 briefing、下周计划和汇报提纲。"
                    if zh
                    else "Weekly report, next-meeting briefing, next-week plan, and presentation outline."
                ),
            ),
            output_summary=(
                (
                    f"已生成 briefing summary，以及 {len(deliverables)} 份可导出的 Markdown deliverable。"
                    if zh
                    else f"Generated briefing summary plus {len(deliverables)} exportable Markdown deliverable(s)."
                )
            ),
        )
        explanations = _build_review_explanations(
            prior_memory=prior_memory,
            transcript=transcript,
            progress=progress,
            ideas=ideas,
            research_plan=research_plan,
            reading_batch=reading_batch,
            verified_claims=verified_claims,
            briefing=briefing,
            output_language=response_language,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewPipelineError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": exc.message,
                "stage": exc.stage_key,
                "agent": exc.agent_name,
                "fallback": exc.fallback,
            },
        ) from exc
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
        orchestration=orchestrator.to_summary(),
        explanations=explanations,
    )


def _verify_claims(
    *,
    transcript: ParsedTranscript,
    meeting_id: str,
    verify_claims: bool,
    max_claims_to_verify: int,
    claim_extraction_service: ClaimExtractionService,
    claim_verification_service: ClaimVerificationService,
    output_language: ResponseLanguage,
) -> tuple[list[ClaimVerificationResult], dict[str, object]]:
    if not verify_claims or max_claims_to_verify <= 0:
        return [], {
            "status": "skipped",
            "triggered": False,
            "trigger_reason": localize_text(
                output_language,
                zh="当前 review 未开启 claim verification。",
                en="Claim verification was disabled for this review.",
            ),
            "fallback_used": False,
            "fallback_detail": "",
            "output_summary": localize_text(
                output_language,
                zh="本次运行跳过了可选的证据核验分支。",
                en="The optional evidence lane was skipped for this run.",
            ),
        }

    try:
        extracted = claim_extraction_service.extract_claims(
            transcript,
            meeting_id=meeting_id,
            output_language=output_language,
        )
    except ClaimExtractionError as exc:
        return [], {
            "status": "skipped",
            "triggered": False,
            "trigger_reason": localize_text(
                output_language,
                zh="可选的证据阶段在 claim extraction 处失败。",
                en="Claim extraction failed in the optional evidence stage.",
            ),
            "fallback_used": True,
            "fallback_detail": localize_text(
                output_language,
                zh=f"Claim extraction 失败：{exc}。当前 review 会把证据分支保持为可选，而不是阻断主计划。",
                en=f"Claim extraction failed: {exc}. The review keeps the evidence lane optional instead of blocking the main plan.",
            ),
            "output_summary": localize_text(
                output_language,
                zh="当前没有可靠的 claim 候选，因此证据核验保持为可选分支。",
                en="No reliable claim candidates were available, so evidence verification stayed optional.",
            ),
        }

    if not extracted.claims:
        return [], {
            "status": "skipped",
            "triggered": False,
            "trigger_reason": localize_text(
                output_language,
                zh="当前 transcript 中没有达到证据核验阈值的高价值 claim。",
                en="No high-value claim met the evidence threshold in this transcript.",
            ),
            "fallback_used": False,
            "fallback_detail": "",
            "output_summary": localize_text(
                output_language,
                zh="当前 transcript 中没有足够强的 claim 来触发证据检索。",
                en="The transcript did not contain a claim strong enough to justify evidence retrieval.",
            ),
        }

    verified_claims: list[ClaimVerificationResult] = []
    fallback_notes: list[str] = []
    for claim in extracted.claims[:max_claims_to_verify]:
        try:
            verified_claims.append(
                claim_verification_service.verify_claim(
                    claim,
                    output_language=output_language,
                )
            )
        except Exception as exc:  # pragma: no cover - protects optional evidence stage
            fallback_notes.append(
                localize_text(
                    output_language,
                    zh=f"'{claim.text}' 的核验失败，已降级为 needs_verification。",
                    en=f"Verification for '{claim.text}' failed and was downgraded to needs_verification.",
                )
            )
            verified_claims.append(
                ClaimVerificationResult(
                    claim=claim.model_copy(update={"verification_status": "needs_verification"}),
                    verdict="needs_verification",
                    confidence="low",
                    summary=localize_text(
                        output_language,
                        zh="核验失败，因此这条 claim 会继续以未解决状态保留。",
                        en="Verification failed, so the claim stays visible as unresolved.",
                    ),
                    evidence_cards=[],
                    gaps=[str(exc)],
                )
            )
    return verified_claims, {
        "status": "completed",
        "triggered": True,
        "trigger_reason": localize_text(
            output_language,
            zh="当前已开启 claim verification，且 transcript 产出了高价值 claim。",
            en="Claim verification was enabled and the transcript produced a high-value claim.",
        ),
        "fallback_used": bool(fallback_notes),
        "fallback_detail": " ".join(fallback_notes),
        "output_summary": (
            localize_text(
                output_language,
                zh=f"已核验 {len(extracted.claims)} 个 claim 候选中的 {len(verified_claims)} 个。",
                en=f"Reviewed {len(verified_claims)} claim(s) out of {len(extracted.claims)} extracted candidate(s).",
            )
        ),
    }


def _build_intake_sources(
    meeting: MeetingRecord,
    transcript: ParsedTranscript,
    *,
    output_language: ResponseLanguage,
) -> list[AgentInputSource]:
    sources = [
        AgentInputSource(
            kind="meeting_record",
            label=meeting.meeting_title or ("导入会议" if is_chinese(output_language) else "Imported meeting"),
            detail=localize_text(
                output_language,
                zh=f"Meeting ID：{meeting.meeting_id}",
                en=f"Meeting id: {meeting.meeting_id}",
            ),
        ),
        AgentInputSource(
            kind="parsed_transcript",
            label="已解析 transcript" if is_chinese(output_language) else "Parsed transcript",
            detail=localize_text(
                output_language,
                zh=f"{transcript.chunk_count} 个标准化 chunk，已可供后续能力复用。",
                en=f"{transcript.chunk_count} normalized chunk(s) ready for downstream extraction.",
            ),
        ),
    ]
    if meeting.source_type == "audio":
        sources.append(
            AgentInputSource(
                kind="audio_metadata",
                label=meeting.audio_filename or ("已上传音频" if is_chinese(output_language) else "Uploaded audio"),
                detail=localize_text(
                    output_language,
                    zh=(
                        f"本地转写后端：{meeting.transcription_backend or 'unknown'} / "
                        f"状态：{meeting.transcription_status}"
                    ),
                    en=(
                        f"Local transcription backend: {meeting.transcription_backend or 'unknown'} / "
                        f"status: {meeting.transcription_status}"
                    ),
                ),
            )
        )
    return sources


def _build_memory_query(transcript: ParsedTranscript) -> str:
    if not transcript.chunks:
        return transcript.normalized_text[:240]

    query_parts: list[str] = []
    for chunk in transcript.chunks[:4]:
        query_parts.append(chunk.text.strip())
    return " ".join(part for part in query_parts if part)[:320]


def _describe_memory_usage(memory_usage, *, output_language: ResponseLanguage) -> str:
    if memory_usage.prior_meeting_count <= 0:
        return localize_text(
            output_language,
            zh="当前项目没有加载到更早的组会记忆。",
            en="No earlier meeting memory was loaded for this project.",
        )
    return localize_text(
        output_language,
        zh=(
            f"已加载 {memory_usage.prior_meeting_count} 次历史组会、"
            f"{memory_usage.open_task_count} 个未关闭 carryover task，"
            f"以及 {memory_usage.recent_decision_count} 条历史决策。"
        ),
        en=(
            f"Loaded {memory_usage.prior_meeting_count} prior meeting(s), "
            f"{memory_usage.open_task_count} open carryover task(s), "
            f"and {memory_usage.recent_decision_count} historical decision(s)."
        ),
    )


def _generate_research_plan(
    *,
    transcript: ParsedTranscript,
    ideas: list[ResearchIdea],
    progress: MeetingProgressSnapshot,
    meeting_id: str,
    research_plan_service: ResearchPlanService,
) -> tuple[ResearchPlanResult, bool, str]:
    try:
        return (
            research_plan_service.generate_plan(
                transcript,
                ideas,
                progress=progress,
                meeting_id=meeting_id,
            ),
            False,
            "",
        )
    except ResearchPlanError as exc:
        fallback = _build_research_plan_from_ideas(
            meeting_id=meeting_id,
            ideas=ideas,
            progress=progress,
        )
        if fallback.tasks:
            return (
                fallback,
                True,
                f"Deep plan generation failed: {exc}. Fell back to advisor idea next-actions already captured from the meeting.",
            )
        raise ReviewPipelineError(
            stage_key="plan-generation",
            agent_name="推进 Agent",
            message=str(exc),
            fallback="Use advisor idea next-actions if they are already structured. No usable fallback was available here.",
        ) from exc


def _build_research_plan_from_ideas(
    *,
    meeting_id: str,
    ideas: list[ResearchIdea],
    progress: MeetingProgressSnapshot,
) -> ResearchPlanResult:
    tasks = []
    for idea in ideas:
        for action in idea.next_actions:
            tasks.append(
                {
                    "meeting_id": meeting_id,
                    "idea_id": idea.id or "unknown",
                    "student_name": idea.student_name,
                    "title": action.title,
                    "owner": action.owner,
                    "due_date": action.due_date,
                    "priority": action.priority,
                    "success_metrics": idea.validation_metrics,
                    "dependency_note": action.rationale,
                    "rationale": action.rationale,
                }
            )

    questions = []
    for student in progress.student_progress:
        questions.extend(student.unresolved_questions)

    return ResearchPlanResult(
        meeting_id=meeting_id,
        summary="Fallback plan assembled from advisor idea next-actions already captured in the meeting.",
        tasks=tasks,
        questions_to_answer=questions[:6],
    )


def _generate_reading_batch(
    *,
    transcript: ParsedTranscript,
    ideas: list[ResearchIdea],
    progress: MeetingProgressSnapshot,
    meeting_id: str,
    reading_service: ReadingRecommendationService,
) -> tuple[ReadingRecommendationBatch, bool, str]:
    try:
        return (
            reading_service.generate_recommendations(
                transcript,
                ideas,
                progress=progress,
                meeting_id=meeting_id,
            ),
            False,
            "",
        )
    except ReadingRecommendationError as exc:
        fallback = _build_reading_batch_from_ideas(meeting_id=meeting_id, ideas=ideas)
        if fallback.recommendations:
            return (
                fallback,
                True,
                f"Reading generation failed: {exc}. Fell back to idea-linked readings that were already grounded during idea capture.",
            )
        raise ReviewPipelineError(
            stage_key="reading-recommendation",
            agent_name="推荐阅读 Agent",
            message=str(exc),
            fallback="Use idea-linked readings from advisor idea capture if they were already extracted. No usable fallback was available here.",
        ) from exc


def _build_reading_batch_from_ideas(
    *,
    meeting_id: str,
    ideas: list[ResearchIdea],
) -> ReadingRecommendationBatch:
    recommendations = []
    seen_titles: set[str] = set()
    for idea in ideas:
        for reading in idea.recommended_reading:
            if reading.title in seen_titles:
                continue
            recommendations.append(reading.model_copy(update={"meeting_id": meeting_id}))
            seen_titles.add(reading.title)

    return ReadingRecommendationBatch(
        meeting_id=meeting_id,
        summary="Fallback reading list assembled from advisor idea capture.",
        recommendations=recommendations,
    )


def _build_review_explanations(
    *,
    prior_memory: ProjectMemorySnapshot,
    transcript: ParsedTranscript,
    progress: MeetingProgressSnapshot,
    ideas: AdvisorIdeaCaptureResult,
    research_plan: ResearchPlanResult,
    reading_batch: ReadingRecommendationBatch,
    verified_claims: list[ClaimVerificationResult],
    briefing: BriefingResult,
) -> ReviewExplanationBundle:
    return ReviewExplanationBundle(
        action_items=_build_action_item_insights(
            prior_memory=prior_memory,
            transcript=transcript,
            progress=progress,
            ideas=ideas.ideas,
            research_plan=research_plan,
        ),
        readings=_build_reading_insights(
            prior_memory=prior_memory,
            transcript=transcript,
            progress=progress,
            ideas=ideas.ideas,
            reading_batch=reading_batch,
        ),
        claims=_build_claim_insights(verified_claims),
        briefing_items=_build_briefing_item_insights(briefing),
    )


def _build_action_item_insights(
    *,
    prior_memory: ProjectMemorySnapshot,
    transcript: ParsedTranscript,
    progress: MeetingProgressSnapshot,
    ideas: list[ResearchIdea],
    research_plan: ResearchPlanResult,
) -> list[ActionItemInsight]:
    idea_by_id = {idea.id: idea for idea in ideas if idea.id}
    prior_open_tasks = [task for task in prior_memory.action_items if task.status != "done"]
    insights: list[ActionItemInsight] = []

    for task in research_plan.tasks:
        attributions: list[ArtifactAttribution] = []
        linked_idea = idea_by_id.get(task.idea_id)
        if linked_idea is not None:
            attributions.append(
                ArtifactAttribution(
                    source_type="advisor_idea",
                    origin_layer="current_transcript",
                    label=linked_idea.idea_text,
                    detail=linked_idea.expected_validation,
                    meeting_id=linked_idea.meeting_id,
                    chunk_ids=_match_chunk_ids(transcript, linked_idea.idea_text),
                )
            )

        student = next(
            (
                item
                for item in progress.student_progress
                if item.student_name == task.student_name
            ),
            None,
        )
        if student is not None and student.blockers:
            blocker = student.blockers[0]
            attributions.append(
                ArtifactAttribution(
                    source_type="blocker",
                    origin_layer="current_transcript",
                    label=blocker,
                    detail="Current blocker that makes this task necessary.",
                    meeting_id=student.meeting_id,
                    chunk_ids=_match_chunk_ids(transcript, blocker),
                )
            )
        if student is not None and student.unresolved_questions:
            question = student.unresolved_questions[0]
            attributions.append(
                ArtifactAttribution(
                    source_type="unresolved_question",
                    origin_layer="current_transcript",
                    label=question,
                    detail="Open question the task is meant to close.",
                    meeting_id=student.meeting_id,
                    chunk_ids=_match_chunk_ids(transcript, question),
                )
            )

        carryover_task = next(
            (
                item
                for item in prior_open_tasks
                if item.student_name == task.student_name and _texts_overlap(item.title, task.title)
            ),
            None,
        )
        carryover = carryover_task is not None
        if carryover_task is not None:
            attributions.append(
                ArtifactAttribution(
                    source_type="action_item",
                    origin_layer="history_memory",
                    label=carryover_task.title,
                    detail="Historical open task that is being carried forward into the current plan.",
                    meeting_id=carryover_task.meeting_id,
                )
            )

        insights.append(
            ActionItemInsight(
                action_item_id=_action_item_key(task.title, task.owner),
                title=task.title,
                rationale=task.rationale,
                output_summary=(
                    "Derived from current advisor guidance and blockers."
                    if not carryover
                    else "Derived from current advisor guidance while carrying forward unresolved historical work."
                ),
                carryover=carryover,
                attributions=attributions,
            )
        )
    return insights


def _build_reading_insights(
    *,
    prior_memory: ProjectMemorySnapshot,
    transcript: ParsedTranscript,
    progress: MeetingProgressSnapshot,
    ideas: list[ResearchIdea],
    reading_batch: ReadingRecommendationBatch,
) -> list[ReadingInsight]:
    idea_by_id = {idea.id: idea for idea in ideas if idea.id}
    prior_open_tasks = [task for task in prior_memory.action_items if task.status != "done"]
    insights: list[ReadingInsight] = []

    for reading in reading_batch.recommendations:
        attributions: list[ArtifactAttribution] = []
        linked_idea = idea_by_id.get(reading.idea_id)
        if linked_idea is not None:
            attributions.append(
                ArtifactAttribution(
                    source_type="advisor_idea",
                    origin_layer="current_transcript",
                    label=linked_idea.idea_text,
                    detail="Advisor idea that this reading is meant to support.",
                    meeting_id=linked_idea.meeting_id,
                    chunk_ids=_match_chunk_ids(transcript, linked_idea.idea_text),
                )
            )

        student = next(
            (
                item
                for item in progress.student_progress
                if item.student_name == reading.student_name
            ),
            None,
        )
        if student is not None and student.blockers:
            blocker = student.blockers[0]
            attributions.append(
                ArtifactAttribution(
                    source_type="blocker",
                    origin_layer="current_transcript",
                    label=blocker,
                    detail="Current blocker that this reading is expected to unblock.",
                    meeting_id=student.meeting_id,
                    chunk_ids=_match_chunk_ids(transcript, blocker),
                )
            )

        prior_task = next(
            (
                item
                for item in prior_open_tasks
                if item.student_name == reading.student_name
            ),
            None,
        )
        if prior_task is not None:
            attributions.append(
                ArtifactAttribution(
                    source_type="action_item",
                    origin_layer="history_memory",
                    label=prior_task.title,
                    detail="Historical open task that still shapes the reading priority.",
                    meeting_id=prior_task.meeting_id,
                )
            )

        insights.append(
            ReadingInsight(
                reading_id=reading.id or reading.title,
                title=reading.title,
                reason=reading.reason,
                output_summary="Prioritized because it directly supports next week's execution path.",
                attributions=attributions,
            )
        )
    return insights


def _build_claim_insights(
    verified_claims: list[ClaimVerificationResult],
) -> list[ClaimInsight]:
    insights: list[ClaimInsight] = []
    for claim_result in verified_claims:
        attributions = [
            ArtifactAttribution(
                source_type="claim",
                origin_layer="current_transcript",
                label=claim_result.claim.transcript_snippet,
                detail="Transcript slice that triggered verification.",
                meeting_id=claim_result.claim.meeting_id,
                chunk_ids=claim_result.claim.source_chunk_ids,
            )
        ]
        if claim_result.evidence_cards:
            top_card = claim_result.evidence_cards[0]
            attributions.append(
                ArtifactAttribution(
                    source_type="key_paper",
                    origin_layer="evidence_retrieval",
                    label=top_card.source_title,
                    detail=top_card.reason,
                    meeting_id=claim_result.claim.meeting_id,
                )
            )

        insights.append(
            ClaimInsight(
                claim_id=claim_result.claim.id or claim_result.claim.text,
                title=claim_result.claim.text,
                trigger_reason="Verification was enabled and this claim materially affects the research direction.",
                verdict=claim_result.verdict,
                output_summary=claim_result.summary,
                attributions=attributions,
            )
        )
    return insights


def _build_briefing_item_insights(
    briefing: BriefingResult,
) -> list[BriefingItemInsight]:
    insights: list[BriefingItemInsight] = []
    for task in briefing.carryover_tasks:
        insights.append(
            BriefingItemInsight(
                item_id=f"carryover::{task.meeting_id or 'unknown'}::{task.title}",
                item_type="carryover_task",
                title=task.title,
                reason="This unfinished task is being carried over from an earlier meeting.",
                origin_layer="history_memory",
                attributions=[
                    ArtifactAttribution(
                        source_type="action_item",
                        origin_layer="history_memory",
                        label=task.title,
                        detail=f"Open task from meeting {task.meeting_id or 'unknown'}.",
                        meeting_id=task.meeting_id,
                    )
                ],
            )
        )

    for index, item in enumerate(briefing.recommended_agenda, start=1):
        origin_layer = "history_memory" if "open task" in item.reason.lower() else "current_transcript"
        insights.append(
            BriefingItemInsight(
                item_id=f"agenda::{index:02d}",
                item_type="agenda",
                title=item.title,
                reason=item.reason,
                origin_layer=origin_layer,
                attributions=[],
            )
        )

    for index, question in enumerate(briefing.focus_questions, start=1):
        origin_layer = "history_memory" if "before" in question.lower() else "current_transcript"
        insights.append(
            BriefingItemInsight(
                item_id=f"focus-question::{index:02d}",
                item_type="focus_question",
                title=question,
                reason="Included because the next meeting should explicitly answer it.",
                origin_layer=origin_layer,
                attributions=[],
            )
        )

    return insights


def _match_chunk_ids(transcript: ParsedTranscript, text: str, *, limit: int = 3) -> list[str]:
    if not text:
        return []
    normalized_text = text.lower()
    text_tokens = _tokenize(text)
    matches: list[str] = []
    for chunk in transcript.chunks:
        chunk_text = chunk.text.lower()
        if normalized_text in chunk_text:
            matches.append(chunk.chunk_id)
            continue
        chunk_tokens = _tokenize(chunk.text)
        if text_tokens and len(text_tokens & chunk_tokens) >= min(2, len(text_tokens)):
            matches.append(chunk.chunk_id)
    return matches[:limit]


def _action_item_key(title: str, owner: str) -> str:
    return f"{title.strip().lower()}::{owner.strip().lower()}"


def _texts_overlap(left: str, right: str) -> bool:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return False
    return len(left_tokens & right_tokens) >= 2


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 4
    }


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
