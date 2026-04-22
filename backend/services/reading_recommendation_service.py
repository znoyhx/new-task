from __future__ import annotations

from typing import Any, Protocol, Sequence

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.meeting import ParsedTranscript
from backend.schemas.reading_recommendation import (
    ReadingRecommendation,
    ReadingRecommendationBatch,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot
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


class ReadingRecommendationError(RuntimeError):
    """Raised when recommendation generation cannot complete."""


class ReadingRecommendationService:
    base_system_prompt = (
        "You generate prioritized reading recommendations for a research-group workflow. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(self, client: ChatJsonClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def generate_recommendations(
        self,
        transcript: ParsedTranscript,
        ideas: Sequence[ResearchIdea],
        *,
        progress: MeetingProgressSnapshot | None = None,
        meeting_id: str | None = None,
        output_language: ResponseLanguage = "en",
    ) -> ReadingRecommendationBatch:
        resolved_meeting_id = meeting_id or transcript.meeting_id
        if not resolved_meeting_id:
            raise ReadingRecommendationError("meeting_id is required for reading recommendations.")
        if not transcript.chunks:
            raise ReadingRecommendationError("Cannot generate reading recommendations from an empty transcript.")

        payload = self.client.chat_json(
            self._build_prompt(
                transcript,
                ideas=ideas,
                progress=progress,
                output_language=output_language,
            ),
            system_prompt=self._build_system_prompt(output_language),
            temperature=0.0,
            timeout=60.0,
        )
        return self._normalize_payload(
            payload,
            meeting_id=resolved_meeting_id,
            ideas=ideas,
        )

    def _build_system_prompt(self, output_language: ResponseLanguage) -> str:
        return f"{self.base_system_prompt} {build_json_output_language_instruction(output_language)}"

    def _build_prompt(
        self,
        transcript: ParsedTranscript,
        *,
        ideas: Sequence[ResearchIdea],
        progress: MeetingProgressSnapshot | None,
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

        idea_lines: list[str] = []
        for idea in ideas:
            metrics = ", ".join(idea.validation_metrics) or "none"
            idea_lines.append(
                f"- {idea.id or 'unknown'} | student={idea.student_name} | idea={idea.idea_text} "
                f"| validation={idea.expected_validation} | metrics={metrics}"
            )

        blocker_lines: list[str] = []
        if progress is not None:
            for student in progress.student_progress:
                blockers = ", ".join(student.blockers) or "none"
                blocker_lines.append(f"- {student.student_name}: blockers={blockers}")

        return (
            "Generate prioritized reading recommendations that help the team execute next week's research work.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "recommendations": [\n'
            "    {\n"
            '      "idea_id": "string or unknown",\n'
            '      "student_name": "string or unknown",\n'
            '      "title": "string",\n'
            '      "source_url": "string or unknown",\n'
            '      "reason": "string",\n'
            '      "priority": "low | medium | high"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Prioritize readings that unblock an experiment or directly support an advisor idea.\n"
            "- Use canonical source URLs only when you are confident. Otherwise use the literal string 'unknown'.\n"
            "- Do not fabricate citations or paper metadata.\n"
            "- Keep the list concise and ordered by practical value for next week.\n\n"
            f"Output language: {build_json_output_language_instruction(output_language)}\n\n"
            "Advisor ideas:\n"
            f"{chr(10).join(idea_lines) if idea_lines else '- none'}\n\n"
            "Known blockers:\n"
            f"{chr(10).join(blocker_lines) if blocker_lines else '- none'}\n\n"
            "Transcript:\n"
            f"{chr(10).join(transcript_lines)}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        meeting_id: str,
        ideas: Sequence[ResearchIdea],
    ) -> ReadingRecommendationBatch:
        summary = self._clean_text(payload.get("summary"))
        raw_items = (
            payload.get("recommendations")
            or payload.get("recommended_reading")
            or payload.get("reading_list")
            or []
        )
        idea_by_id = {
            idea.id: idea
            for idea in ideas
            if idea.id
        }
        recommendations: list[ReadingRecommendation] = []

        for index, raw_item in enumerate(self._ensure_list(raw_items), start=1):
            normalized = self._normalize_recommendation(
                raw_item,
                meeting_id=meeting_id,
                index=index,
                idea_by_id=idea_by_id,
            )
            if normalized is None:
                continue
            recommendations.append(ReadingRecommendation.model_validate(normalized))

        return ReadingRecommendationBatch(
            meeting_id=meeting_id,
            summary=summary,
            recommendations=recommendations,
        )

    def _normalize_recommendation(
        self,
        raw_item: object,
        *,
        meeting_id: str,
        index: int,
        idea_by_id: dict[str, ResearchIdea],
    ) -> dict[str, Any] | None:
        if isinstance(raw_item, str):
            title = self._clean_text(raw_item)
            if not title:
                return None
            return {
                "id": f"{meeting_id}-reading-{index:02d}",
                "meeting_id": meeting_id,
                "idea_id": "unknown",
                "student_name": "unknown",
                "title": title,
                "source_url": "unknown",
                "reason": "unknown",
                "priority": "medium",
            }

        if not isinstance(raw_item, dict):
            return None

        title = self._clean_text(raw_item.get("title") or raw_item.get("paper"))
        if not title:
            return None

        idea_id = self._clean_text(raw_item.get("idea_id"), default="unknown")
        linked_idea = idea_by_id.get(idea_id)
        student_name = self._clean_text(
            raw_item.get("student_name"),
            default=linked_idea.student_name if linked_idea else "unknown",
        )

        return {
            "id": self._clean_text(raw_item.get("id"), default=f"{meeting_id}-reading-{index:02d}"),
            "meeting_id": meeting_id,
            "idea_id": idea_id,
            "student_name": student_name,
            "title": title,
            "source_url": raw_item.get("source_url", "unknown"),
            "reason": raw_item.get("reason", "unknown"),
            "priority": raw_item.get("priority", "medium"),
        }

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
