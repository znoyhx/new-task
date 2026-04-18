from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.evidence_card import EvidenceCard

ClaimKind = Literal["factual", "strategic"]
ClaimVerdict = Literal["supported", "contradicted", "needs_verification"]
ClaimConfidence = Literal["low", "medium", "high"]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str | None = None
    meeting_id: str | None = None
    idea_id: str | None = None
    text: str
    speaker: str = "unknown"
    timestamp_start: str | None = None
    timestamp_end: str | None = None
    transcript_snippet: str = "unknown"
    source_chunk_ids: list[str] = Field(default_factory=list)
    claim_kind: ClaimKind = "factual"
    confidence: ClaimConfidence = "medium"
    verification_status: ClaimVerdict = "needs_verification"

    @field_validator("speaker", "transcript_snippet", mode="before")
    @classmethod
    def default_unknown_text(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("timestamp_start", "timestamp_end", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text or text.lower() in {"unknown", "none", "null"}:
            return None
        return text

    @field_validator("claim_kind", mode="before")
    @classmethod
    def normalize_claim_kind(cls, value: object) -> ClaimKind:
        normalized = str(value or "factual").strip().lower()
        if normalized in {"plan", "proposal", "recommendation", "strategy"}:
            return "strategic"
        if normalized not in {"factual", "strategic"}:
            return "factual"
        return normalized

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: object) -> ClaimConfidence:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"weak", "tentative"}:
            return "low"
        if normalized in {"strong", "certain"}:
            return "high"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_verdict(cls, value: object) -> ClaimVerdict:
        normalized = str(value or "needs_verification").strip().lower().replace(" ", "_")
        mapping = {
            "support": "supported",
            "supports": "supported",
            "supporting": "supported",
            "contradict": "contradicted",
            "contradicts": "contradicted",
            "refuted": "contradicted",
            "mixed": "needs_verification",
            "unknown": "needs_verification",
            "unclear": "needs_verification",
            "needs-verification": "needs_verification",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"supported", "contradicted", "needs_verification"}:
            return "needs_verification"
        return normalized

    @field_validator("source_chunk_ids", mode="before")
    @classmethod
    def coerce_source_chunk_ids(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            chunk_ids: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    chunk_ids.append(text)
            return chunk_ids
        text = str(value).strip()
        return [text] if text else []


class ClaimExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    summary: str = ""
    claims: list[Claim] = Field(default_factory=list)


class ClaimVerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claim: Claim
    verdict: ClaimVerdict = "needs_verification"
    confidence: ClaimConfidence = "medium"
    summary: str = ""
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    @field_validator("gaps", mode="before")
    @classmethod
    def coerce_gaps(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            gaps: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    gaps.append(text)
            return gaps
        text = str(value).strip()
        return [text] if text else []
