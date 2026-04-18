from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from backend.schemas.project_memory import ProjectMemorySnapshot
from backend.services.briefing_service import BriefingResult, BriefingService
from backend.services.deliverable_service import (
    DeliverableDocument,
    DeliverableService,
    DeliverableType,
)
from backend.services.project_memory_service import ProjectMemoryService

router = APIRouter(prefix="/api/deliverables", tags=["deliverables"])


class DeliverableGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str
    deliverable_type: DeliverableType
    query: str | None = None


class DeliverableGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_memory: ProjectMemorySnapshot
    briefing: BriefingResult
    document: DeliverableDocument


def get_project_memory_service() -> ProjectMemoryService:
    return ProjectMemoryService()


def get_briefing_service() -> BriefingService:
    return BriefingService()


def get_deliverable_service() -> DeliverableService:
    return DeliverableService()


@router.post("/generate", response_model=DeliverableGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_deliverable(
    request: DeliverableGenerationRequest,
    project_memory_service: Annotated[ProjectMemoryService, Depends(get_project_memory_service)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
    deliverable_service: Annotated[DeliverableService, Depends(get_deliverable_service)],
) -> DeliverableGenerationResponse:
    project_memory = project_memory_service.load_project_memory(
        request.project_id,
        query=request.query,
    )
    if project_memory.project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_id}' was not found in local memory.",
        )

    briefing = briefing_service.generate_briefing(project_memory)
    document = deliverable_service.generate_deliverable(
        request.deliverable_type,
        project_memory=project_memory,
        briefing=briefing,
    )
    return DeliverableGenerationResponse(
        project_memory=project_memory,
        briefing=briefing,
        document=document,
    )
