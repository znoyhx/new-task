from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.project_memory import ProjectMemorySnapshot
from backend.schemas.reading_recommendation import ReadingRecommendation
from backend.services.briefing_service import BriefingResult
from backend.services.response_language import ResponseLanguage, localize_text

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
        output_language: ResponseLanguage = "en",
    ) -> DeliverableDocument:
        generators = {
            "weekly_report": self._build_weekly_report,
            "next_meeting_briefing": self._build_next_meeting_briefing,
            "next_week_research_plan": self._build_next_week_research_plan,
            "presentation_outline": self._build_presentation_outline,
        }
        document = generators[deliverable_type](
            project_memory=project_memory,
            briefing=briefing,
            output_language=output_language,
        )
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
        output_language: ResponseLanguage = "en",
    ) -> DeliverableBundle:
        project_id = briefing.project_id
        documents = [
            self.generate_deliverable(
                deliverable_type=deliverable_type,
                project_memory=project_memory,
                briefing=briefing,
                output_language=output_language,
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
        output_language: ResponseLanguage,
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
        task_lines = [
            localize_text(
                output_language,
                zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline} | 优先级：{task.priority}",
                en=f"- {task.title} | owner: {task.owner} | due: {task.deadline} | priority: {task.priority}",
            )
            for task in open_tasks
        ]
        carryover_lines = [
            localize_text(
                output_language,
                zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline}",
                en=f"- {task.title} | owner: {task.owner} | due: {task.deadline}",
            )
            for task in briefing.carryover_tasks
        ]
        risk_lines = [
            localize_text(
                output_language,
                zh=f"- [{risk.level}] {risk.title}（{risk.owner}）",
                en=f"- [{risk.level}] {risk.title} ({risk.owner})",
            )
            for risk in risks
        ]
        reading_lines = [
            f"- {reading.title} | {reading.reason}"
            for reading in readings
        ]

        content = "\n".join(
            [
                localize_text(
                    output_language,
                    zh=f"# 周报：{briefing.project_name}",
                    en=f"# Weekly Report: {briefing.project_name}",
                ),
                "",
                localize_text(output_language, zh="## 本次组会", en="## Meeting"),
                localize_text(
                    output_language,
                    zh=f"- 标题：{latest_meeting.title if latest_meeting else '未知'}",
                    en=f"- Title: {latest_meeting.title if latest_meeting else 'Unknown'}",
                ),
                localize_text(
                    output_language,
                    zh=f"- 摘要：{briefing.summary}",
                    en=f"- Summary: {briefing.summary}",
                ),
                "",
                localize_text(output_language, zh="## 学生进展", en="## Student Progress"),
                *(progress_lines or [localize_text(output_language, zh="- 暂无学生进展记录。", en="- No student progress has been recorded yet.")]),
                "",
                localize_text(output_language, zh="## 导师 Ideas", en="## Advisor Ideas"),
                *(
                    [
                        f"- {idea.idea_text} ({idea.expected_validation})"
                        for idea in advisor_ideas
                    ]
                    or [localize_text(output_language, zh="- 暂未捕获导师 idea。", en="- No advisor ideas were captured.")]
                ),
                "",
                localize_text(output_language, zh="## 未完成任务", en="## Open Tasks"),
                *(task_lines or [localize_text(output_language, zh="- 当前没有未完成任务。", en="- No open tasks remain.")]),
                "",
                localize_text(output_language, zh="## 历史延续事项", en="## Carryover From Earlier Meetings"),
                *(carryover_lines or [localize_text(output_language, zh="- 当前没有从更早组会延续的未完成事项。", en="- No unfinished work is being carried over.")]),
                "",
                localize_text(output_language, zh="## 风险", en="## Risks"),
                *(risk_lines or [localize_text(output_language, zh="- 当前没有记录到关键风险。", en="- No material risks are currently tracked.")]),
                "",
                localize_text(output_language, zh="## 推荐阅读", en="## Recommended Reading"),
                *(reading_lines or [localize_text(output_language, zh="- 当前没有推荐阅读。", en="- No recommended reading is available yet.")]),
            ]
        )
        return {
            "title": localize_text(
                output_language,
                zh=f"周报 - {briefing.project_name}",
                en=f"Weekly Report - {briefing.project_name}",
            ),
            "content_markdown": content,
        }

    def _build_next_meeting_briefing(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
        output_language: ResponseLanguage,
    ) -> dict[str, str]:
        _ = project_memory
        commitment_lines = [
            f"- **{commitment.student_name}**: " + "; ".join(commitment.commitments)
            for commitment in briefing.student_commitments
        ]
        agenda_lines = [
            localize_text(
                output_language,
                zh=f"- [{item.priority}] {item.title}：{item.reason}",
                en=f"- [{item.priority}] {item.title}: {item.reason}",
            )
            for item in briefing.recommended_agenda
        ]
        carryover_lines = [
            localize_text(
                output_language,
                zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline}",
                en=f"- {task.title} | owner: {task.owner} | due: {task.deadline}",
            )
            for task in briefing.carryover_tasks
        ]
        risk_lines = [
            localize_text(
                output_language,
                zh=f"- [{risk.level}] {risk.title}：{risk.detail or '需要明确缓解方案。'}",
                en=f"- [{risk.level}] {risk.title}: {risk.detail or 'Needs explicit mitigation.'}",
            )
            for risk in briefing.risks
        ]
        question_lines = [f"- {question}" for question in briefing.focus_questions]

        content = "\n".join(
            [
                localize_text(
                    output_language,
                    zh=f"# 下次组会 Briefing：{briefing.project_name}",
                    en=f"# Next Meeting Briefing: {briefing.project_name}",
                ),
                "",
                localize_text(output_language, zh="## 摘要", en="## Summary"),
                briefing.summary,
                "",
                localize_text(output_language, zh="## 学生承诺", en="## Student Commitments"),
                *(commitment_lines or [localize_text(output_language, zh="- 当前没有记录到进行中的承诺事项。", en="- No active commitments are recorded.")]),
                "",
                localize_text(output_language, zh="## 未完成任务", en="## Open Tasks"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline} | 状态：{task.status}",
                            en=f"- {task.title} | owner: {task.owner} | due: {task.deadline} | status: {task.status}",
                        )
                        for task in briefing.open_tasks
                    ]
                    or [localize_text(output_language, zh="- 当前没有未完成任务。", en="- No open tasks remain.")]
                ),
                "",
                localize_text(output_language, zh="## 历史延续事项", en="## Carryover From Earlier Meetings"),
                *(carryover_lines or [localize_text(output_language, zh="- 当前没有识别到历史延续事项。", en="- No carryover items were detected.")]),
                "",
                localize_text(output_language, zh="## 风险", en="## Risks"),
                *(risk_lines or [localize_text(output_language, zh="- 当前没有跟踪中的风险。", en="- No risks are currently tracked.")]),
                "",
                localize_text(output_language, zh="## 建议议程", en="## Recommended Agenda"),
                *(agenda_lines or [localize_text(output_language, zh="- 当前没有生成建议议程。", en="- No agenda items were generated.")]),
                "",
                localize_text(output_language, zh="## 关键问题", en="## Focus Questions"),
                *(question_lines or [localize_text(output_language, zh="- 当前没有生成关键问题。", en="- No focus questions were generated.")]),
            ]
        )
        return {
            "title": localize_text(
                output_language,
                zh=f"Briefing - {briefing.project_name}",
                en=f"Briefing - {briefing.project_name}",
            ),
            "content_markdown": content,
        }

    def _build_next_week_research_plan(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
        output_language: ResponseLanguage,
    ) -> dict[str, str]:
        high_priority_tasks = [task for task in briefing.open_tasks if task.priority == "high"]
        carryover_lines = [
            localize_text(
                output_language,
                zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline}",
                en=f"- {task.title} | owner: {task.owner} | due: {task.deadline}",
            )
            for task in briefing.carryover_tasks
        ]
        readings = self._collect_readings(project_memory)
        content = "\n".join(
            [
                localize_text(
                    output_language,
                    zh=f"# 下周研究执行计划：{briefing.project_name}",
                    en=f"# Next-Week Research Plan: {briefing.project_name}",
                ),
                "",
                localize_text(output_language, zh="## 优先任务", en="## Priority Tasks"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline} | 验收指标：{task.dependency_note}",
                            en=f"- {task.title} | owner: {task.owner} | due: {task.deadline} | metric: {task.dependency_note}",
                        )
                        for task in (high_priority_tasks or briefing.open_tasks)
                    ]
                    or [localize_text(output_language, zh="- 当前没有下周任务。", en="- No next-week tasks are currently available.")]
                ),
                "",
                localize_text(output_language, zh="## 验证目标", en="## Validation Targets"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {idea.idea_text} | 预期验证：{idea.expected_validation}",
                            en=f"- {idea.idea_text} | expected validation: {idea.expected_validation}",
                        )
                        for idea in briefing.last_advisor_ideas
                    ]
                    or [localize_text(output_language, zh="- 当前没有导师验证目标。", en="- No advisor validation targets are available.")]
                ),
                "",
                localize_text(output_language, zh="## 推荐阅读", en="## Recommended Reading"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {reading.title} | 优先级：{reading.priority} | {reading.reason}",
                            en=f"- {reading.title} | priority: {reading.priority} | {reading.reason}",
                        )
                        for reading in readings
                    ]
                    or [localize_text(output_language, zh="- 当前没有推荐阅读。", en="- No recommended reading is available.")]
                ),
                "",
                localize_text(output_language, zh="## 下周需要关闭的问题", en="## Questions To Close Next Week"),
                *(
                    [f"- {question}" for question in briefing.focus_questions]
                    or [localize_text(output_language, zh="- 当前没有待关闭问题。", en="- No closing questions are available.")]
                ),
                "",
                localize_text(output_language, zh="## 历史延续任务", en="## Carryover Tasks"),
                *(carryover_lines or [localize_text(output_language, zh="- 当前没有历史延续任务。", en="- No tasks are being carried over from previous meetings.")]),
            ]
        )
        return {
            "title": localize_text(
                output_language,
                zh=f"下周计划 - {briefing.project_name}",
                en=f"Next-Week Plan - {briefing.project_name}",
            ),
            "content_markdown": content,
        }

    def _build_presentation_outline(
        self,
        *,
        project_memory: ProjectMemorySnapshot,
        briefing: BriefingResult,
        output_language: ResponseLanguage,
    ) -> dict[str, str]:
        content = "\n".join(
            [
                localize_text(
                    output_language,
                    zh=f"# 汇报提纲：{briefing.project_name}",
                    en=f"# Presentation Outline: {briefing.project_name}",
                ),
                "",
                localize_text(output_language, zh="## 1. 本周发生了什么", en="## 1. What happened this week"),
                f"- {briefing.summary}",
                "",
                localize_text(output_language, zh="## 2. 值得强调的学生进展", en="## 2. Student progress worth highlighting"),
                *(
                    [
                        f"- {progress.student_name}: {progress.current_result}"
                        for progress in project_memory.student_progress
                    ]
                    or [localize_text(output_language, zh="- 当前没有学生进展。", en="- No student progress is available.")]
                ),
                "",
                localize_text(output_language, zh="## 3. 导师 ideas 与验证路径", en="## 3. Advisor ideas and validation path"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {idea.idea_text} | 验证：{idea.expected_validation}",
                            en=f"- {idea.idea_text} | validation: {idea.expected_validation}",
                        )
                        for idea in briefing.last_advisor_ideas
                    ]
                    or [localize_text(output_language, zh="- 当前没有导师 ideas。", en="- No advisor ideas are available.")]
                ),
                "",
                localize_text(output_language, zh="## 4. 风险与阻塞项", en="## 4. Risks and blockers"),
                *(
                    [
                        f"- [{risk.level}] {risk.title}"
                        for risk in briefing.risks
                    ]
                    or [localize_text(output_language, zh="- 当前没有关键风险。", en="- No material risks are available.")]
                ),
                "",
                localize_text(output_language, zh="## 5. 下周执行计划", en="## 5. Next-week execution plan"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {task.title} | 负责人：{task.owner} | 截止：{task.deadline}",
                            en=f"- {task.title} | owner: {task.owner} | due: {task.deadline}",
                        )
                        for task in briefing.open_tasks
                    ]
                    or [localize_text(output_language, zh="- 当前没有下周执行项。", en="- No next-week plan items are available.")]
                ),
                "",
                localize_text(output_language, zh="## 6. 需要说明的历史延续事项", en="## 6. Memory carryover to mention"),
                *(
                    [
                        localize_text(
                            output_language,
                            zh=f"- {task.title} | 延续自 {task.meeting_id}",
                            en=f"- {task.title} | carryover from {task.meeting_id}",
                        )
                        for task in briefing.carryover_tasks
                    ]
                    or [localize_text(output_language, zh="- 当前没有需要强调的历史延续任务。", en="- No carryover tasks need to be highlighted.")]
                ),
            ]
        )
        return {
            "title": localize_text(
                output_language,
                zh=f"汇报提纲 - {briefing.project_name}",
                en=f"Presentation Outline - {briefing.project_name}",
            ),
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

        for paper in project_memory.key_papers:
            if paper.title in seen_titles:
                continue
            readings.append(
                ReadingRecommendation(
                    id=paper.id,
                    meeting_id=paper.meeting_id or "unknown",
                    idea_id="memory",
                    student_name="unknown",
                    title=paper.title,
                    source_url=paper.source_url,
                    reason=paper.reason,
                    priority="medium",
                )
            )
            seen_titles.add(paper.title)

        return readings[:6]
