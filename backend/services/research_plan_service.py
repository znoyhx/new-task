from __future__ import annotations

from typing import Any, Literal, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.adapters.deepseek_client import DeepSeekClient
from backend.schemas.meeting import ParsedTranscript
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot
from backend.services.response_language import ResponseLanguage, build_json_output_language_instruction

ResearchPlanPriority = Literal["low", "medium", "high"]


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


class ResearchPlanTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str | None = None
    idea_id: str = "unknown"
    student_name: str = "unknown"
    title: str
    owner: str = "unknown"
    due_date: str = "unknown"
    priority: ResearchPlanPriority = "medium"
    success_metrics: list[str] = Field(default_factory=list)
    dependency_note: str = "unknown"
    rationale: str = "unknown"

    @field_validator("idea_id", "student_name", "owner", "due_date", "dependency_note", "rationale", mode="before")
    @classmethod
    def default_unknown(cls, value: object) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        return text or "unknown"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> ResearchPlanPriority:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"critical", "urgent", "p0"}:
            return "high"
        if normalized in {"normal", "default", "p2"}:
            return "medium"
        if normalized in {"minor", "optional", "p3"}:
            return "low"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized

    @field_validator("success_metrics", mode="before")
    @classmethod
    def coerce_success_metrics(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            metrics: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    metrics.append(text)
            return metrics
        text = str(value).strip()
        return [text] if text else []


class ResearchPlanResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    summary: str = ""
    tasks: list[ResearchPlanTask] = Field(default_factory=list)
    questions_to_answer: list[str] = Field(default_factory=list)

    @field_validator("questions_to_answer", mode="before")
    @classmethod
    def coerce_questions(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            questions: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    questions.append(text)
            return questions
        text = str(value).strip()
        return [text] if text else []


class ResearchPlanError(RuntimeError):
    """Raised when next-week research plan generation cannot complete."""


class ResearchPlanService:
    base_system_prompt = (
        "You turn advisor ideas and current blockers into a concrete next-week research plan. "
        "Return JSON only and never wrap the answer in markdown."
    )

    def __init__(self, client: ChatJsonClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def generate_plan(
        self,
        transcript: ParsedTranscript,
        ideas: Sequence[ResearchIdea],
        *,
        progress: MeetingProgressSnapshot | None = None,
        meeting_id: str | None = None,
        output_language: ResponseLanguage = "en",
    ) -> ResearchPlanResult:
        resolved_meeting_id = meeting_id or transcript.meeting_id
        if not resolved_meeting_id:
            raise ResearchPlanError("meeting_id is required for research plan generation.")
        if not transcript.chunks:
            raise ResearchPlanError("Cannot generate a research plan from an empty transcript.")
        if not ideas:
            raise ResearchPlanError("At least one advisor idea is required to generate a research plan.")

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
                f"| expected_validation={idea.expected_validation} | metrics={metrics}"
            )

        progress_lines: list[str] = []
        if progress is not None:
            for student in progress.student_progress:
                blockers = ", ".join(student.blockers) or "none"
                progress_lines.append(
                    f"- {student.student_name}: current_result={student.current_result}; blockers={blockers}"
                )

        return (
            "Turn the advisor ideas and current blockers into a concrete plan for the next seven days.\n\n"
            "Return one JSON object with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "tasks": [\n'
            "    {\n"
            '      "idea_id": "string or unknown",\n'
            '      "student_name": "string or unknown",\n'
            '      "title": "string",\n'
            '      "owner": "string or unknown",\n'
            '      "due_date": "string or unknown",\n'
            '      "priority": "low | medium | high",\n'
            '      "success_metrics": ["string"],\n'
            '      "dependency_note": "string or unknown",\n'
            '      "rationale": "string or unknown"\n'
            "    }\n"
            "  ],\n"
            '  "questions_to_answer": ["string"]\n'
            "}\n\n"
            "Rules:\n"
            "- Focus only on the next week, not long-term roadmap items.\n"
            "- Each task must be observable and actionable.\n"
            "- Success metrics should be measurable outputs, not vague aspirations.\n"
            "- If owner or due date is not stated in the meeting, use the literal string 'unknown'.\n"
            "- Prefer tasks that directly resolve blockers or validate an advisor idea.\n\n"
            f"Output language: {build_json_output_language_instruction(output_language)}\n\n"
            "Advisor ideas:\n"
            f"{chr(10).join(idea_lines)}\n\n"
            "Current progress and blockers:\n"
            f"{chr(10).join(progress_lines) if progress_lines else '- none'}\n\n"
            "Transcript:\n"
            f"{chr(10).join(transcript_lines)}"
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        meeting_id: str,
        ideas: Sequence[ResearchIdea],
    ) -> ResearchPlanResult:
        summary = self._clean_text(payload.get("summary"))
        raw_tasks = payload.get("tasks") or payload.get("plan") or payload.get("action_items") or []
        idea_by_id = {
            idea.id: idea
            for idea in ideas
            if idea.id
        }
        tasks: list[ResearchPlanTask] = []

        for index, raw_task in enumerate(self._ensure_list(raw_tasks), start=1):
            normalized = self._normalize_task(
                raw_task,
                meeting_id=meeting_id,
                index=index,
                idea_by_id=idea_by_id,
            )
            if normalized is None:
                continue
            tasks.append(ResearchPlanTask.model_validate(normalized))

        return ResearchPlanResult(
            meeting_id=meeting_id,
            summary=summary,
            tasks=tasks,
            questions_to_answer=payload.get("questions_to_answer") or payload.get("next_meeting_questions") or [],
        )

    def _normalize_task(
        self,
        raw_task: object,
        *,
        meeting_id: str,
        index: int,
        idea_by_id: dict[str, ResearchIdea],
    ) -> dict[str, Any] | None:
        if isinstance(raw_task, str):
            title = self._clean_text(raw_task)
            if not title:
                return None
            return {
                "meeting_id": meeting_id,
                "idea_id": "unknown",
                "student_name": "unknown",
                "title": title,
                "owner": "unknown",
                "due_date": "unknown",
                "priority": "medium",
                "success_metrics": [],
                "dependency_note": "unknown",
                "rationale": "unknown",
            }

        if not isinstance(raw_task, dict):
            return None

        title = self._clean_text(raw_task.get("title") or raw_task.get("task"))
        if not title:
            return None

        idea_id = self._clean_text(raw_task.get("idea_id"), default="unknown")
        linked_idea = idea_by_id.get(idea_id)
        success_metrics = self._ensure_text_list(raw_task.get("success_metrics"))
        if not success_metrics and linked_idea is not None:
            success_metrics = linked_idea.validation_metrics

        return {
            "meeting_id": meeting_id,
            "idea_id": idea_id,
            "student_name": self._clean_text(
                raw_task.get("student_name"),
                default=linked_idea.student_name if linked_idea else "unknown",
            ),
            "title": title,
            "owner": raw_task.get("owner", "unknown"),
            "due_date": raw_task.get("due_date") or raw_task.get("deadline") or "unknown",
            "priority": raw_task.get("priority", "medium"),
            "success_metrics": success_metrics,
            "dependency_note": raw_task.get("dependency_note") or raw_task.get("depends_on") or "unknown",
            "rationale": raw_task.get("rationale") or raw_task.get("reason") or "unknown",
        }

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
