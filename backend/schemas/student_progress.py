from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.action_item import ActionItem
from backend.schemas.risk import Risk


class StudentProgress(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str | None = None
    student_name: str
    completed_work: list[str] = Field(default_factory=list)
    current_result: str = "unknown"
    blockers: list[str] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    next_step_suggestion: str = "unknown"
    action_items: list[ActionItem] = Field(default_factory=list)

    @field_validator("completed_work", "blockers", "unresolved_questions", mode="before")
    @classmethod
    def coerce_list_fields(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            items: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    items.append(text)
            return items
        text = str(value).strip()
        return [text] if text else []

    @field_validator("current_result", "next_step_suggestion", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"
        text = str(value).strip()
        return text or "unknown"


class MeetingProgressSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    summary: str = ""
    student_progress: list[StudentProgress] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
