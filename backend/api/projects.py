from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.action_item import ActionItem, ActionItemStatus
from backend.schemas.orchestration import ArtifactAttribution, BriefingItemInsight
from backend.schemas.project_memory import ProjectMemorySnapshot
from backend.services.briefing_service import BriefingResult, BriefingService
from backend.services.project_memory_service import ProjectMemoryService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectMemoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_memory: ProjectMemorySnapshot
    briefing: BriefingResult
    briefing_items: list[BriefingItemInsight] = Field(default_factory=list)


class ActionItemStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    title: str
    owner: str
    status: ActionItemStatus


class ActionItemStatusUpdateResponse(ProjectMemoryResponse):
    updated_action_item: ActionItem


def get_project_memory_service() -> ProjectMemoryService:
    return ProjectMemoryService()


def get_briefing_service() -> BriefingService:
    return BriefingService()


@router.get("/{project_id}/memory", response_model=ProjectMemoryResponse)
async def get_project_memory(
    project_id: str,
    project_memory_service: Annotated[ProjectMemoryService, Depends(get_project_memory_service)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
    query: str | None = None,
) -> ProjectMemoryResponse:
    project_memory = project_memory_service.load_project_memory(project_id, query=query)
    if project_memory.project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' was not found in local memory.",
        )

    briefing = briefing_service.generate_briefing(project_memory)
    return ProjectMemoryResponse(
        project_memory=project_memory,
        briefing=briefing,
        briefing_items=_build_briefing_item_insights(briefing),
    )


@router.patch("/{project_id}/action-items/status", response_model=ActionItemStatusUpdateResponse)
async def update_action_item_status(
    project_id: str,
    request: ActionItemStatusUpdateRequest,
    project_memory_service: Annotated[ProjectMemoryService, Depends(get_project_memory_service)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
) -> ActionItemStatusUpdateResponse:
    updated_action_item = project_memory_service.update_action_item_status(
        project_id,
        meeting_id=request.meeting_id,
        title=request.title,
        owner=request.owner,
        status=request.status,
    )
    if updated_action_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Action item '{request.title}' owned by '{request.owner}' "
                f"for meeting '{request.meeting_id}' was not found."
            ),
        )

    project_memory = project_memory_service.load_project_memory(project_id)
    if project_memory.project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' was not found in local memory.",
        )

    briefing = briefing_service.generate_briefing(project_memory)
    return ActionItemStatusUpdateResponse(
        updated_action_item=updated_action_item,
        project_memory=project_memory,
        briefing=briefing,
        briefing_items=_build_briefing_item_insights(briefing),
    )


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
