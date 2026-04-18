from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.project_memory import ProjectMemorySnapshot
from backend.schemas.reading_recommendation import ReadingRecommendation
from backend.services.briefing_service import BriefingResult

DeliverableType = Literal[
    "weekly_report",
    "next_meeting_briefing",
    "next_week_research_plan",
    "presentation_outline",
]


class DeliverableDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    deliverable_type: DeliverableType
    title: str
    content_markdown: str


class DeliverableBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str
    documents: list[DeliverableDocument] = Field(default_factory=list)


class DeliverableService:
    def generate_deliverable(
        self,
        deliverable_type: DeliverableType,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> DeliverableDocument:
        generators = {
            "weekly_report": self._build_weekly_report,
            "next_meeting_briefing": self._build_next_meeting_briefing,
            "next_week_research_plan": self._build_next_week_research_plan,
            "presentation_outline": self._build_presentation_outline,
        }
        document = generators[deliverable_type](project_memory=project_memory, briefing=briefing)
        return DeliverableDocument(
            deliverable_type=deliverable_type,
            title=document["title"],
            content_markdown=document["content_markdown"],
        )

    def generate_all(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> DeliverableBundle:
        project_id = briefing.project_id
        documents = [
            self.generate_deliverable(
                deliverable_type=deliverable_type,
                project_memory=project_memory,
                briefing=briefing,
            )
            for deliverable_type in (
                "weekly_report",
                "next_meeting_briefing",
                "next_week_research_plan",
                "presentation_outline",
            )
        ]
        return DeliverableBundle(project_id=project_id, documents=documents)

    def _build_weekly_report(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> dict[str, str]:
        latest_meeting = briefing.latest_meeting
        advisor_ideas = briefing.last_advisor_ideas
        open_tasks = briefing.open_tasks
        risks = briefing.risks
        readings = self._collect_readings(project_memory)
        progress_lines = [
            f"- **{progress.student_name}**: {progress.current_result}"
            for progress in project_memory.student_progress
        ]
        idea_lines = [
            f"- {idea.idea_text} ({idea.expected_validation})"
            for idea in advisor_ideas
        ]
        task_lines = [
            f"- {task.title} | owner: {task.owner} | due: {task.deadline} | priority: {task.priority}"
            for task in open_tasks
        ]
        risk_lines = [
            f"- [{risk.level}] {risk.title} ({risk.owner})"
            for risk in risks
        ]
        reading_lines = [
            f"- {reading.title} | {reading.reason}"
            for reading in readings
        ]

        content = "\n".join(
            [
                f"# Weekly Report: {briefing.project_name}",
                "",
                f"## Meeting",
                f"- Title: {latest_meeting.title if latest_meeting else 'Unknown'}",
                f"- Summary: {briefing.summary}",
                "",
                "## Student Progress",
                *(progress_lines or ["- No student progress has been recorded yet."]),
                "",
                "## Advisor Ideas",
                *(idea_lines or ["- No advisor ideas were captured."]),
                "",
                "## Open Tasks",
                *(task_lines or ["- No open tasks remain."]),
                "",
                "## Risks",
                *(risk_lines or ["- No material risks are currently tracked."]),
                "",
                "## Recommended Reading",
                *(reading_lines or ["- No recommended reading is available yet."]),
            ]
        )
        return {
            "title": f"Weekly Report - {briefing.project_name}",
            "content_markdown": content,
        }

    def _build_next_meeting_briefing(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> dict[str, str]:
        commitment_lines = [
            f"- **{commitment.student_name}**: " + "; ".join(commitment.commitments)
            for commitment in briefing.student_commitments
        ]
        agenda_lines = [
            f"- [{item.priority}] {item.title} — {item.reason}"
            for item in briefing.recommended_agenda
        ]
        risk_lines = [
            f"- [{risk.level}] {risk.title} — {risk.detail or 'Needs explicit mitigation.'}"
            for risk in briefing.risks
        ]
        question_lines = [
            f"- {question}"
            for question in briefing.focus_questions
        ]

        content = "\n".join(
            [
                f"# Next Meeting Briefing: {briefing.project_name}",
                "",
                f"## Summary",
                briefing.summary,
                "",
                "## Student Commitments",
                *(commitment_lines or ["- No active commitments are recorded."]),
                "",
                "## Open Tasks",
                *(
                    [
                        f"- {task.title} | owner: {task.owner} | due: {task.deadline} | status: {task.status}"
                        for task in briefing.open_tasks
                    ]
                    or ["- No open tasks remain."]
                ),
                "",
                "## Risks",
                *(risk_lines or ["- No risks are currently tracked."]),
                "",
                "## Recommended Agenda",
                *(agenda_lines or ["- No agenda items were generated."]),
                "",
                "## Focus Questions",
                *(question_lines or ["- No focus questions were generated."]),
            ]
        )
        return {
            "title": f"Briefing - {briefing.project_name}",
            "content_markdown": content,
        }

    def _build_next_week_research_plan(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> dict[str, str]:
        high_priority_tasks = [task for task in briefing.open_tasks if task.priority == "high"]
        readings = self._collect_readings(project_memory)
        content = "\n".join(
            [
                f"# Next-Week Research Plan: {briefing.project_name}",
                "",
                "## Priority Tasks",
                *(
                    [
                        f"- {task.title} | owner: {task.owner} | due: {task.deadline} | metric: {task.dependency_note}"
                        for task in (high_priority_tasks or briefing.open_tasks)
                    ]
                    or ["- No next-week tasks are currently available."]
                ),
                "",
                "## Validation Targets",
                *(
                    [
                        f"- {idea.idea_text} | expected validation: {idea.expected_validation}"
                        for idea in briefing.last_advisor_ideas
                    ]
                    or ["- No advisor validation targets are available."]
                ),
                "",
                "## Recommended Reading",
                *(
                    [
                        f"- {reading.title} | priority: {reading.priority} | {reading.reason}"
                        for reading in readings
                    ]
                    or ["- No recommended reading is available."]
                ),
                "",
                "## Questions To Close Next Week",
                *(
                    [f"- {question}" for question in briefing.focus_questions]
                    or ["- No closing questions are available."]
                ),
            ]
        )
        return {
            "title": f"Next-Week Plan - {briefing.project_name}",
            "content_markdown": content,
        }

    def _build_presentation_outline(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
    ) -> dict[str, str]:
        content = "\n".join(
            [
                f"# Presentation Outline: {briefing.project_name}",
                "",
                "## 1. What happened this week",
                f"- {briefing.summary}",
                "",
                "## 2. Student progress worth highlighting",
                *(
                    [
                        f"- {progress.student_name}: {progress.current_result}"
                        for progress in project_memory.student_progress
                    ]
                    or ["- No student progress is available."]
                ),
                "",
                "## 3. Advisor ideas and validation path",
                *(
                    [
                        f"- {idea.idea_text} | validation: {idea.expected_validation}"
                        for idea in briefing.last_advisor_ideas
                    ]
                    or ["- No advisor ideas are available."]
                ),
                "",
                "## 4. Risks and blockers",
                *(
                    [
                        f"- [{risk.level}] {risk.title}"
                        for risk in briefing.risks
                    ]
                    or ["- No material risks are available."]
                ),
                "",
                "## 5. Next-week execution plan",
                *(
                    [
                        f"- {task.title} | owner: {task.owner} | due: {task.deadline}"
                        for task in briefing.open_tasks
                    ]
                    or ["- No next-week plan items are available."]
                ),
            ]
        )
        return {
            "title": f"Presentation Outline - {briefing.project_name}",
            "content_markdown": content,
        }

    def _collect_readings(self, project_memory: ProjectMemorySnapshot) -> list[ReadingRecommendation]:
        readings: list[ReadingRecommendation] = []
        seen_titles: set[str] = set()

        for idea in project_memory.advisor_ideas:
            for reading in idea.recommended_reading:
                if reading.title in seen_titles:
                    continue
                readings.append(reading)
                seen_titles.add(reading.title)

        if not readings:
            for paper in project_memory.key_papers:
                if paper.title in seen_titles:
                    continue
                readings.append(
                    ReadingRecommendation(
                        id=paper.id,
                        meeting_id=paper.meeting_id,
                        student_name="unknown",
                        title=paper.title,
                        source_url=paper.source_url,
                        reason=paper.reason,
                        priority="medium",
                    )
                )
                seen_titles.add(paper.title)

        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(readings, key=lambda reading: (priority_order.get(reading.priority, 3), reading.title))
