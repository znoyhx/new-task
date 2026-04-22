from __future__ import annotations

from typing import Any, Protocol

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.meeting import ParsedTranscript
from backend.schemas.reading_recommendation import ReadingRecommendation
from backend.schemas.research_idea import (
    AdvisorIdeaCaptureResult,
    IdeaNextAction,
    ResearchIdea,
)
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


class IdeaCaptureError(RuntimeError):
    """Raised when advisor idea capture cannot complete."""


class IdeaCaptureService:
    base_system_prompt = (
        "You extract advisor research ideas from a research-group meeting transcript. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(self, client: ChatJsonClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def capture_ideas(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
        output_language: ResponseLanguage = "en",
    ) -> AdvisorIdeaCaptureResult:
        resolved_meeting_id = meeting_id or transcript.meeting_id
        if not resolved_meeting_id:
            raise IdeaCaptureError("meeting_id is required for advisor idea capture.")
        if not transcript.chunks:
            raise IdeaCaptureError("Cannot capture advisor ideas from an empty transcript.")

        payload = self.client.chat_json(
            self._build_prompt(transcript, output_language=output_language),
            system_prompt=self._build_system_prompt(output_language),
            temperature=0.0,
            timeout=60.0,
        )
        return self._normalize_payload(payload, meeting_id=resolved_meeting_id)

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

        transcript_block = "\n".join(transcript_lines)
        return (
            "Read the following research-group meeting transcript and extract only the advisor or PI ideas "
            "that should drive next week's research work.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "ideas": [\n'
            "    {\n"
            '      "student_name": "string or unknown",\n'
            '      "idea_text": "string",\n'
            '      "suggested_by": "string",\n'
            '      "expected_validation": "string or unknown",\n'
            '      "status": "proposed | planned | validated | deferred | unknown",\n'
            '      "validation_metrics": ["string"],\n'
            '      "next_actions": [\n'
            "        {\n"
            '          "title": "string",\n'
            '          "owner": "string or unknown",\n'
            '          "due_date": "string or unknown",\n'
            '          "priority": "low | medium | high",\n'
            '          "rationale": "string or unknown"\n'
            "        }\n"
            "      ],\n"
            '      "recommended_reading": [\n'
            "        {\n"
            '          "title": "string",\n'
            '          "source_url": "string or unknown",\n'
            '          "reason": "string",\n'
            '          "priority": "low | medium | high"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Capture only advisor, PI, or mentor suggestions, not ordinary student status updates.\n"
            "- Each idea must be actionable for next week.\n"
            "- If the transcript does not specify an owner or due date, use the literal string 'unknown'.\n"
            "- Every idea must include next_actions, recommended_reading, and validation_metrics keys. Use empty lists if needed.\n"
            "- Do not invent references. Use 'unknown' when you are not confident about a URL.\n\n"
            f"Output language: {build_json_output_language_instruction(output_language)}\n\n"
            "Transcript:\n"
            f"{transcript_block}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        meeting_id: str,
    ) -> AdvisorIdeaCaptureResult:
        summary = self._clean_text(payload.get("summary"))
        raw_ideas = payload.get("ideas") or payload.get("advisor_ideas") or payload.get("items") or []
        ideas: list[ResearchIdea] = []

        for index, raw_idea in enumerate(self._ensure_list(raw_ideas), start=1):
            normalized = self._normalize_idea(raw_idea, meeting_id=meeting_id, index=index)
            if normalized is None:
                continue
            ideas.append(ResearchIdea.model_validate(normalized))

        return AdvisorIdeaCaptureResult(
            meeting_id=meeting_id,
            summary=summary,
            ideas=ideas,
        )

    def _normalize_idea(
        self,
        raw_idea: object,
        *,
        meeting_id: str,
        index: int,
    ) -> dict[str, Any] | None:
        if isinstance(raw_idea, str):
            idea_text = self._clean_text(raw_idea)
            if not idea_text:
                return None
            idea_id = f"{meeting_id}-idea-{index:02d}"
            return {
                "id": idea_id,
                "meeting_id": meeting_id,
                "student_name": "unknown",
                "idea_text": idea_text,
                "suggested_by": "advisor",
                "expected_validation": "unknown",
                "status": "proposed",
                "validation_metrics": [],
                "next_actions": [],
                "recommended_reading": [],
            }

        if not isinstance(raw_idea, dict):
            return None

        idea_text = self._clean_text(
            raw_idea.get("idea_text")
            or raw_idea.get("idea")
            or raw_idea.get("hypothesis")
            or raw_idea.get("suggestion")
        )
        if not idea_text:
            return None

        idea_id = self._clean_text(raw_idea.get("id"), default=f"{meeting_id}-idea-{index:02d}")
        expected_validation = self._clean_text(
            raw_idea.get("expected_validation") or raw_idea.get("validation_goal"),
            default="unknown",
        )
        validation_metrics = self._ensure_text_list(raw_idea.get("validation_metrics"))
        if not validation_metrics and expected_validation != "unknown":
            validation_metrics = [expected_validation]

        student_name = self._clean_text(
            raw_idea.get("student_name") or raw_idea.get("target_student"),
            default="unknown",
        )
        recommended_reading = self._normalize_recommended_reading(
            raw_idea.get("recommended_reading")
            or raw_idea.get("reading_recommendations")
            or raw_idea.get("reading_list"),
            meeting_id=meeting_id,
            idea_id=idea_id,
            student_name=student_name,
        )
        next_actions = self._normalize_next_actions(raw_idea.get("next_actions"))

        return {
            "id": idea_id,
            "meeting_id": meeting_id,
            "student_name": student_name,
            "idea_text": idea_text,
            "suggested_by": self._clean_text(
                raw_idea.get("suggested_by") or raw_idea.get("speaker"),
                default="advisor",
            ),
            "expected_validation": expected_validation,
            "status": raw_idea.get("status", "proposed"),
            "validation_metrics": validation_metrics,
            "next_actions": [item.model_dump(mode="json") for item in next_actions],
            "recommended_reading": [
                item.model_dump(mode="json")
                for item in recommended_reading
            ],
        }

    def _normalize_next_actions(self, raw_actions: object) -> list[IdeaNextAction]:
        next_actions: list[IdeaNextAction] = []
        for raw_action in self._ensure_list(raw_actions):
            if isinstance(raw_action, str):
                title = self._clean_text(raw_action)
                if not title:
                    continue
                next_actions.append(IdeaNextAction(title=title))
                continue

            if not isinstance(raw_action, dict):
                continue

            title = self._clean_text(raw_action.get("title") or raw_action.get("task"))
            if not title:
                continue

            next_actions.append(
                IdeaNextAction(
                    title=title,
                    owner=raw_action.get("owner", "unknown"),
                    due_date=raw_action.get("due_date") or raw_action.get("deadline") or "unknown",
                    priority=raw_action.get("priority", "medium"),
                    rationale=raw_action.get("rationale") or raw_action.get("reason") or "unknown",
                )
            )
        return next_actions

    def _normalize_recommended_reading(
        self,
        raw_items: object,
        *,
        meeting_id: str,
        idea_id: str,
        student_name: str,
    ) -> list[ReadingRecommendation]:
        recommendations: list[ReadingRecommendation] = []
        for index, raw_item in enumerate(self._ensure_list(raw_items), start=1):
            if isinstance(raw_item, str):
                title = self._clean_text(raw_item)
                if not title:
                    continue
                recommendations.append(
                    ReadingRecommendation(
                        id=f"{idea_id}-reading-{index:02d}",
                        meeting_id=meeting_id,
                        idea_id=idea_id,
                        student_name=student_name,
                        title=title,
                    )
                )
                continue

            if not isinstance(raw_item, dict):
                continue

            title = self._clean_text(raw_item.get("title") or raw_item.get("paper"))
            if not title:
                continue

            recommendations.append(
                ReadingRecommendation(
                    id=self._clean_text(
                        raw_item.get("id"),
                        default=f"{idea_id}-reading-{index:02d}",
                    ),
                    meeting_id=meeting_id,
                    idea_id=idea_id,
                    student_name=student_name,
                    title=title,
                    source_url=raw_item.get("source_url", "unknown"),
                    reason=raw_item.get("reason", "unknown"),
                    priority=raw_item.get("priority", "medium"),
                )
            )
        return recommendations

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
