from __future__ import annotations

from typing import Any, Protocol

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.claim import Claim, ClaimExtractionResult
from backend.schemas.meeting import ParsedTranscript, TranscriptChunk
from backend.services.response_language import ResponseLanguage, build_json_output_language_instruction


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


class ClaimExtractionError(RuntimeError):
    """Raised when claim extraction cannot complete."""


class ClaimExtractionService:
    base_system_prompt = (
        "You extract high-value factual or strategic claims from a research-group meeting transcript. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(self, client: ChatJsonClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def extract_claims(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
        output_language: ResponseLanguage = "en",
    ) -> ClaimExtractionResult:
        resolved_meeting_id = meeting_id or transcript.meeting_id
        if not resolved_meeting_id:
            raise ClaimExtractionError("meeting_id is required for claim extraction.")
        if not transcript.chunks:
            raise ClaimExtractionError("Cannot extract claims from an empty transcript.")

        payload = self.client.chat_json(
            self._build_prompt(transcript, output_language=output_language),
            system_prompt=self._build_system_prompt(output_language),
            temperature=0.0,
            timeout=60.0,
        )
        return self._normalize_payload(
            payload,
            transcript=transcript,
            meeting_id=resolved_meeting_id,
        )

    def _build_system_prompt(self, output_language: ResponseLanguage) -> str:
        return f"{self.base_system_prompt} {build_json_output_language_instruction(output_language)}"

    def _build_prompt(
        self,
        transcript: ParsedTranscript,
        *,
        output_language: ResponseLanguage,
    ) -> str:
        transcript_lines: list[str] = []
        for chunk in transcript.chunks:
            if chunk.timestamp_start and chunk.timestamp_end:
                timestamp = f"[{chunk.timestamp_start}-{chunk.timestamp_end}]"
            elif chunk.timestamp_start:
                timestamp = f"[{chunk.timestamp_start}]"
            else:
                timestamp = ""
            prefix = f"{timestamp} {chunk.speaker}:".strip()
            transcript_lines.append(f"{prefix} {chunk.text}".strip())

        return (
            "Read the following research-group meeting transcript and extract only the highest-value claims.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "claims": [\n'
            "    {\n"
            '      "text": "string",\n'
            '      "speaker": "string or unknown",\n'
            '      "timestamp_start": "string or unknown",\n'
            '      "timestamp_end": "string or unknown",\n'
            '      "transcript_snippet": "string",\n'
            '      "claim_kind": "factual | strategic",\n'
            '      "confidence": "low | medium | high"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Extract only claims that materially affect research direction, evidence lookup, or next-week execution.\n"
            "- Ignore routine status chatter and purely subjective opinions.\n"
            "- A factual claim states a result, limitation, comparison, or observable finding.\n"
            "- A strategic claim states a recommended direction, research hypothesis, or experimental priority.\n"
            "- Return an empty list if no claim is strong enough.\n"
            "- Keep the list concise.\n\n"
            f"Output language: {build_json_output_language_instruction(output_language)}\n\n"
            "Transcript:\n"
            f"{chr(10).join(transcript_lines)}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        transcript: ParsedTranscript,
        meeting_id: str,
    ) -> ClaimExtractionResult:
        summary = self._clean_text(payload.get("summary"))
        raw_claims = payload.get("claims") or payload.get("items") or payload.get("statements") or []
        claims: list[Claim] = []

        for index, raw_claim in enumerate(self._ensure_list(raw_claims), start=1):
            normalized = self._normalize_claim(
                raw_claim,
                transcript=transcript,
                meeting_id=meeting_id,
                index=index,
            )
            if normalized is None:
                continue
            claims.append(Claim.model_validate(normalized))

        return ClaimExtractionResult(
            meeting_id=meeting_id,
            summary=summary,
            claims=claims,
        )

    def _normalize_claim(
        self,
        raw_claim: object,
        *,
        transcript: ParsedTranscript,
        meeting_id: str,
        index: int,
    ) -> dict[str, Any] | None:
        if isinstance(raw_claim, str):
            claim_text = self._clean_text(raw_claim)
            if not claim_text:
                return None
            chunk_ids = self._match_source_chunk_ids(
                transcript,
                claim_text=claim_text,
                speaker="unknown",
                timestamp_start=None,
                transcript_snippet=claim_text,
            )
            return {
                "id": f"{meeting_id}-claim-{index:02d}",
                "meeting_id": meeting_id,
                "text": claim_text,
                "speaker": "unknown",
                "timestamp_start": None,
                "timestamp_end": None,
                "transcript_snippet": claim_text,
                "source_chunk_ids": chunk_ids,
                "claim_kind": "factual",
                "confidence": "medium",
            }

        if not isinstance(raw_claim, dict):
            return None

        claim_text = self._clean_text(
            raw_claim.get("text")
            or raw_claim.get("claim")
            or raw_claim.get("statement")
            or raw_claim.get("claim_text")
        )
        if not claim_text:
            return None

        speaker = self._clean_text(raw_claim.get("speaker"), default="unknown")
        timestamp_start = self._clean_text(raw_claim.get("timestamp_start"), default="")
        timestamp_end = self._clean_text(raw_claim.get("timestamp_end"), default="")
        transcript_snippet = self._clean_text(
            raw_claim.get("transcript_snippet") or raw_claim.get("snippet"),
            default=claim_text,
        )
        source_chunk_ids = self._ensure_text_list(raw_claim.get("source_chunk_ids"))
        if not source_chunk_ids:
            source_chunk_ids = self._match_source_chunk_ids(
                transcript,
                claim_text=claim_text,
                speaker=speaker,
                timestamp_start=timestamp_start or None,
                transcript_snippet=transcript_snippet,
            )

        return {
            "id": self._clean_text(raw_claim.get("id"), default=f"{meeting_id}-claim-{index:02d}"),
            "meeting_id": meeting_id,
            "idea_id": self._clean_text(raw_claim.get("idea_id"), default="") or None,
            "text": claim_text,
            "speaker": speaker,
            "timestamp_start": timestamp_start or None,
            "timestamp_end": timestamp_end or None,
            "transcript_snippet": transcript_snippet,
            "source_chunk_ids": source_chunk_ids,
            "claim_kind": raw_claim.get("claim_kind", "factual"),
            "confidence": raw_claim.get("confidence", "medium"),
            "verification_status": raw_claim.get("verification_status", "needs_verification"),
        }

    def _match_source_chunk_ids(
        self,
        transcript: ParsedTranscript,
        *,
        claim_text: str,
        speaker: str,
        timestamp_start: str | None,
        transcript_snippet: str,
    ) -> list[str]:
        matched_chunk_ids: list[str] = []
        normalized_speaker = speaker.strip().lower()
        normalized_claim_text = claim_text.strip().lower()
        normalized_snippet = transcript_snippet.strip().lower()

        for chunk in transcript.chunks:
            if self._chunk_matches(
                chunk,
                speaker=normalized_speaker,
                timestamp_start=timestamp_start,
                claim_text=normalized_claim_text,
                transcript_snippet=normalized_snippet,
            ):
                matched_chunk_ids.append(chunk.chunk_id)

        return matched_chunk_ids[:3]

    def _chunk_matches(
        self,
        chunk: TranscriptChunk,
        *,
        speaker: str,
        timestamp_start: str | None,
        claim_text: str,
        transcript_snippet: str,
    ) -> bool:
        if speaker not in {"", "unknown"} and chunk.speaker.strip().lower() != speaker:
            return False

        if timestamp_start and chunk.timestamp_start == timestamp_start:
            return True

        chunk_text = chunk.text.strip().lower()
        if transcript_snippet and transcript_snippet != "unknown":
            if transcript_snippet in chunk_text or chunk_text in transcript_snippet:
                return True
        if claim_text and (claim_text in chunk_text or chunk_text in claim_text):
            return True
        return False

    def _ensure_list(self, value: object) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _ensure_text_list(self, value: object) -> list[str]:
        items: list[str] = []
        for entry in self._ensure_list(value):
            text = self._clean_text(entry)
            if text:
                items.append(text)
        return items

    def _clean_text(self, value: object, *, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default
