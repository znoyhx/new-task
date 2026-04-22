import type {
  ActionItemStatusValue,
  DashboardResultData,
  DeliverableKey,
  DeliverablePreview,
  EvidenceConfidence,
  EvidenceStance,
  ProjectMemoryData,
  RiskLevel,
  TaskPriority,
} from "./dashboard-types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

type ReviewErrorDetail = {
  message?: string;
  stage?: string;
  agent?: string;
  fallback?: string;
};

export class DashboardApiError extends Error {
  stage?: string;
  agent?: string;
  fallback?: string;

  constructor(message: string, detail?: ReviewErrorDetail) {
    super(message);
    this.name = "DashboardApiError";
    this.stage = detail?.stage;
    this.agent = detail?.agent;
    this.fallback = detail?.fallback;
  }
}

type MeetingImportResponse = {
  meeting: {
    meeting_id: string;
  };
};

type MeetingReviewResponse = {
  project: {
    project_id: string;
    name: string;
  };
  meeting: {
    meeting_id: string;
    meeting_title?: string | null;
    created_at: string;
    status: string;
  };
  transcript: {
    chunks: Array<{
      chunk_id: string;
      timestamp_start?: string | null;
      speaker: string;
      text: string;
    }>;
  };
  progress: {
    summary: string;
    student_progress: Array<{
      student_name: string;
      completed_work: string[];
      current_result: string;
      blockers: string[];
      risks: Array<{
        title: string;
        level: RiskLevel;
        description: string;
      }>;
      next_step_suggestion: string;
      unresolved_questions: string[];
    }>;
  };
  ideas: {
    ideas: Array<{
      id?: string | null;
      idea_text: string;
      expected_validation: string;
      validation_metrics: string[];
      recommended_reading: Array<{
        title: string;
      }>;
    }>;
  };
  research_plan: {
    tasks: Array<{
      idea_id: string;
      title: string;
      owner: string;
      due_date: string;
      priority: TaskPriority;
      success_metrics: string[];
      rationale: string;
    }>;
  };
  reading_recommendations: {
    recommendations: Array<{
      id?: string | null;
      title: string;
      reason: string;
      priority: TaskPriority;
      source_url: string;
      student_name: string;
    }>;
  };
  claims: Array<{
    claim: {
      id?: string | null;
      text: string;
      speaker: string;
      verification_status: "supported" | "contradicted" | "needs_verification";
      transcript_snippet: string;
      source_chunk_ids: string[];
    };
    verdict: "supported" | "contradicted" | "needs_verification";
    confidence: EvidenceConfidence;
    evidence_cards: Array<{
      id?: string | null;
      source_title: string;
      source_url: string;
      source_type: string;
      stance: "support" | "contradict" | "needs_verification";
      confidence: EvidenceConfidence;
      snippet: string;
    }>;
  }>;
  briefing: {
    summary: string;
    focus_questions: string[];
    recommended_agenda: Array<{
      title: string;
      reason: string;
      priority: TaskPriority;
    }>;
  };
  deliverables: Array<{
    deliverable_type:
      | "weekly_report"
      | "next_meeting_briefing"
      | "next_week_research_plan"
      | "presentation_outline";
    title: string;
    content_markdown: string;
  }>;
  orchestration: {
    controller_agent_name: string;
    llm_provider: string;
    llm_model: string;
    stages: Array<{
      stage_key: string;
      stage_label: string;
      capability: string;
      agent_name: string;
      goal: string;
      input_sources: Array<{
        kind: string;
        label: string;
        detail: string;
        meeting_id?: string | null;
        chunk_ids: string[];
      }>;
      output_target: {
        kind: string;
        label: string;
        detail: string;
      };
      fallback: {
        summary: string;
        used: boolean;
        detail: string;
      };
      status: "completed" | "skipped" | "failed";
      triggered: boolean;
      trigger_reason: string;
      output_summary: string;
      error_detail: string;
    }>;
    memory_usage?: {
      project_id: string;
      prior_meeting_count: number;
      open_task_count: number;
      recent_decision_count: number;
      relevant_context_count: number;
      memory_in_use: Array<{
        item_id: string;
        title: string;
        item_type: string;
        source_meeting_id?: string | null;
        status: string;
        reason: string;
      }>;
    } | null;
  };
  explanations: {
    action_items: Array<{
      action_item_id: string;
      title: string;
      rationale: string;
      output_summary: string;
      carryover: boolean;
      attributions: Array<{
        source_type: string;
        origin_layer: string;
        label: string;
        detail: string;
        meeting_id?: string | null;
        chunk_ids: string[];
      }>;
    }>;
    readings: Array<{
      reading_id: string;
      title: string;
      reason: string;
      output_summary: string;
      attributions: Array<{
        source_type: string;
        origin_layer: string;
        label: string;
        detail: string;
        meeting_id?: string | null;
        chunk_ids: string[];
      }>;
    }>;
    claims: Array<{
      claim_id: string;
      title: string;
      trigger_reason: string;
      verdict: string;
      output_summary: string;
      attributions: Array<{
        source_type: string;
        origin_layer: string;
        label: string;
        detail: string;
        meeting_id?: string | null;
        chunk_ids: string[];
      }>;
    }>;
    briefing_items: Array<{
      item_id: string;
      item_type: string;
      title: string;
      reason: string;
      origin_layer: string;
      attributions: Array<{
        source_type: string;
        origin_layer: string;
        label: string;
        detail: string;
        meeting_id?: string | null;
        chunk_ids: string[];
      }>;
    }>;
  };
};

