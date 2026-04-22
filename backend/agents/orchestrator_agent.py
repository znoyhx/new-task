from __future__ import annotations

from dataclasses import dataclass

from backend.config import Settings
from backend.schemas.orchestration import (
    AgentFallback,
    AgentInputSource,
    AgentOutputTarget,
    AgentStageRecord,
    MemoryInUseItem,
    MemoryUsageSummary,
    ReviewOrchestrationSummary,
)
from backend.schemas.project_memory import ProjectMemorySnapshot
from backend.services.response_language import ResponseLanguage, localize_text


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    name_en: str
    name_zh: str
    fallback_en: str
    fallback_zh: str

    def name(self, output_language: ResponseLanguage) -> str:
        return self.name_zh if output_language == "zh" else self.name_en

    def fallback(self, output_language: ResponseLanguage) -> str:
        return self.fallback_zh if output_language == "zh" else self.fallback_en


AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "controller": AgentDefinition(
        key="controller",
        name_en="Controller Agent",
        name_zh="主控 Agent",
        fallback_en="Stop the run, keep imported artifacts on disk, and report the failing capability clearly.",
        fallback_zh="停止当前运行，保留已导入材料，并明确报告失败的能力阶段。",
    ),
    "memory_steward": AgentDefinition(
        key="memory_steward",
        name_en="Memory Steward Agent",
        name_zh="记忆管家 Agent",
        fallback_en="If no prior project memory exists, continue in first-meeting mode with an empty memory snapshot.",
        fallback_zh="如果不存在历史项目记忆，就以首轮组会模式继续，并使用空的 memory snapshot。",
    ),
    "execution_driver": AgentDefinition(
        key="execution_driver",
        name_en="Execution Driver Agent",
        name_zh="推进 Agent",
        fallback_en="If the final plan call fails, fall back to advisor idea next-actions that are already grounded in the meeting.",
        fallback_zh="如果最终计划生成失败，就退回到组会中已提取的 advisor next-actions。",
    ),
    "reading_specialist": AgentDefinition(
        key="reading_specialist",
        name_en="Reading Specialist Agent",
        name_zh="推荐阅读 Agent",
        fallback_en="If the reading pass fails, keep the advisor-linked reading list captured during idea extraction.",
        fallback_zh="如果阅读推荐阶段失败，就保留 idea capture 阶段中已提取的关联阅读。",
    ),
    "evidence_hunter": AgentDefinition(
        key="evidence_hunter",
        name_en="Evidence Hunter Agent",
        name_zh="证据猎手 Agent",
        fallback_en="If retrieval or verification fails, keep the claim visible as 'needs verification' and preserve transcript traceability.",
        fallback_zh="如果检索或核验失败，就把 claim 保留为“待核验”，同时保留 transcript traceability。",
    ),
}


class ReviewOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        project_id: str,
        response_language: ResponseLanguage = "en",
    ) -> None:
        self.settings = settings
        self.project_id = project_id
        self.response_language = response_language
        self.controller_agent_name = AGENT_DEFINITIONS["controller"].name(response_language)
        self._stages: list[AgentStageRecord] = []
        self._memory_usage: MemoryUsageSummary | None = None

    def record_stage(
        self,
        *,
        stage_key: str,
        stage_label: str,
        capability: str,
        agent_key: str,
        goal: str,
        input_sources: list[AgentInputSource],
        output_target: AgentOutputTarget,
        output_summary: str = "",
        trigger_reason: str = "",
        triggered: bool = True,
        status: str = "completed",
        fallback_used: bool = False,
        fallback_detail: str = "",
        error_detail: str = "",
    ) -> AgentStageRecord:
        definition = AGENT_DEFINITIONS[agent_key]
        stage = AgentStageRecord(
            stage_key=stage_key,
            stage_label=stage_label,
            capability=capability,
            agent_key=definition.key,  # type: ignore[arg-type]
            agent_name=definition.name(self.response_language),
            goal=goal,
            input_sources=input_sources,
            output_target=output_target,
            fallback=AgentFallback(
                summary=definition.fallback(self.response_language),
                used=fallback_used,
                detail=fallback_detail,
            ),
            status=status,  # type: ignore[arg-type]
            triggered=triggered,
            trigger_reason=trigger_reason,
            output_summary=output_summary,
            error_detail=error_detail,
        )
        self._stages.append(stage)
        return stage

    def summarize_memory(
        self,
        snapshot: ProjectMemorySnapshot,
        *,
        current_meeting_id: str,
    ) -> MemoryUsageSummary:
        prior_meetings = [
            meeting
            for meeting in snapshot.meetings
            if meeting.meeting_id != current_meeting_id
        ]
        prior_open_tasks = [
            task
            for task in snapshot.action_items
            if task.meeting_id != current_meeting_id and task.status != "done"
        ]
        prior_decisions = [
            decision
            for decision in snapshot.decisions
            if decision.meeting_id != current_meeting_id
        ]

        memory_in_use: list[MemoryInUseItem] = []
        for task in prior_open_tasks[:3]:
            memory_in_use.append(
                MemoryInUseItem(
                    item_id=f"carryover-task::{task.meeting_id or 'unknown'}::{task.title}",
                    title=task.title,
                    item_type="carryover_action_item",
                    source_meeting_id=task.meeting_id,
                    status=task.status,
                    reason=localize_text(
                        self.response_language,
                        zh=f"{task.owner} 负责的未完成任务在本次 review 前仍未关闭。",
                        en=f"Open task owned by {task.owner} remains unresolved before this review.",
                    ),
                )
            )

        for decision in prior_decisions[:2]:
            memory_in_use.append(
                MemoryInUseItem(
                    item_id=f"decision::{decision.id}",
                    title=decision.title,
                    item_type="project_decision",
                    source_meeting_id=decision.meeting_id,
                    status="tracked",
                    reason=localize_text(
                        self.response_language,
                        zh="历史决策仍然和当前推进方向直接相关。",
                        en="Historical decision is still relevant to the current direction.",
                    ),
                )
            )

        for hit in snapshot.relevant_context[:2]:
            memory_in_use.append(
                MemoryInUseItem(
                    item_id=hit.entry_id,
                    title=hit.text,
                    item_type=hit.entry_type,
                    source_meeting_id=hit.meeting_id,
                    status="retrieved",
                    reason=localize_text(
                        self.response_language,
                        zh="作为相关上下文从本地 memory 检索命中。",
                        en="Retrieved from local memory search as relevant context.",
                    ),
                )
            )

        summary = MemoryUsageSummary(
            project_id=self.project_id,
            prior_meeting_count=len(prior_meetings),
            open_task_count=len(prior_open_tasks),
            recent_decision_count=len(prior_decisions),
            relevant_context_count=len(snapshot.relevant_context),
            memory_in_use=memory_in_use,
        )
        self._memory_usage = summary
        return summary

    def to_summary(self) -> ReviewOrchestrationSummary:
        return ReviewOrchestrationSummary(
            controller_agent_name=self.controller_agent_name,
            llm_provider=self.settings.llm_provider,
            llm_model=self.settings.llm_model,
            stages=self._stages,
            memory_usage=self._memory_usage,
        )
