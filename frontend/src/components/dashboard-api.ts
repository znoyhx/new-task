import type {
  DashboardResultData,
  DeliverableKey,
  DeliverablePreview,
  EvidenceConfidence,
  EvidenceStance,
  RiskLevel,
  TaskPriority,
} from "./dashboard-types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

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
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // keep response status text
    }
    throw new Error(detail);
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
      id: `${task.idea_id}-${index + 1}`,
      title: task.title,
      owner: task.owner,
      dueDate: task.due_date,
      priority: task.priority,
      status: "open",
      successMetrics: task.success_metrics,
      rationale: task.rationale,
      sourceLabel: `Derived from ${task.idea_id}`,
    })),
    readingList: review.reading_recommendations.recommendations.map((reading, index) => ({
      id: reading.id || `reading-${index + 1}`,
      title: reading.title,
      reason: reading.reason,
      priority: reading.priority,
      sourceUrl: reading.source_url,
      studentName: reading.student_name,
    })),
    claims: review.claims.map((claimResult, index) => ({
      id: claimResult.claim.id || `claim-${index + 1}`,
      text: claimResult.claim.text,
      speaker: claimResult.claim.speaker,
      verdict: claimResult.verdict,
      confidence: claimResult.confidence,
      transcriptSnippet: claimResult.claim.transcript_snippet,
      sourceChunkIds: claimResult.claim.source_chunk_ids,
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
    },
    deliverables: review.deliverables.map(mapDeliverable),
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
