from __future__ import annotations

from typing import Any, Protocol, Sequence

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.claim import Claim, ClaimVerificationResult
from backend.schemas.evidence_card import EvidenceCard
from backend.services.evidence_retrieval_service import EvidenceRetrievalService


class ChatJsonClient(Protocol):
    def chat_json(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        ...


class ClaimVerificationError(RuntimeError):
    """Raised when claim verification cannot complete."""


class ClaimVerificationService:
    system_prompt = (
        "You verify research meeting claims against provided evidence cards. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(
        self,
        client: ChatJsonClient | None = None,
        retrieval_service: EvidenceRetrievalService | None = None,
    ) -> None:
        self.client = client or DeepSeekClient()
        self.retrieval_service = retrieval_service

    def verify_claim(
        self,
        claim: Claim,
        evidence_cards: Sequence[EvidenceCard] | None = None,
    ) -> ClaimVerificationResult:
        available_evidence = list(evidence_cards or [])
        if not available_evidence and self.retrieval_service is not None:
            available_evidence = self.retrieval_service.retrieve_evidence(claim).evidence_cards

        if not available_evidence:
            return ClaimVerificationResult(
                claim=claim.model_copy(update={"verification_status": "needs_verification"}),
                verdict="needs_verification",
                confidence="low",
                summary="No evidence cards were available for verification.",
                evidence_cards=[],
                gaps=["No external evidence was retrieved for this claim."],
            )

        payload = self.client.chat_json(
            self._build_prompt(claim, available_evidence),
            system_prompt=self.system_prompt,
            temperature=0.0,
            timeout=60.0,
        )
        return self._normalize_payload(payload, claim=claim, evidence_cards=available_evidence)

    def _build_prompt(self, claim: Claim, evidence_cards: Sequence[EvidenceCard]) -> str:
        evidence_lines: list[str] = []
        for card in evidence_cards:
            evidence_lines.append(
                f"- {card.id or 'unknown'} | title={card.source_title} | url={card.source_url} "
                f"| snippet={card.snippet}"
            )

        return (
            "Verify the claim against the evidence cards.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "verdict": "supported | contradicted | needs_verification",\n'
            '  "confidence": "low | medium | high",\n'
            '  "gaps": ["string"],\n'
            '  "evidence_assessments": [\n'
            "    {\n"
            '      "evidence_id": "string",\n'
            '      "stance": "support | contradict | needs_verification",\n'
            '      "reason": "string",\n'
            '      "confidence": "low | medium | high"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Use only the provided evidence cards.\n"
            "- If the evidence is incomplete, indirect, or mixed, choose needs_verification.\n"
            "- Contradicted requires direct conflicting evidence, not just absence of support.\n"
            "- Assess every evidence card by id.\n\n"
            "Claim:\n"
            f"- text={claim.text}\n"
            f"- speaker={claim.speaker}\n"
            f"- kind={claim.claim_kind}\n\n"
            "Evidence cards:\n"
            f"{chr(10).join(evidence_lines)}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        claim: Claim,
        evidence_cards: Sequence[EvidenceCard],
    ) -> ClaimVerificationResult:
        raw_assessments = (
            payload.get("evidence_assessments")
            or payload.get("assessments")
            or payload.get("evidence_cards")
            or []
        )
        evidence_by_id = {
            card.id: card
            for card in evidence_cards
            if card.id
        }
        normalized_cards: list[EvidenceCard] = []
        assessment_by_id: dict[str, dict[str, Any]] = {}

        for assessment in self._ensure_list(raw_assessments):
            if not isinstance(assessment, dict):
                continue
            evidence_id = self._clean_text(
                assessment.get("evidence_id") or assessment.get("id")
            )
            if not evidence_id:
                continue
            assessment_by_id[evidence_id] = assessment

        for card in evidence_cards:
            if card.id and card.id in assessment_by_id:
                assessment = assessment_by_id[card.id]
                payload = card.model_dump(mode="json")
                payload.update(
                    {
                        "stance": assessment.get("stance", card.stance),
                        "reason": assessment.get("reason", card.reason),
                        "confidence": assessment.get("confidence", card.confidence),
                    }
                )
                normalized_cards.append(EvidenceCard.model_validate(payload))
            else:
                normalized_cards.append(card)

        verdict = self._normalize_verdict(payload.get("verdict"))
        if verdict == "needs_verification":
            verdict = self._derive_verdict_from_evidence(normalized_cards)

        confidence = self._normalize_confidence(payload.get("confidence"))
        summary = self._clean_text(payload.get("summary"))
        if not summary:
            summary = f"Claim review finished with verdict: {verdict}."

        updated_claim = claim.model_copy(update={"verification_status": verdict})
        return ClaimVerificationResult(
            claim=updated_claim,
            verdict=verdict,
            confidence=confidence,
            summary=summary,
            evidence_cards=normalized_cards,
            gaps=payload.get("gaps") or [],
        )

    def _derive_verdict_from_evidence(self, evidence_cards: Sequence[EvidenceCard]) -> str:
        stances = {card.stance for card in evidence_cards}
        if stances == {"support"}:
            return "supported"
        if stances == {"contradict"}:
            return "contradicted"
        return "needs_verification"

    def _normalize_verdict(self, value: object) -> str:
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
            "needs-verification": "needs_verification",
        }
        normalized = mapping.get(normalized, normalized)
        if normalized not in {"supported", "contradicted", "needs_verification"}:
            return "needs_verification"
        return normalized

    def _normalize_confidence(self, value: object) -> str:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"weak", "tentative"}:
            return "low"
        if normalized in {"strong", "certain"}:
            return "high"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized

    def _ensure_list(self, value: object) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _clean_text(self, value: object, *, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default
