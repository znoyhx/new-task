from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentKey = Literal[
    "controller",
    "memory_steward",
    "execution_driver",
    "reading_specialist",
    "evidence_hunter",
]
StageStatus = Literal["completed", "skipped", "failed"]
ArtifactOriginLayer = Literal["current_transcript", "history_memory", "evidence_retrieval", "agent_inference"]
ArtifactSourceType = Literal[
    "advisor_idea",
    "student_progress",
    "blocker",
    "risk",
    "unresolved_question",
    "action_item",
    "claim",
    "project_decision",
    "key_paper",
    "meeting_chunk",
]
BriefingItemType = Literal["open_task", "carryover_task", "risk", "agenda", "focus_question"]


class AgentInputSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str
    label: str
    detail: str = ""
    meeting_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)


class AgentOutputTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str
    label: str
    detail: str = ""


class AgentFallback(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str
    used: bool = False
    detail: str = ""


class AgentStageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stage_key: str
    stage_label: str
    capability: str
    agent_key: AgentKey
    agent_name: str
    goal: str
    input_sources: list[AgentInputSource] = Field(default_factory=list)
    output_target: AgentOutputTarget
    fallback: AgentFallback
    status: StageStatus = "completed"
    triggered: bool = True
    trigger_reason: str = ""
    output_summary: str = ""
    error_detail: str = ""


class ArtifactAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: ArtifactSourceType
    origin_layer: ArtifactOriginLayer
    label: str
    detail: str
    meeting_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)


class ActionItemInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action_item_id: str
    title: str
    rationale: str
    output_summary: str = ""
    carryover: bool = False
    attributions: list[ArtifactAttribution] = Field(default_factory=list)


class ReadingInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reading_id: str
    title: str
    reason: str
    output_summary: str = ""
    attributions: list[ArtifactAttribution] = Field(default_factory=list)


class ClaimInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claim_id: str
    title: str
    trigger_reason: str
    verdict: str
    output_summary: str = ""
    attributions: list[ArtifactAttribution] = Field(default_factory=list)


class BriefingItemInsight(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str
    item_type: BriefingItemType
    title: str
    reason: str
    origin_layer: ArtifactOriginLayer
    attributions: list[ArtifactAttribution] = Field(default_factory=list)


class MemoryInUseItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str
    title: str
    item_type: str
    source_meeting_id: str | None = None
    status: str = "tracked"
    reason: str = ""


class MemoryUsageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str
    prior_meeting_count: int = 0
    open_task_count: int = 0
    recent_decision_count: int = 0
    relevant_context_count: int = 0
    memory_in_use: list[MemoryInUseItem] = Field(default_factory=list)


class ReviewExplanationBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action_items: list[ActionItemInsight] = Field(default_factory=list)
    readings: list[ReadingInsight] = Field(default_factory=list)
    claims: list[ClaimInsight] = Field(default_factory=list)
    briefing_items: list[BriefingItemInsight] = Field(default_factory=list)


class ReviewOrchestrationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    controller_agent_name: str
    llm_provider: str
    llm_model: str
    stages: list[AgentStageRecord] = Field(default_factory=list)
    memory_usage: MemoryUsageSummary | None = None
