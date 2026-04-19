import type {
  DashboardLanguage,
  DeliverableKey,
  EvidenceStance,
  ProcessingStage,
  RiskLevel,
  TaskPriority,
} from "./dashboard-types";

export const navigationByLanguage: Record<DashboardLanguage, string[]> = {
  zh: ["总览", "组会", "学生", "证据", "Briefing", "记忆"],
  en: ["Dashboard", "Meetings", "Students", "Evidence", "Briefings", "Memory"],
};

export const processingStagesByLanguage: Record<DashboardLanguage, ProcessingStage[]> = {
  zh: [
    {
      key: "parse",
      label: "解析 transcript",
      description: "标准化说话人、时间戳和片段边界。",
    },
    {
      key: "progress",
      label: "提取周进展",
      description: "抽取完成项、当前结果、阻塞点和风险。",
    },
    {
      key: "ideas",
      label: "捕获导师 idea",
      description: "把导师建议转成结构化研究想法。",
    },
    {
      key: "evidence",
      label: "检索证据",
      description: "标记需要核验的 claim，并补参考依据。",
    },
    {
      key: "plan",
      label: "生成计划",
      description: "产出下周行动项、阅读建议和可导出交付物。",
    },
  ],
  en: [
    {
      key: "parse",
      label: "Transcript parsing",
      description: "Normalizing speakers, timestamps, and chunk boundaries.",
    },
    {
      key: "progress",
      label: "Progress extraction",
      description: "Pulling out completed work, current result, blockers, and risks.",
    },
    {
      key: "ideas",
      label: "Idea capture",
      description: "Converting advisor suggestions into structured research ideas.",
    },
    {
      key: "evidence",
      label: "Evidence retrieval",
      description: "Marking evidence-sensitive claims and surfacing reference cards.",
    },
    {
      key: "plan",
      label: "Plan generation",
      description: "Producing next-week actions, briefing items, and export-ready deliverables.",
    },
  ],
};

export const audioProcessingStagesByLanguage: Record<DashboardLanguage, ProcessingStage[]> = {
  zh: [
    {
      key: "audio-upload",
      label: "音频上传",
      description: "将原始会议音频保存到本地工作区。",
    },
    {
      key: "local-transcription",
      label: "本地转写",
      description: "优先使用本地 faster-whisper 生成 transcript。",
    },
    {
      key: "transcript-parse",
      label: "解析 transcript",
      description: "标准化时间戳、chunk 边界和审阅时间线。",
    },
    {
      key: "progress",
      label: "提取周进展",
      description: "抽取完成项、当前结果、阻塞点和风险。",
    },
    {
      key: "ideas",
      label: "捕获导师 idea",
      description: "把导师建议转成结构化研究想法。",
    },
    {
      key: "evidence",
      label: "检索证据",
      description: "标记需要核验的 claim，并补参考依据。",
    },
    {
      key: "plan",
      label: "生成计划",
      description: "产出下周行动项、阅读建议和可导出交付物。",
    },
  ],
  en: [
    {
      key: "audio-upload",
      label: "Audio upload",
      description: "Saving the original meeting audio into the local workspace.",
    },
    {
      key: "local-transcription",
      label: "Local transcription",
      description: "Running faster-whisper locally before any downstream agent stage.",
    },
    {
      key: "transcript-parse",
      label: "Transcript parsing",
      description: "Normalizing timestamps, chunk boundaries, and the review timeline.",
    },
    {
      key: "progress",
      label: "Progress extraction",
      description: "Pulling out completed work, current result, blockers, and risks.",
    },
    {
      key: "ideas",
      label: "Idea capture",
      description: "Converting advisor suggestions into structured research ideas.",
    },
    {
      key: "evidence",
      label: "Evidence retrieval",
      description: "Marking evidence-sensitive claims and surfacing reference cards.",
    },
    {
      key: "plan",
      label: "Plan generation",
      description: "Producing next-week actions, briefing items, and export-ready deliverables.",
    },
  ],
};

