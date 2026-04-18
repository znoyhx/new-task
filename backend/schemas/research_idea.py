from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.reading_recommendation import ReadingRecommendation

IdeaActionPriority = Literal["low", "medium", "high"]
ResearchIdeaStatus = Literal["proposed", "planned", "validated", "deferred", "unknown"]


class IdeaNextAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    owner: str = "unknown"
    due_date: str = "unknown"
    priority: IdeaActionPriority = "medium"
    rationale: str = "unknown"

    @field_validator("owner", "due_date", "rationale", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> IdeaActionPriority:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"critical", "urgent", "p0"}:
            return "high"
        if normalized in {"normal", "default", "p2"}:
            return "medium"
        if normalized in {"minor", "optional", "p3"}:
            return "low"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized


class ResearchIdea(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str | None = None
    meeting_id: str | None = None
    student_name: str = "unknown"
    idea_text: str
    suggested_by: str = "advisor"
    expected_validation: str = "unknown"
    status: ResearchIdeaStatus = "proposed"
    validation_metrics: list[str] = Field(default_factory=list)
    next_actions: list[IdeaNextAction] = Field(default_factory=list)
    recommended_reading: list[ReadingRecommendation] = Field(default_factory=list)

    @field_validator("student_name", "suggested_by", "expected_validation", mode="before")
    @classmethod
    def default_text_fields(cls, value: object, info) -> str:
        if value is None:
            return "advisor" if info.field_name == "suggested_by" else "unknown"

        text = str(value).strip()
        if text:
            return text
        return "advisor" if info.field_name == "suggested_by" else "unknown"

    @field_validator("validation_metrics", mode="before")
    @classmethod
    def coerce_validation_metrics(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            metrics: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    metrics.append(text)
            return metrics
        text = str(value).strip()
        return [text] if text else []

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> ResearchIdeaStatus:
        normalized = str(value or "proposed").strip().lower()
        mapping = {
            "new": "proposed",
            "open": "proposed",
            "active": "planned",
            "in_progress": "planned",
            "in progress": "planned",
            "tested": "validated",
            "done": "validated",
            "parked": "deferred",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"proposed", "planned", "validated", "deferred", "unknown"}:
            return "unknown"
        return normalized


class AdvisorIdeaCaptureResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    summary: str = ""
    ideas: list[ResearchIdea] = Field(default_factory=list)
