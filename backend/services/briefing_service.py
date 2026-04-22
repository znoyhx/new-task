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
from backend.services.response_language import ResponseLanguage, is_chinese, localize_text

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
    carryover_tasks: list[ActionItem] = Field(default_factory=list)
    risks: list[BriefingRiskItem] = Field(default_factory=list)
    recommended_agenda: list[BriefingAgendaItem] = Field(default_factory=list)
    focus_questions: list[str] = Field(default_factory=list)


class BriefingService:
    def generate_briefing(
        self,
        project_memory: ProjectMemorySnapshot,
        *,
        output_language: ResponseLanguage = "en",
    ) -> BriefingResult:
        if project_memory.project is None:
            raise ValueError("Project memory must include a project record.")

        latest_meeting = self._pick_latest_meeting(project_memory.meetings)
        latest_meeting_id = latest_meeting.meeting_id if latest_meeting is not None else None

        last_advisor_ideas = self._filter_by_meeting(project_memory.advisor_ideas, latest_meeting_id)
        open_tasks = self._collect_open_tasks(project_memory.action_items)
        carryover_tasks = [
            task
            for task in open_tasks
            if latest_meeting_id is not None and task.meeting_id != latest_meeting_id
        ]
        student_commitments = self._build_student_commitments(
            open_tasks,
            output_language=output_language,
        )
        risks = self._collect_risks(
            project_memory,
            latest_meeting_id,
            output_language=output_language,
        )
        recommended_agenda = self._build_recommended_agenda(
            open_tasks=open_tasks,
            risks=risks,
            last_advisor_ideas=last_advisor_ideas,
            claims=project_memory.claims,
            output_language=output_language,
        )
        focus_questions = self._build_focus_questions(
            last_advisor_ideas=last_advisor_ideas,
            open_tasks=open_tasks,
            risks=risks,
            claims=project_memory.claims,
            output_language=output_language,
        )
        summary = self._build_summary(
            latest_meeting=latest_meeting,
            open_tasks=open_tasks,
            carryover_tasks=carryover_tasks,
            risks=risks,
            last_advisor_ideas=last_advisor_ideas,
            output_language=output_language,
        )

        return BriefingResult(
            project_id=project_memory.project.project_id,
            project_name=project_memory.project.name,
            latest_meeting=latest_meeting,
            summary=summary,
            last_advisor_ideas=last_advisor_ideas[:4],
            student_commitments=student_commitments,
            open_tasks=open_tasks[:6],
            carryover_tasks=carryover_tasks[:6],
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
        *,
        output_language: ResponseLanguage,
    ) -> list[BriefingStudentCommitment]:
        grouped: dict[str, list[str]] = {}
        for task in open_tasks:
            student_name = (task.student_name or task.owner or "Unknown").strip() or "Unknown"
            grouped.setdefault(student_name, [])
            grouped[student_name].append(
                localize_text(
                    output_language,
                    zh=f"{task.title}（状态 {task.status}，截止 {task.deadline}，负责人 {task.owner}）",
                    en=f"{task.title} ({task.status}, due {task.deadline}, owner {task.owner})",
                )
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
        *,
        output_language: ResponseLanguage,
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
                        detail=localize_text(
                            output_language,
                            zh="来自最近一次 progress snapshot 的未解决 blocker。",
                            en="Open blocker from the latest progress snapshot.",
                        ),
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
                    detail=localize_text(
                        output_language,
                        zh="这条 claim 目前仍缺少决定性证据。",
                        en="This claim still lacks decisive evidence.",
                    ),
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
        output_language: ResponseLanguage,
    ) -> list[BriefingAgendaItem]:
        agenda: list[BriefingAgendaItem] = []

        if risks:
            top_risk = risks[0]
            agenda.append(
                BriefingAgendaItem(
                    title=localize_text(
                        output_language,
                        zh=f"优先处理最高风险：{top_risk.title}",
                        en=f"Address the top risk: {top_risk.title}",
                    ),
                    reason=top_risk.detail or localize_text(
                        output_language,
                        zh="这是当前优先级最高的未解决风险。",
                        en="This is the highest-priority unresolved risk.",
                    ),
                    priority="high" if top_risk.level == "high" else "medium",
                )
            )

        if open_tasks:
            top_task = open_tasks[0]
            agenda.append(
                BriefingAgendaItem(
                    title=localize_text(
                        output_language,
                        zh=f"检查任务进展：{top_task.title}",
                        en=f"Review progress on {top_task.title}",
                    ),
                    reason=localize_text(
                        output_language,
                        zh=f"未完成任务，负责人 {top_task.owner}，截止时间 {top_task.deadline}。",
                        en=f"Open task owned by {top_task.owner} with due date {top_task.deadline}.",
                    ),
                    priority="high" if top_task.priority == "high" else "medium",
                )
            )

        if last_advisor_ideas:
            top_idea = last_advisor_ideas[0]
            agenda.append(
                BriefingAgendaItem(
                    title=localize_text(
                        output_language,
                        zh=f"核验导师 idea：{top_idea.idea_text}",
                        en=f"Validate advisor idea: {top_idea.idea_text}",
                    ),
                    reason=top_idea.expected_validation,
                    priority="medium",
                )
            )

        pending_claims = [claim for claim in claims if claim.verification_status == "needs_verification"]
        if pending_claims:
            agenda.append(
                BriefingAgendaItem(
                    title=localize_text(
                        output_language,
                        zh="决定这条未完成 claim 是否需要证据跟进",
                        en="Decide whether the open claim needs evidence follow-up",
                    ),
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
        output_language: ResponseLanguage,
    ) -> list[str]:
        questions: list[str] = []

        if last_advisor_ideas:
            first_idea = last_advisor_ideas[0]
            questions.append(
                localize_text(
                    output_language,
                    zh=f"'{first_idea.idea_text}' 的最快验证路径是什么？",
                    en=f"What is the fastest validation path for '{first_idea.idea_text}'?",
                )
            )

        if open_tasks:
            first_task = open_tasks[0]
            questions.append(
                localize_text(
                    output_language,
                    zh=f"{first_task.owner} 能否在 {first_task.deadline} 前完成 '{first_task.title}'？",
                    en=f"Can {first_task.owner} close '{first_task.title}' before {first_task.deadline}?",
                )
            )

        if risks:
            questions.append(
                localize_text(
                    output_language,
                    zh=f"针对风险 '{risks[0].title}'，当前有什么缓解方案？",
                    en=f"What mitigation is in place for the risk '{risks[0].title}'?",
                )
            )

        pending_claims = [claim for claim in claims if claim.verification_status == "needs_verification"]
        if pending_claims:
            questions.append(
                localize_text(
                    output_language,
                    zh=f"我们是否需要为 claim '{pending_claims[0].text}' 补充证据？",
                    en=f"Do we need evidence support for the claim '{pending_claims[0].text}'?",
                )
            )

        return questions

    def _build_summary(
        self,
        *,
        latest_meeting: ProjectMeetingRecord | None,
        open_tasks: list[ActionItem],
        carryover_tasks: list[ActionItem],
        risks: list[BriefingRiskItem],
        last_advisor_ideas: list[ResearchIdea],
        output_language: ResponseLanguage,
    ) -> str:
        meeting_text = latest_meeting.title if latest_meeting is not None else (
            "最新一次组会" if is_chinese(output_language) else "the latest meeting"
        )
        return localize_text(
            output_language,
            zh=(
                f"{meeting_text} 的 briefing：当前有 {len(open_tasks)} 个未完成任务，"
                f"{len(risks)} 个跟踪风险，{len(last_advisor_ideas)} 条近期导师 idea 需要跟进，"
                f"其中 {len(carryover_tasks)} 个任务是从更早的组会延续下来的。"
            ),
            en=(
                f"Briefing for {meeting_text}: "
                f"{len(open_tasks)} open tasks, {len(risks)} tracked risks, "
                f"{len(last_advisor_ideas)} recent advisor ideas need follow-up, "
                f"and {len(carryover_tasks)} task(s) are being carried over from earlier meetings."
            ),
        )
