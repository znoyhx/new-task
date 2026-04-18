from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

RiskLevel = Literal["low", "medium", "high"]


class Risk(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str | None = None
    student_name: str | None = None
    title: str
    level: RiskLevel = "medium"
    description: str = ""
    owner: str = "unknown"
    mitigation: str = "unknown"

    @field_validator("owner", "mitigation", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: object) -> RiskLevel:
        normalized = str(value or "medium").strip().lower()
        mapping = {
            "critical": "high",
            "severe": "high",
            "warning": "medium",
            "moderate": "medium",
            "minor": "low",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized
