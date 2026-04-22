from __future__ import annotations

from typing import Any, Protocol

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.action_item import ActionItem
from backend.schemas.meeting import ParsedTranscript
from backend.schemas.risk import Risk
from backend.schemas.student_progress import MeetingProgressSnapshot, StudentProgress
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


class ProgressExtractionError(RuntimeError):
    """Raised when weekly progress extraction cannot complete."""


class ProgressExtractionService:
    base_system_prompt = (
        "You extract weekly research-group progress from a meeting transcript. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(self, client: ChatJsonClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def extract_progress(
        self,
        transcript: ParsedTranscript,
        *,
        meeting_id: str | None = None,
        output_language: ResponseLanguage = "en",
    ) -> MeetingProgressSnapshot:
        resolved_meeting_id = meeting_id or transcript.meeting_id
        if not resolved_meeting_id:
            raise ProgressExtractionError("meeting_id is required for progress extraction.")
        if not transcript.chunks:
            raise ProgressExtractionError("Cannot extract progress from an empty transcript.")

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
            "Read the following research-group meeting transcript and extract structured weekly progress.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "student_progress": [\n'
            "    {\n"
            '      "student_name": "string",\n'
            '      "completed_work": ["string"],\n'
            '      "current_result": "string",\n'
            '      "blockers": ["string"],\n'
            '      "risks": [\n'
            "        {\n"
            '          "title": "string",\n'
            '          "level": "low | medium | high",\n'
            '          "description": "string",\n'
            '          "owner": "string or unknown",\n'
            '          "mitigation": "string or unknown"\n'
            "        }\n"
            "      ],\n"
            '      "unresolved_questions": ["string"],\n'
            '      "next_step_suggestion": "string",\n'
            '      "action_items": [\n'
            "        {\n"
            '          "title": "string",\n'
            '          "owner": "string or unknown",\n'
            '          "deadline": "string or unknown",\n'
            '          "priority": "low | medium | high",\n'
            '          "status": "open | in_progress | blocked | done | unknown",\n'
            '          "dependency_note": "string or unknown"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Focus on students or reporting members, not the advisor.\n"
            "- If owner or deadline is missing, use the literal string 'unknown'.\n"
            "- Do not invent details that are not supported by the transcript.\n"
            "- Keep lists empty instead of hallucinating.\n\n"
            f"Output language: {build_json_output_language_instruction(output_language)}\n\n"
            "Transcript:\n"
            f"{transcript_block}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        meeting_id: str,
    ) -> MeetingProgressSnapshot:
        summary = self._clean_text(payload.get("summary"))
        raw_students = (
            payload.get("student_progress")
            or payload.get("students")
            or payload.get("progress")
            or []
        )

        student_progress: list[StudentProgress] = []
        action_items: list[ActionItem] = []

        for raw_student in self._ensure_list(raw_students):
            normalized_student = self._normalize_student(raw_student, meeting_id=meeting_id)
            if normalized_student is None:
                continue

            student = StudentProgress.model_validate(normalized_student)
            student_progress.append(student)
            for action_item in student.action_items:
                action_items.append(
                    action_item.model_copy(
                        update={
                            "meeting_id": meeting_id,
                            "student_name": student.student_name,
                        }
                    )
                )

        return MeetingProgressSnapshot(
            meeting_id=meeting_id,
            summary=summary,
            student_progress=student_progress,
            action_items=action_items,
        )

    def _normalize_student(
        self,
        raw_student: object,
        *,
        meeting_id: str,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_student, dict):
            return None

        student_name = self._clean_text(raw_student.get("student_name") or raw_student.get("name"))
        if not student_name:
            return None

        risks = self._normalize_risks(
            raw_student.get("risks"),
            meeting_id=meeting_id,
            student_name=student_name,
        )
        action_items = self._normalize_action_items(
            raw_student.get("action_items"),
            meeting_id=meeting_id,
            student_name=student_name,
        )

        return {
            "meeting_id": meeting_id,
            "student_name": student_name,
            "completed_work": self._ensure_text_list(raw_student.get("completed_work")),
            "current_result": self._clean_text(raw_student.get("current_result"), default="unknown"),
            "blockers": self._ensure_text_list(raw_student.get("blockers")),
            "risks": [risk.model_dump(mode="json") for risk in risks],
            "unresolved_questions": self._ensure_text_list(raw_student.get("unresolved_questions")),
            "next_step_suggestion": self._clean_text(
                raw_student.get("next_step_suggestion") or raw_student.get("next_step"),
                default="unknown",
            ),
            "action_items": [item.model_dump(mode="json") for item in action_items],
        }

    def _normalize_risks(
        self,
        raw_risks: object,
        *,
        meeting_id: str,
        student_name: str,
    ) -> list[Risk]:
        risks: list[Risk] = []
        for raw_risk in self._ensure_list(raw_risks):
            if isinstance(raw_risk, str):
                title = self._clean_text(raw_risk)
                if not title:
                    continue
                risks.append(
                    Risk(
                        meeting_id=meeting_id,
                        student_name=student_name,
                        title=title,
                    )
                )
                continue

            if not isinstance(raw_risk, dict):
                continue

            title = self._clean_text(raw_risk.get("title") or raw_risk.get("risk"))
            description = self._clean_text(raw_risk.get("description"))
            if not title:
                title = description
            if not title:
                continue

            risks.append(
                Risk(
                    meeting_id=meeting_id,
                    student_name=student_name,
                    title=title,
                    level=raw_risk.get("level", "medium"),
                    description=description,
                    owner=raw_risk.get("owner", "unknown"),
                    mitigation=raw_risk.get("mitigation", "unknown"),
                )
            )
        return risks

    def _normalize_action_items(
        self,
        raw_action_items: object,
        *,
        meeting_id: str,
        student_name: str,
    ) -> list[ActionItem]:
        action_items: list[ActionItem] = []
        for raw_item in self._ensure_list(raw_action_items):
            if isinstance(raw_item, str):
                title = self._clean_text(raw_item)
                if not title:
                    continue
                action_items.append(
                    ActionItem(
                        meeting_id=meeting_id,
                        student_name=student_name,
                        title=title,
                    )
                )
                continue

            if not isinstance(raw_item, dict):
                continue

            title = self._clean_text(raw_item.get("title") or raw_item.get("task"))
            if not title:
                continue

            action_items.append(
                ActionItem(
                    meeting_id=meeting_id,
                    student_name=student_name,
                    title=title,
                    owner=raw_item.get("owner", "unknown"),
                    deadline=raw_item.get("deadline", "unknown"),
                    priority=raw_item.get("priority", "medium"),
                    status=raw_item.get("status", "open"),
                    dependency_note=raw_item.get("dependency_note", "unknown"),
                )
            )
        return action_items

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
