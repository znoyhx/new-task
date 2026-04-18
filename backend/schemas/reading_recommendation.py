from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReadingPriority = Literal["low", "medium", "high"]


class ReadingRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str | None = None
    meeting_id: str | None = None
    idea_id: str | None = None
    student_name: str = "unknown"
    title: str
    source_url: str = "unknown"
    reason: str = "unknown"
    priority: ReadingPriority = "medium"

    @field_validator("student_name", "source_url", "reason", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> ReadingPriority:
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


class ReadingRecommendationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    summary: str = ""
    recommendations: list[ReadingRecommendation] = Field(default_factory=list)
