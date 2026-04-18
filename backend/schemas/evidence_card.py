from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EvidenceSourceType = Literal["paper", "transcript", "project_note", "unknown"]
EvidenceStance = Literal["support", "contradict", "needs_verification"]
EvidenceConfidence = Literal["low", "medium", "high"]


class EvidenceCard(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str | None = None
    claim_id: str | None = None
    source_title: str
    source_url: str = "unknown"
    source_type: EvidenceSourceType = "paper"
    stance: EvidenceStance = "needs_verification"
    snippet: str = "unknown"
    score: float = 0.0
    confidence: EvidenceConfidence = "medium"
    reason: str = "unknown"
    authors: list[str] = Field(default_factory=list)
    publication_year: int | None = None

    @field_validator("source_url", "snippet", "reason", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

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

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: object) -> EvidenceConfidence:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"weak", "tentative"}:
            return "low"
        if normalized in {"strong", "certain"}:
            return "high"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized

    @field_validator("stance", mode="before")
    @classmethod
    def normalize_stance(cls, value: object) -> EvidenceStance:
        normalized = str(value or "needs_verification").strip().lower().replace(" ", "_")
        mapping = {
            "supported": "support",
            "supports": "support",
            "supporting": "support",
            "contradicted": "contradict",
            "contradicts": "contradict",
            "conflict": "contradict",
            "conflicts": "contradict",
            "unknown": "needs_verification",
            "unclear": "needs_verification",
            "neutral": "needs_verification",
            "mixed": "needs_verification",
            "needs-verification": "needs_verification",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"support", "contradict", "needs_verification"}:
            return "needs_verification"
        return normalized

    @field_validator("source_type", mode="before")
    @classmethod
    def normalize_source_type(cls, value: object) -> EvidenceSourceType:
        normalized = str(value or "paper").strip().lower().replace(" ", "_")
        if normalized in {"article", "journal", "preprint"}:
            return "paper"
        if normalized not in {"paper", "transcript", "project_note", "unknown"}:
            return "unknown"
        return normalized

    @field_validator("authors", mode="before")
    @classmethod
    def coerce_authors(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            authors: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    authors.append(text)
            return authors
        text = str(value).strip()
        return [text] if text else []


class EvidenceRetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claim_id: str | None = None
    query: str
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
