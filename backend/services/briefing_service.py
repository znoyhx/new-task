from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.project_memory import (
    ProjectMeetingRecord,
    ProjectMemorySnapshot,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.risk import Risk

AgendaPriority = Literal["high", "medium", "low"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class BriefingStudentCommitment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    student_name: str
    commitments: list[str] = Field(default_factory=list)


class BriefingRiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    level: str = "medium"
    owner: str = "unknown"
    detail: str = ""

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: object) -> str:
        normalized = str(value or "medium").strip().lower()
        if normalized in {"critical", "urgent"}:
            return "high"
        if normalized not in {"low", "medium", "high"}:
            return "medium"
        return normalized


class BriefingAgendaItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    reason: str
    priority: AgendaPriority = "medium"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> AgendaPriority:
        normalized = str(value or "medium").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            return "medium"
        return normalized


class BriefingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str
    project_name: str = "Unknown project"
    generated_at: datetime = Field(default_factory=utcnow)
    latest_meeting: ProjectMeetingRecord | None = None
    summary: str = ""
    last_advisor_ideas: list[ResearchIdea] = Field(default_factory=list)
    student_commitments: list[BriefingStudentCommitment] = Field(default_factory=list)
    open_tasks: list[ActionItem] = Field(default_factory=list)
    risks: list[BriefingRiskItem] = Field(default_factory=list)
    recommended_agenda: list[BriefingAgendaItem] = Field(default_factory=list)
    focus_questions: list[str] = Field(default_factory=list)


class BriefingService:
    def generate_briefing(self, project_memory: ProjectMemorySnapshot) -> BriefingResult:
        if project_memory.project is None:
            raise ValueError("Project memory must include a project record.")

        latest_meeting = self._pick_latest_meeting(project_memory.meetings)
        latest_meeting_id = latest_meeting.meeting_id if latest_meeting is not None else None

        last_advisor_ideas = self._filter_by_meeting(project_memory.advisor_ideas, latest_meeting_id)
        open_tasks = self._collect_open_tasks(project_memory.action_items)
        student_commitments = self._build_student_commitments(open_tasks)
        risks = self._collect_risks(project_memory, latest_meeting_id)
        recommended_agenda = self._build_recommended_agenda(
            open_tasks=open_tasks,
            risks=risks,
            last_advisor_ideas=last_advisor_ideas,
            claims=project_memory.claims,
        )
        focus_questions = self._build_focus_questions(
            last_advisor_ideas=last_advisor_ideas,
            open_tasks=open_tasks,
            risks=risks,
            claims=project_memory.claims,
        )
        summary = self._build_summary(
            latest_meeting=latest_meeting,
            open_tasks=open_tasks,
            risks=risks,
            last_advisor_ideas=last_advisor_ideas,
        )

        return BriefingResult(
            project_id=project_memory.project.project_id,
            project_name=project_memory.project.name,
            latest_meeting=latest_meeting,
            summary=summary,
            last_advisor_ideas=last_advisor_ideas[:4],
            student_commitments=student_commitments,
            open_tasks=open_tasks[:6],
            risks=risks[:6],
            recommended_agenda=recommended_agenda[:6],
            focus_questions=focus_questions[:6],
        )

    def _pick_latest_meeting(
        self,
        meetings: list[ProjectMeetingRecord],
    ) -> ProjectMeetingRecord | None:
        if not meetings:
            return None
        return sorted(meetings, key=lambda meeting: (meeting.created_at, meeting.meeting_id))[-1]

    def _filter_by_meeting(self, items: list[object], meeting_id: str | None) -> list[object]:
        if meeting_id is None:
            return list(items)
        return [item for item in items if getattr(item, "meeting_id", None) == meeting_id]

    def _collect_open_tasks(self, action_items: list[ActionItem]) -> list[ActionItem]:
        priority_order = {"high": 0, "medium": 1, "low": 2}
        open_tasks = [
            item for item in action_items
            if item.status not in {"done"}
        ]
        return sorted(
            open_tasks,
            key=lambda item: (
                priority_order.get(item.priority, 3),
                item.deadline,
                item.title,
            ),
        )

    def _build_student_commitments(
        self,
        open_tasks: list[ActionItem],
    ) -> list[BriefingStudentCommitment]:
        grouped: dict[str, list[str]] = {}
        for task in open_tasks:
            student_name = (task.student_name or task.owner or "Unknown").strip() or "Unknown"
            grouped.setdefault(student_name, [])
            grouped[student_name].append(
                f"{task.title} ({task.status}, due {task.deadline}, owner {task.owner})"
            )

        commitments: list[BriefingStudentCommitment] = []
        for student_name in sorted(grouped):
            commitments.append(
                BriefingStudentCommitment(
                    student_name=student_name,
                    commitments=grouped[student_name][:4],
                )
            )
        return commitments

    def _collect_risks(
        self,
        project_memory: ProjectMemorySnapshot,
        latest_meeting_id: str | None,
    ) -> list[BriefingRiskItem]:
        risks: list[BriefingRiskItem] = []
        seen_titles: set[str] = set()

        for progress in self._filter_by_meeting(project_memory.student_progress, latest_meeting_id):
            for risk in progress.risks:
                if risk.title in seen_titles:
                    continue
                risks.append(
                    BriefingRiskItem(
                        title=risk.title,
                        level=risk.level,
                        owner=risk.owner,
                        detail=risk.description or risk.mitigation,
                    )
                )
                seen_titles.add(risk.title)

            for blocker in progress.blockers:
                blocker_title = f"{progress.student_name}: {blocker}"
                if blocker_title in seen_titles:
                    continue
                risks.append(
                    BriefingRiskItem(
                        title=blocker_title,
                        level="medium",
                        owner=progress.student_name,
                        detail="Open blocker from the latest progress snapshot.",
                    )
                )
                seen_titles.add(blocker_title)

        for claim in self._filter_by_meeting(project_memory.claims, latest_meeting_id):
            if claim.verification_status != "needs_verification":
                continue
            if claim.text in seen_titles:
                continue
            risks.append(
                BriefingRiskItem(
                    title=claim.text,
                    level="medium",
                    owner=claim.speaker,
                    detail="This claim still lacks decisive evidence.",
                )
            )
            seen_titles.add(claim.text)

        level_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(risks, key=lambda risk: (level_order.get(risk.level, 3), risk.title))

    def _build_recommended_agenda(
        self,
        *,
        open_tasks: list[ActionItem],
        risks: list[BriefingRiskItem],
        last_advisor_ideas: list[ResearchIdea],
        claims: list[Claim],
    ) -> list[BriefingAgendaItem]:
        agenda: list[BriefingAgendaItem] = []

        if risks:
            top_risk = risks[0]
            agenda.append(
                BriefingAgendaItem(
                    title=f"Address the top risk: {top_risk.title}",
                    reason=top_risk.detail or "This is the highest-priority unresolved risk.",
                    priority="high" if top_risk.level == "high" else "medium",
                )
            )

        if open_tasks:
            top_task = open_tasks[0]
            agenda.append(
                BriefingAgendaItem(
                    title=f"Review progress on {top_task.title}",
                    reason=f"Open task owned by {top_task.owner} with due date {top_task.deadline}.",
                    priority="high" if top_task.priority == "high" else "medium",
                )
            )

        if last_advisor_ideas:
            top_idea = last_advisor_ideas[0]
            agenda.append(
                BriefingAgendaItem(
                    title=f"Validate advisor idea: {top_idea.idea_text}",
                    reason=top_idea.expected_validation,
                    priority="medium",
                )
            )

        pending_claims = [claim for claim in claims if claim.verification_status == "needs_verification"]
        if pending_claims:
            agenda.append(
                BriefingAgendaItem(
                    title="Decide whether the open claim needs evidence follow-up",
                    reason=pending_claims[0].text,
                    priority="medium",
                )
            )

        return agenda

    def _build_focus_questions(
        self,
        *,
        last_advisor_ideas: list[ResearchIdea],
        open_tasks: list[ActionItem],
        risks: list[BriefingRiskItem],
        claims: list[Claim],
    ) -> list[str]:
        questions: list[str] = []

        if last_advisor_ideas:
            first_idea = last_advisor_ideas[0]
            questions.append(
                f"What is the fastest validation path for '{first_idea.idea_text}'?"
            )

        if open_tasks:
            first_task = open_tasks[0]
            questions.append(
                f"Can {first_task.owner} close '{first_task.title}' before {first_task.deadline}?"
            )

        if risks:
            questions.append(
                f"What mitigation is in place for the risk '{risks[0].title}'?"
            )

        pending_claims = [claim for claim in claims if claim.verification_status == "needs_verification"]
        if pending_claims:
            questions.append(
                f"Do we need evidence support for the claim '{pending_claims[0].text}'?"
            )

        return questions

    def _build_summary(
        self,
        *,
        latest_meeting: ProjectMeetingRecord | None,
        open_tasks: list[ActionItem],
        risks: list[BriefingRiskItem],
        last_advisor_ideas: list[ResearchIdea],
    ) -> str:
        meeting_text = latest_meeting.title if latest_meeting is not None else "the latest meeting"
        return (
            f"Briefing for {meeting_text}: "
            f"{len(open_tasks)} open tasks, {len(risks)} tracked risks, "
            f"and {len(last_advisor_ideas)} recent advisor ideas need follow-up."
        )
