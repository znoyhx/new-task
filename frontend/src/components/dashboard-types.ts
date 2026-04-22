export type RiskLevel = "low" | "medium" | "high";
export type TaskPriority = "low" | "medium" | "high";
export type ActionItemStatusValue = "open" | "in_progress" | "blocked" | "done" | "unknown";
export type EvidenceStance = "support" | "contradict" | "needs verification";
export type EvidenceConfidence = "low" | "medium" | "high";
export type DashboardLanguage = "zh" | "en";
export type DeliverableKey =
  | "weekly-report"
  | "next-meeting-briefing"
  | "next-week-plan"
  | "presentation-outline";
export type DashboardRunState = "idle" | "loading" | "ready" | "error";
export type StageStatus = "planned" | "completed" | "skipped" | "failed";

export type ArtifactAttributionData = {
  sourceType: string;
  originLayer: string;
  label: string;
  detail: string;
  meetingId?: string | null;
  chunkIds: string[];
};

export type ProcessingStage = {
  key: string;
  label: string;
  description: string;
  agentName: string;
  agentGoal: string;
  inputSource: string;
  outputTarget: string;
  fallback: string;
  outputSummary?: string;
  triggerReason?: string;
  status?: StageStatus;
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
  meetingId: string;
  title: string;
  owner: string;
  dueDate: string;
  priority: TaskPriority;
  status: ActionItemStatusValue;
  successMetrics: string[];
  rationale: string;
  sourceLabel: string;
  outputSummary: string;
  carryover: boolean;
  attributions: ArtifactAttributionData[];
};

export type ReadingItemData = {
  id: string;
  title: string;
  reason: string;
  priority: TaskPriority;
  sourceUrl: string;
  studentName: string;
  outputSummary: string;
  attributions: ArtifactAttributionData[];
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
  triggerReason: string;
  outputSummary: string;
  attributions: ArtifactAttributionData[];
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

export type BriefingItemData = {
  id: string;
  itemType: string;
  title: string;
  reason: string;
  originLayer: string;
  attributions: ArtifactAttributionData[];
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
  items: BriefingItemData[];
};

export type MemoryInUseItemData = {
  id: string;
  title: string;
  itemType: string;
  sourceMeetingId?: string | null;
  status: string;
  reason: string;
};

export type MemoryUsageData = {
  projectId: string;
  priorMeetingCount: number;
  openTaskCount: number;
  recentDecisionCount: number;
  relevantContextCount: number;
  memoryInUse: MemoryInUseItemData[];
};

export type MemoryMeetingData = {
  meetingId: string;
  title: string;
  summary: string;
  createdAt: string;
};

export type MemoryDecisionData = {
  id: string;
  meetingId?: string | null;
  meetingTitle?: string | null;
  title: string;
  rationale: string;
  decidedBy: string;
};

export type MemoryActionItemData = {
  id: string;
  meetingId?: string | null;
  meetingTitle?: string | null;
  title: string;
  owner: string;
  dueDate: string;
  priority: TaskPriority;
  status: ActionItemStatusValue;
  originLayer: string;
};

export type ProjectMemoryData = {
  projectId: string;
  projectName: string;
  meetings: MemoryMeetingData[];
  recentDecisions: MemoryDecisionData[];
  openActionItems: MemoryActionItemData[];
  briefing: BriefingData;
  memoryUsage: MemoryUsageData;
};

export type OrchestrationData = {
  controllerAgentName: string;
  llmProvider: string;
  llmModel: string;
  stages: ProcessingStage[];
  memoryUsage?: MemoryUsageData | null;
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
  orchestration: OrchestrationData;
};
