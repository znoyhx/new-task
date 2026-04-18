from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

ActionItemPriority = Literal["low", "medium", "high"]
ActionItemStatus = Literal["open", "in_progress", "blocked", "done", "unknown"]


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str | None = None
    student_name: str | None = None
    title: str
    owner: str = "unknown"
    deadline: str = "unknown"
    priority: ActionItemPriority = "medium"
    status: ActionItemStatus = "open"
    dependency_note: str = "unknown"

    @field_validator("owner", "deadline", "dependency_note", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> ActionItemPriority:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"urgent", "p0", "critical"}:
            return "high"
        if normalized in {"normal", "default", "p2"}:
            return "medium"
        if normalized in {"minor", "p3"}:
            return "low"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> ActionItemStatus:
        normalized = str(value or "open").strip().lower()
        mapping = {
            "todo": "open",
            "pending": "open",
            "in progress": "in_progress",
            "doing": "in_progress",
            "complete": "done",
            "completed": "done",
            "finished": "done",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"open", "in_progress", "blocked", "done", "unknown"}:
            return "unknown"
        return normalized