export const dashboardCopy = {
  zh: {
    brandEyebrow: "研究驾驶舱",
    brandTitle: "EvidenceFlow Agent",
    brandSubtitle: "把一次科研组会转成下周可执行计划。",
    languageLabel: "界面语言",
    activeProject: "当前项目",
    defaultProjectName: "EvidenceFlow 演示项目",
    projectDescription: "面向周组会、briefing 和证据追踪的单工作区 MVP。",
    navigationTitle: "导航",
    meetingContext: "组会上下文",
    defaultMeetingName: "演示周组会",
    fixedDemo: "固定演示样例",
    sampleNarrative:
      "这个样例包含 1 位学生进展、2 个导师 idea、3 个行动项，以及 1 个仍需证据核验的 claim。",
    meetingProcessing: "组会处理",
    uploadHeading: "导入 transcript，并把它转成下周执行计划。",
    uploadHeadingAudio: "导入会议音频，在本地转写后进入下周执行计划。",
    inputModeLabel: "输入类型",
    transcriptInputMode: "Transcript",
    audioInputMode: "Audio",
    loadDemo: "加载演示 transcript",
    process: "开始处理",
    processAudio: "处理音频",
    processing: "处理中...",
    meetingTranscript: "组会 transcript",
    importTranscriptFile: "导入 transcript 文件",
    transcriptPlaceholder: "把一段周组会 transcript 粘贴到这里。",
    selectAudioFile: "选择音频文件",
    supportedAudioFormats: "支持 .mp3 / .wav / .m4a / .mp4 / .webm",
    localTranscriptionNote: "音频会先在本地保存，再由本地 faster-whisper 完成转写。",
    selectedAudioLabel: "当前音频",
    noAudioSelected: "还没有选择音频文件。",
    clearSelectedAudio: "清空音频",
    emptyAudioUploadPrompt: "先选择一个会议音频文件，再开始处理。",
    audioReadError: "选中的音频文件无法导入。",
    resetReviewState: "重置审阅状态",
    uploadHint: "上传优先：先导入，再检查，最后导出 briefing 与交付物。",
    processingStages: "处理阶段",
    emptyUploadPrompt: "上传一段组会 transcript，系统就会生成第一版研究计划。",
    meetingSummary: "组会摘要",
    readyForReview: "可开始审阅",
    studentView: "学生视图",
    advisorIdeas: "导师想法",
    openActions: "开放行动项",
    evidenceClaims: "待核验 claim",
    progressTitle: "学生周进展",
    studentLabel: "学生",
    completed: "完成项",
    currentResult: "当前结果",
    blockers: "阻塞点",
    risks: "风险",
    nextStep: "下一步",
    advisorSignals: "导师信号",
    newIdeas: "新 idea",
    addToPlan: "加入计划",
    summary: "摘要",
    suggestedExperiment: "建议实验",
    validationMetrics: "验证指标",
    recommendedReading: "推荐阅读",
    evidenceStatus: "证据状态",
    traceability: "可追溯性",
    transcriptTimeline: "Transcript 时间线",
    transcriptHint: "点击右侧 claim，可以高亮它对应的 transcript 片段。",
    reviewState: "审阅状态",
    emptyReviewTitle: "上传一段组会 transcript，生成第一版研究计划。",
    emptyReviewBody: "界面会把计划和阅读放在主视觉位置，证据保持次级但始终可追溯。",
    execution: "执行面板",
    nextWeekPlan: "下周计划",
    actionReady: "可直接执行",
    whyTaskExists: "为什么有这个任务",
    due: "截止",
    reading: "阅读",
    agenda: "议程",
    recommendedAgenda: "建议议程",
    evidence: "证据",
    referenceBasis: "参考依据",
    evidenceEmpty: "只有当组会里出现值得核验的 claim 时，证据区才会展开。",
    evidenceSecondary: "次级展示，但可追溯",
    confidence: "置信度",
    evidenceCards: "证据卡片",
    openSource: "打开来源",
    briefing: "Briefing",
    deliveryArtifacts: "交付物",
    markdownReady: "可导出 Markdown",
    briefingEmpty: "组会处理完成后，这里会展示 briefing 项和可导出的 Markdown。",
    focusQuestions: "追问问题",
    advisorFocus: "导师下次最该追问什么",
    deliverablesAria: "交付物",
    exportMarkdown: "导出 Markdown",
  },
  en: {
    brandEyebrow: "Research Cockpit",
    brandTitle: "EvidenceFlow Agent",
    brandSubtitle: "Turn a weekly group meeting into next-week execution.",
    languageLabel: "Language",
    activeProject: "Active Project",
    defaultProjectName: "EvidenceFlow Demo Project",
    projectDescription: "Single-workspace MVP for weekly meetings, briefing prep, and evidence-aware follow-up.",
    navigationTitle: "Navigation",
    meetingContext: "Meeting Context",
    defaultMeetingName: "Demo Weekly Group Meeting",
    fixedDemo: "Fixed demo",
    sampleNarrative:
      "This sample includes one student update, two advisor ideas, three action items, and one claim that still needs evidence.",
    meetingProcessing: "Meeting Processing",
    uploadHeading: "Import a transcript and turn it into next-week execution.",
    uploadHeadingAudio: "Import meeting audio, transcribe it locally, and turn it into next-week execution.",
    inputModeLabel: "Input mode",
    transcriptInputMode: "Transcript",
    audioInputMode: "Audio",
    loadDemo: "Load Demo Transcript",
    process: "Process Transcript",
    processAudio: "Process Audio",
    processing: "Processing...",
    meetingTranscript: "Meeting transcript",
    importTranscriptFile: "Import transcript file",
    transcriptPlaceholder: "Paste a weekly research meeting transcript here.",
    selectAudioFile: "Select audio file",
    supportedAudioFormats: "Supports .mp3 / .wav / .m4a / .mp4 / .webm",
    localTranscriptionNote: "Audio is saved locally first, then transcribed with local faster-whisper.",
    selectedAudioLabel: "Selected audio",
    noAudioSelected: "No audio file selected yet.",
    clearSelectedAudio: "Clear audio",
    emptyAudioUploadPrompt: "Select a meeting audio file before processing.",
    audioReadError: "The selected audio file could not be loaded.",
    resetReviewState: "Reset Review State",
    uploadHint: "Upload-first flow: import, inspect, then export briefing-ready outputs.",
    processingStages: "Processing Stages",
    emptyUploadPrompt: "Upload a meeting transcript to generate the first research plan.",
    meetingSummary: "Meeting Summary",
    readyForReview: "Ready for review",
    studentView: "student view",
    advisorIdeas: "advisor ideas",
    openActions: "open actions",
    evidenceClaims: "evidence claims",
    progressTitle: "Student Progress",
    studentLabel: "Student",
    completed: "Completed",
    currentResult: "Current Result",
    blockers: "Blockers",
    risks: "Risks",
    nextStep: "Next Step",
    advisorSignals: "Advisor Signals",
    newIdeas: "New Ideas",
    addToPlan: "Add to plan",
    summary: "Summary",
    suggestedExperiment: "Suggested Experiment",
    validationMetrics: "Validation Metrics",
    recommendedReading: "Recommended Reading",
    evidenceStatus: "Evidence Status",
    traceability: "Traceability",
    transcriptTimeline: "Transcript Timeline",
    transcriptHint: "Click a claim in the evidence panel to highlight source chunks.",
    reviewState: "Review State",
    emptyReviewTitle: "Upload a meeting transcript to generate the first research plan.",
    emptyReviewBody: "The dashboard keeps planning and reading visually primary, with evidence visible but secondary.",
    execution: "Execution",
    nextWeekPlan: "Next-Week Plan",
    actionReady: "Action-ready",
    whyTaskExists: "Why this task exists",
    due: "due",
    reading: "Reading",
    agenda: "Agenda",
    recommendedAgenda: "Recommended Agenda",
    evidence: "Evidence",
    referenceBasis: "Reference Basis",
    evidenceEmpty: "The evidence lane appears only when the meeting contains a claim worth checking.",
    evidenceSecondary: "Secondary but traceable",
    confidence: "confidence",
    evidenceCards: "Evidence Cards",
    openSource: "Open source",
    briefing: "Briefing",
    deliveryArtifacts: "Delivery Artifacts",
    markdownReady: "Markdown-ready",
    briefingEmpty: "Once the meeting is processed, this panel exposes briefing items and exportable Markdown.",
    focusQuestions: "Focus Questions",
    advisorFocus: "What the advisor should press on",
    deliverablesAria: "Deliverables",
    exportMarkdown: "Export Markdown",
  },
} as const;

