export type RiskLevel = "low" | "medium" | "high";
export type TaskPriority = "low" | "medium" | "high";
export type EvidenceStance = "support" | "contradict" | "needs verification";
export type EvidenceConfidence = "low" | "medium" | "high";
export type DeliverableKey =
  | "weekly-report"
  | "next-meeting-briefing"
  | "next-week-plan"
  | "presentation-outline";
export type DashboardRunState = "idle" | "loading" | "ready" | "error";

export type ProcessingStage = {
  key: string;
  label: string;
  description: string;
};

export type StudentProgressCardData = {
  studentName: string;
  completedWork: string[];
  currentResult: string;
  blockers: string[];
  riskLevel: RiskLevel;
  risks: string[];
  nextStep: string;
  unresolvedQuestions: string[];
};

export type AdvisorIdeaCardData = {
  id: string;
  title: string;
  summary: string;
  suggestedExperiment: string;
  recommendedReading: string[];
  validationMetrics: string[];
  evidenceStatus: string;
  sourceChunkIds: string[];
};

export type ActionItemData = {
  id: string;
  title: string;
  owner: string;
  dueDate: string;
  priority: TaskPriority;
  status: string;
  successMetrics: string[];
  rationale: string;
  sourceLabel: string;
};

export type ReadingItemData = {
  id: string;
  title: string;
  reason: string;
  priority: TaskPriority;
  sourceUrl: string;
  studentName: string;
};

export type EvidenceCardData = {
  id: string;
  sourceTitle: string;
  sourceUrl: string;
  sourceType: string;
  stance: EvidenceStance;
  confidence: EvidenceConfidence;
  snippet: string;
};

export type ClaimData = {
  id: string;
  text: string;
  speaker: string;
  verdict: "supported" | "contradicted" | "needs_verification";
  confidence: EvidenceConfidence;
  transcriptSnippet: string;
  sourceChunkIds: string[];
  evidenceCards: EvidenceCardData[];
};

export type TranscriptEntryData = {
  chunkId: string;
  timestamp: string;
  speaker: string;
  text: string;
};

export type BriefingAgendaItemData = {
  title: string;
  reason: string;
  priority: TaskPriority;
};

export type DeliverablePreview = {
  key: DeliverableKey;
  label: string;
  title: string;
  content: string;
};

export type BriefingData = {
  summary: string;
  focusQuestions: string[];
  recommendedAgenda: BriefingAgendaItemData[];
};

export type DashboardResultData = {
  projectId: string;
  meetingId: string;
  projectName: string;
  meetingTitle: string;
  meetingDate: string;
  meetingStatus: string;
  processingNote: string;
  summary: string;
  studentProgress: StudentProgressCardData[];
  advisorIdeas: AdvisorIdeaCardData[];
  actionItems: ActionItemData[];
  readingList: ReadingItemData[];
  claims: ClaimData[];
  transcriptTimeline: TranscriptEntryData[];
  briefing: BriefingData;
  deliverables: DeliverablePreview[];
};