type DeliverableGenerationResponse = {
  document: {
    deliverable_type:
      | "weekly_report"
      | "next_meeting_briefing"
      | "next_week_research_plan"
      | "presentation_outline";
    title: string;
    content_markdown: string;
  };
};

type ProjectMemoryApiResponse = {
  project_memory: {
    project: {
      project_id: string;
      name: string;
    } | null;
    meetings: Array<{
      meeting_id: string;
      title: string;
      summary: string;
      created_at: string;
    }>;
    decisions: Array<{
      id: string;
      meeting_id?: string | null;
      title: string;
      rationale: string;
      decided_by: string;
      created_at: string;
    }>;
    action_items: Array<{
      meeting_id?: string | null;
      title: string;
      owner: string;
      deadline: string;
      priority: TaskPriority;
      status: ActionItemStatusValue;
    }>;
    relevant_context: Array<{
      entry_id: string;
    }>;
  };
  briefing: {
    summary: string;
    focus_questions: string[];
    recommended_agenda: Array<{
      title: string;
      reason: string;
      priority: TaskPriority;
    }>;
  };
  briefing_items: Array<{
    item_id: string;
    item_type: string;
    title: string;
    reason: string;
    origin_layer: string;
    attributions: Array<{
      source_type: string;
      origin_layer: string;
      label: string;
      detail: string;
      meeting_id?: string | null;
      chunk_ids: string[];
    }>;
  }>;
};

type ActionItemStatusUpdateResponse = ProjectMemoryApiResponse & {
  updated_action_item: {
    meeting_id?: string | null;
    title: string;
    owner: string;
    deadline: string;
    priority: TaskPriority;
    status: ActionItemStatusValue;
  };
};

export type ActionItemStatusUpdateResult = {
  updatedActionItem: {
    id: string;
    meetingId?: string | null;
    title: string;
    owner: string;
    status: ActionItemStatusValue;
  };
  projectMemory: ProjectMemoryData;
};

function toKey(type: DeliverableGenerationResponse["document"]["deliverable_type"]): DeliverableKey {
  if (type === "weekly_report") {
    return "weekly-report";
  }
  if (type === "next_meeting_briefing") {
    return "next-meeting-briefing";
  }
  if (type === "next_week_research_plan") {
    return "next-week-plan";
  }
  return "presentation-outline";
}

function toLabel(key: DeliverableKey) {
  if (key === "weekly-report") {
    return "Weekly Report";
  }
  if (key === "next-meeting-briefing") {
    return "Briefing";
  }
  if (key === "next-week-plan") {
    return "Next-Week Plan";
  }
  return "Presentation Outline";
}

function toStance(stance: "support" | "contradict" | "needs_verification"): EvidenceStance {
  if (stance === "support") {
    return "support";
  }
  if (stance === "contradict") {
    return "contradict";
  }
  return "needs verification";
}

function buildUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), init);
  if (!response.ok) {
    let detail = response.statusText;
    let detailObject: ReviewErrorDetail | undefined;
    try {
      const payload = (await response.json()) as { detail?: string | ReviewErrorDetail };
      if (typeof payload.detail === "string" && payload.detail) {
        detail = payload.detail;
      }
      if (payload.detail && typeof payload.detail === "object") {
        detailObject = payload.detail;
        detail = payload.detail.message || response.statusText;
      }
    } catch {
      // keep response status text
    }
    throw new DashboardApiError(detail, detailObject);
  }
  return (await response.json()) as T;
}

function formatDate(isoDate: string) {
  return new Date(isoDate).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function mapDeliverable(
  deliverable:
    | MeetingReviewResponse["deliverables"][number]
    | DeliverableGenerationResponse["document"]
): DeliverablePreview {
  const key = toKey(deliverable.deliverable_type);
  return {
    key,
    label: toLabel(key),
    title: deliverable.title,
    content: deliverable.content_markdown,
  };
}

function toActionInsightKey(title: string, owner: string) {
  return `${title.trim().toLowerCase()}::${owner.trim().toLowerCase()}`;
}

function toActionItemId(meetingId: string | null | undefined, title: string, owner: string) {
  return `${meetingId || "unknown"}::${toActionInsightKey(title, owner)}`;
}

function mapAttributions(
  attributions: Array<{
    source_type: string;
    origin_layer: string;
    label: string;
    detail: string;
    meeting_id?: string | null;
    chunk_ids: string[];
  }>
) {
  return attributions.map((attribution) => ({
    sourceType: attribution.source_type,
    originLayer: attribution.origin_layer,
    label: attribution.label,
    detail: attribution.detail,
    meetingId: attribution.meeting_id,
    chunkIds: attribution.chunk_ids,
  }));
}

function mapOrchestrationStages(
  stages: MeetingReviewResponse["orchestration"]["stages"]
) {
  return stages.map((stage) => ({
    key: stage.stage_key,
    label: stage.stage_label,
    description: stage.output_summary || stage.capability,
    agentName: stage.agent_name,
    agentGoal: stage.goal,
    inputSource:
      stage.input_sources.map((source) => `${source.label}${source.detail ? `: ${source.detail}` : ""}`).join(" / ") ||
      "Unknown",
    outputTarget: `${stage.output_target.label}${stage.output_target.detail ? `: ${stage.output_target.detail}` : ""}`,
    fallback: `${stage.fallback.summary}${stage.fallback.detail ? ` ${stage.fallback.detail}` : ""}`,
    outputSummary: stage.output_summary,
    triggerReason: stage.trigger_reason,
    status: stage.status,
  }));
}

function mapBriefingItems(
  items:
    | MeetingReviewResponse["explanations"]["briefing_items"]
    | ProjectMemoryApiResponse["briefing_items"]
) {
  return items.map((item) => ({
    id: item.item_id,
    itemType: item.item_type,
    title: item.title,
    reason: item.reason,
    originLayer: item.origin_layer,
    attributions: mapAttributions(item.attributions),
  }));
}

function deriveMemoryUsage(
  response: ProjectMemoryApiResponse,
  currentMeetingId?: string
) {
  const meetingTitleById = new Map(
    response.project_memory.meetings.map((meeting) => [meeting.meeting_id, meeting.title] as const)
  );
  const priorMeetings = response.project_memory.meetings.filter(
    (meeting) => meeting.meeting_id !== currentMeetingId
  );
  const carryoverTasks = response.project_memory.action_items.filter(
    (item) => item.status !== "done" && item.meeting_id !== currentMeetingId
  );
  const priorDecisions = response.project_memory.decisions.filter(
    (decision) => decision.meeting_id !== currentMeetingId
  );

  return {
    projectId: response.project_memory.project?.project_id || "unknown-project",
    priorMeetingCount: priorMeetings.length,
    openTaskCount: carryoverTasks.length,
    recentDecisionCount: priorDecisions.length,
    relevantContextCount: response.project_memory.relevant_context.length,
    memoryInUse: [
      ...carryoverTasks.slice(0, 4).map((item) => ({
        id: toActionItemId(item.meeting_id, item.title, item.owner),
        title: item.title,
        itemType: "action_item",
        sourceMeetingId: item.meeting_id,
        status: item.status,
        reason: `Carryover task from ${meetingTitleById.get(item.meeting_id || "") || item.meeting_id || "history"}.`,
      })),
      ...priorDecisions.slice(0, 2).map((decision) => ({
        id: `decision::${decision.id}`,
        title: decision.title,
        itemType: "decision",
        sourceMeetingId: decision.meeting_id,
        status: "recorded",
        reason: `Earlier decision from ${meetingTitleById.get(decision.meeting_id || "") || decision.meeting_id || "history"}.`,
      })),
    ],
  };
}

function mapProjectMemoryResponse(
  response: ProjectMemoryApiResponse,
  currentMeetingId?: string
): ProjectMemoryData {
  const meetingTitleById = new Map(
    response.project_memory.meetings.map((meeting) => [meeting.meeting_id, meeting.title] as const)
  );
  const meetings = [...response.project_memory.meetings]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .map((meeting) => ({
      meetingId: meeting.meeting_id,
      title: meeting.title,
      summary: meeting.summary,
      createdAt: formatDate(meeting.created_at),
    }));
  const recentDecisions = [...response.project_memory.decisions]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .slice(0, 4)
    .map((decision) => ({
      id: decision.id,
      meetingId: decision.meeting_id,
      meetingTitle: decision.meeting_id ? meetingTitleById.get(decision.meeting_id) || null : null,
      title: decision.title,
      rationale: decision.rationale,
      decidedBy: decision.decided_by,
    }));
  const openActionItems = response.project_memory.action_items
    .filter((item) => item.status !== "done")
    .map((item) => ({
      id: toActionItemId(item.meeting_id, item.title, item.owner),
      meetingId: item.meeting_id,
      meetingTitle: item.meeting_id ? meetingTitleById.get(item.meeting_id) || null : null,
      title: item.title,
      owner: item.owner,
      dueDate: item.deadline,
      priority: item.priority,
      status: item.status,
      originLayer:
        item.meeting_id && currentMeetingId && item.meeting_id !== currentMeetingId
          ? "history_memory"
          : "current_transcript",
    }))
    .sort((left, right) => {
      if (left.originLayer !== right.originLayer) {
        return left.originLayer === "history_memory" ? -1 : 1;
      }
      const priorityRank = { high: 0, medium: 1, low: 2 };
      return (
        priorityRank[left.priority] - priorityRank[right.priority] ||
        left.title.localeCompare(right.title)
      );
    });

  return {
    projectId: response.project_memory.project?.project_id || "unknown-project",
    projectName: response.project_memory.project?.name || "Unknown project",
    meetings,
    recentDecisions,
    openActionItems,
    briefing: {
      summary: response.briefing.summary,
      focusQuestions: response.briefing.focus_questions,
      recommendedAgenda: response.briefing.recommended_agenda,
      items: mapBriefingItems(response.briefing_items),
    },
    memoryUsage: deriveMemoryUsage(response, currentMeetingId),
  };
}

async function reviewImportedMeeting(meetingId: string): Promise<MeetingReviewResponse> {
  return requestJson<MeetingReviewResponse>(`/api/meetings/${meetingId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: "evidenceflow-demo-project",
      project_name: "EvidenceFlow Demo Project",
      project_description: "Single-workspace research cockpit for weekly meetings.",
      project_domain: "research-automation",
      verify_claims: true,
      max_claims_to_verify: 1,
    }),
  });
}

function mapReviewToDashboardResult(review: MeetingReviewResponse): DashboardResultData {
  const actionInsightByKey = new Map(
    review.explanations.action_items.map((insight) => [insight.action_item_id, insight] as const)
  );
  const readingInsightById = new Map(
    review.explanations.readings.map((insight) => [insight.reading_id, insight] as const)
  );
  const claimInsightById = new Map(
    review.explanations.claims.map((insight) => [insight.claim_id, insight] as const)
  );

  return {
    projectId: review.project.project_id,
    meetingId: review.meeting.meeting_id,
    projectName: review.project.name,
    meetingTitle: review.meeting.meeting_title || "Imported meeting",
    meetingDate: formatDate(review.meeting.created_at),
    meetingStatus: review.meeting.status,
    processingNote: review.progress.summary,
    summary: review.briefing.summary,
    studentProgress: review.progress.student_progress.map((student) => {
      const riskLevel = student.risks[0]?.level ?? "medium";
      return {
        studentName: student.student_name,
        completedWork: student.completed_work,
        currentResult: student.current_result,
        blockers: student.blockers,
        riskLevel,
        risks: student.risks.map((risk) => risk.title),
        nextStep: student.next_step_suggestion,
        unresolvedQuestions: student.unresolved_questions,
      };
    }),
    advisorIdeas: review.ideas.ideas.map((idea, index) => ({
      id: idea.id || `idea-${index + 1}`,
      title: idea.idea_text,
      summary: idea.expected_validation,
      suggestedExperiment: idea.expected_validation,
      recommendedReading: idea.recommended_reading.map((reading) => reading.title),
      validationMetrics: idea.validation_metrics,
      evidenceStatus: "Optional evidence support",
      sourceChunkIds: [],
    })),
    actionItems: review.research_plan.tasks.map((task, index) => ({
      id: toActionItemId(review.meeting.meeting_id, task.title, task.owner),
      meetingId: review.meeting.meeting_id,
      title: task.title,
      owner: task.owner,
      dueDate: task.due_date,
      priority: task.priority,
      status: "open",
      successMetrics: task.success_metrics,
      rationale: task.rationale,
      sourceLabel:
        actionInsightByKey
          .get(toActionInsightKey(task.title, task.owner))
          ?.attributions.map((attribution) => attribution.label)
          .join(" / ") || `Derived from ${task.idea_id}`,
      outputSummary:
        actionInsightByKey.get(toActionInsightKey(task.title, task.owner))?.output_summary ||
        task.rationale,
      carryover:
        actionInsightByKey.get(toActionInsightKey(task.title, task.owner))?.carryover || false,
      attributions: mapAttributions(
        actionInsightByKey.get(toActionInsightKey(task.title, task.owner))?.attributions || []
      ),
    })),
    readingList: review.reading_recommendations.recommendations.map((reading, index) => ({
      id: reading.id || `reading-${index + 1}`,
      title: reading.title,
      reason: reading.reason,
      priority: reading.priority,
      sourceUrl: reading.source_url,
      studentName: reading.student_name,
      outputSummary: readingInsightById.get(reading.id || reading.title)?.output_summary || reading.reason,
      attributions: mapAttributions(readingInsightById.get(reading.id || reading.title)?.attributions || []),
    })),
    claims: review.claims.map((claimResult, index) => ({
      id: claimResult.claim.id || `claim-${index + 1}`,
      text: claimResult.claim.text,
      speaker: claimResult.claim.speaker,
      verdict: claimResult.verdict,
      confidence: claimResult.confidence,
      transcriptSnippet: claimResult.claim.transcript_snippet,
      sourceChunkIds: claimResult.claim.source_chunk_ids,
      triggerReason:
        claimInsightById.get(claimResult.claim.id || claimResult.claim.text)?.trigger_reason ||
        "Claim verification was enabled for this run.",
      outputSummary:
        claimInsightById.get(claimResult.claim.id || claimResult.claim.text)?.output_summary ||
        "",
      attributions: mapAttributions(
        claimInsightById.get(claimResult.claim.id || claimResult.claim.text)?.attributions || []
      ),
      evidenceCards: claimResult.evidence_cards.map((card, evidenceIndex) => ({
        id: card.id || `evidence-${evidenceIndex + 1}`,
        sourceTitle: card.source_title,
        sourceUrl: card.source_url,
        sourceType: card.source_type,
        stance: toStance(card.stance),
        confidence: card.confidence,
        snippet: card.snippet,
      })),
    })),
    transcriptTimeline: review.transcript.chunks.map((chunk) => ({
      chunkId: chunk.chunk_id,
      timestamp: chunk.timestamp_start || "--:--",
      speaker: chunk.speaker,
      text: chunk.text,
    })),
    briefing: {
      summary: review.briefing.summary,
      focusQuestions: review.briefing.focus_questions,
      recommendedAgenda: review.briefing.recommended_agenda,
      items: mapBriefingItems(review.explanations.briefing_items),
    },
    deliverables: review.deliverables.map(mapDeliverable),
    orchestration: {
      controllerAgentName: review.orchestration.controller_agent_name,
      llmProvider: review.orchestration.llm_provider,
      llmModel: review.orchestration.llm_model,
      stages: mapOrchestrationStages(review.orchestration.stages),
      memoryUsage: review.orchestration.memory_usage
        ? {
            projectId: review.orchestration.memory_usage.project_id,
            priorMeetingCount: review.orchestration.memory_usage.prior_meeting_count,
            openTaskCount: review.orchestration.memory_usage.open_task_count,
            recentDecisionCount: review.orchestration.memory_usage.recent_decision_count,
            relevantContextCount: review.orchestration.memory_usage.relevant_context_count,
            memoryInUse: review.orchestration.memory_usage.memory_in_use.map((item) => ({
              id: item.item_id,
              title: item.title,
              itemType: item.item_type,
              sourceMeetingId: item.source_meeting_id,
              status: item.status,
              reason: item.reason,
            })),
          }
        : null,
    },
  };
}

export async function processMeetingTranscript(transcriptText: string): Promise<DashboardResultData> {
  const imported = await requestJson<MeetingImportResponse>("/api/meetings/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      meeting_title: "Demo Weekly Group Meeting",
      source_type: "transcript",
      transcript_text: transcriptText,
    }),
  });

  return mapReviewToDashboardResult(await reviewImportedMeeting(imported.meeting.meeting_id));
}

export async function processMeetingAudio(
  audioFile: File,
  options?: {
    meetingTitle?: string;
    languageHint?: string;
  }
): Promise<DashboardResultData> {
  const formData = new FormData();
  formData.append("file", audioFile);
  formData.append("meeting_title", options?.meetingTitle || audioFile.name || "Audio Meeting");
  if (options?.languageHint) {
    formData.append("language_hint", options.languageHint);
  }

  const imported = await requestJson<MeetingImportResponse>("/api/meetings/import-audio", {
    method: "POST",
    body: formData,
  });

  return mapReviewToDashboardResult(await reviewImportedMeeting(imported.meeting.meeting_id));
}

export async function fetchDeliverable(
  projectId: string,
  key: DeliverableKey
): Promise<DeliverablePreview> {
  const deliverableType =
    key === "weekly-report"
      ? "weekly_report"
      : key === "next-meeting-briefing"
        ? "next_meeting_briefing"
        : key === "next-week-plan"
          ? "next_week_research_plan"
          : "presentation_outline";

  const response = await requestJson<DeliverableGenerationResponse>("/api/deliverables/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      deliverable_type: deliverableType,
    }),
  });
  return mapDeliverable(response.document);
}

export async function fetchProjectMemory(
  projectId: string,
  currentMeetingId?: string
): Promise<ProjectMemoryData> {
  const response = await requestJson<ProjectMemoryApiResponse>(`/api/projects/${projectId}/memory`, {
    method: "GET",
  });
  return mapProjectMemoryResponse(response, currentMeetingId);
}

export async function updateActionItemStatus(
  projectId: string,
  request: {
    meetingId: string;
    title: string;
    owner: string;
    status: ActionItemStatusValue;
    currentMeetingId?: string;
  }
): Promise<ActionItemStatusUpdateResult> {
  const response = await requestJson<ActionItemStatusUpdateResponse>(
    `/api/projects/${projectId}/action-items/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        meeting_id: request.meetingId,
        title: request.title,
        owner: request.owner,
        status: request.status,
      }),
    }
  );

  return {
    updatedActionItem: {
      id: toActionItemId(response.updated_action_item.meeting_id, response.updated_action_item.title, response.updated_action_item.owner),
      meetingId: response.updated_action_item.meeting_id,
      title: response.updated_action_item.title,
      owner: response.updated_action_item.owner,
      status: response.updated_action_item.status,
    },
    projectMemory: mapProjectMemoryResponse(response, request.currentMeetingId),
  };
}