export function getRiskLabel(language: DashboardLanguage, level: RiskLevel) {
  if (language === "zh") {
    if (level === "high") return "高风险";
    if (level === "medium") return "中风险";
    return "低风险";
  }
  if (level === "high") return "High risk";
  if (level === "medium") return "Medium risk";
  return "Low risk";
}

export function getPriorityText(language: DashboardLanguage, priority: TaskPriority) {
  if (language === "zh") {
    if (priority === "high") return "高";
    if (priority === "medium") return "中";
    return "低";
  }
  return priority;
}

export function getStatusText(language: DashboardLanguage, status: string) {
  if (language !== "zh") return status;
  const normalized = status.trim().toLowerCase();
  if (normalized === "open") return "未开始";
  if (normalized === "in progress" || normalized === "in_progress") return "进行中";
  if (normalized === "blocked") return "阻塞";
  if (normalized === "done") return "已完成";
  return status;
}

export function getVerdictLabel(
  language: DashboardLanguage,
  verdict: "supported" | "contradicted" | "needs_verification"
) {
  if (language === "zh") {
    if (verdict === "supported") return "已支持";
    if (verdict === "contradicted") return "被反驳";
    return "待核验";
  }
  if (verdict === "needs_verification") {
    return "Needs verification";
  }
  return verdict.charAt(0).toUpperCase() + verdict.slice(1);
}

export function getEvidenceStanceLabel(language: DashboardLanguage, stance: EvidenceStance) {
  if (language === "zh") {
    if (stance === "support") return "支持";
    if (stance === "contradict") return "反驳";
    return "待核验";
  }
  return stance;
}

export function getDeliverableLabel(language: DashboardLanguage, key: DeliverableKey) {
  if (language === "zh") {
    if (key === "weekly-report") return "周报";
    if (key === "next-meeting-briefing") return "下次组会 Briefing";
    if (key === "next-week-plan") return "下周计划";
    return "汇报提纲";
  }
  if (key === "weekly-report") return "Weekly Report";
  if (key === "next-meeting-briefing") return "Briefing";
  if (key === "next-week-plan") return "Next-Week Plan";
  return "Presentation Outline";
}
