from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import StudentProgress

MemoryEntryType = Literal[
    "meeting_chunk",
    "decision",
    "action_item",
    "claim",
    "advisor_idea",
    "student_progress",
    "key_paper",
    "project_note",
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class ProjectRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str
    name: str
    description: str = ""
    domain: str = "unknown"
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("description", "domain", mode="before")
    @classmethod
    def default_text(cls, value: object, info) -> str:
        if value is None:
            return "" if info.field_name == "description" else "unknown"

        text = str(value).strip()
        if text:
            return text
        return "" if info.field_name == "description" else "unknown"


class ProjectMeetingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    project_id: str
    title: str = "Untitled meeting"
    summary: str = ""
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("title", "summary", mode="before")
    @classmethod
    def default_text(cls, value: object, info) -> str:
        if value is None:
            return "Untitled meeting" if info.field_name == "title" else ""

        text = str(value).strip()
        if text:
            return text
        return "Untitled meeting" if info.field_name == "title" else ""


class ProjectDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    project_id: str | None = None
    meeting_id: str | None = None
    title: str
    rationale: str = "unknown"
    decided_by: str = "unknown"
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("project_id", "meeting_id", mode="before")
    @classmethod
    def default_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    @field_validator("rationale", "decided_by", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"


class KeyPaperMemory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    project_id: str | None = None
    meeting_id: str | None = None
    title: str
    source_url: str = "unknown"
    reason: str = "unknown"
    added_at: datetime = Field(default_factory=utcnow)

    @field_validator("project_id", "meeting_id", mode="before")
    @classmethod
    def default_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    @field_validator("source_url", "reason", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"


class ProjectMemoryVectorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str
    project_id: str
    meeting_id: str | None = None
    entry_type: MemoryEntryType
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("meeting_id", mode="before")
    @classmethod
    def normalize_meeting_id(cls, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None


class ProjectMemorySearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entry_id: str
    project_id: str
    meeting_id: str | None = None
    entry_type: MemoryEntryType
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, value: object) -> float:
        if value is None:
            return 0.0

        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(score, 0.0)


class ProjectMemorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project: ProjectRecord | None = None
    meetings: list[ProjectMeetingRecord] = Field(default_factory=list)
    decisions: list[ProjectDecision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    advisor_ideas: list[ResearchIdea] = Field(default_factory=list)
    student_progress: list[StudentProgress] = Field(default_factory=list)
    key_papers: list[KeyPaperMemory] = Field(default_factory=list)
    relevant_context: list[ProjectMemorySearchHit] = Field(default_factory=list)
