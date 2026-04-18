import type {
  DashboardResultData,
  ProcessingStage,
} from "./dashboard-types";

export const navigation = [
  "Dashboard",
  "Meetings",
  "Students",
  "Evidence",
  "Briefings",
  "Memory",
];

export const processingStages: ProcessingStage[] = [
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
];

export const demoTranscript = `[00:00:06] Alice: This week I reran the curriculum-learning baseline on the reviewer-comment benchmark and reached 74 percent macro F1.
[00:00:18] Alice: The improvement comes mostly from hard examples, but calibration still gets worse after the third curriculum stage.
[00:00:31] Alice: I still do not have a clean ablation table, and the long-context runs fail when logging token-level evidence.
[00:00:46] Prof. Chen: Keep the hard-negative curriculum ablation in next week's plan and report macro F1 plus calibration error.
[00:00:59] Prof. Chen: Also test retrieval-assisted logging so we can trace every action item back to a transcript slice.
[00:01:12] Prof. Chen: Before the next meeting, read one paper on curriculum learning, one on calibration under imbalance, and one on retrieval-grounded meeting agents.
[00:01:26] Bob: I can help instrument the logging pipeline if Alice shares the failing traces.
[00:01:39] Prof. Chen: One claim we should verify is whether curriculum learning consistently improves hard-example macro F1 in small-data settings.`;

export const demoDashboardResult: DashboardResultData = {
  projectId: "evidenceflow-demo-project",
  meetingId: "demo-meeting-001",
  projectName: "EvidenceFlow Demo Project",
  meetingTitle: "Demo Weekly Group Meeting",
  meetingDate: "April 18, 2026",
  meetingStatus: "Processed",
  processingNote:
    "The meeting produced one strong student progress summary, two advisor ideas, three next-week actions, and one evidence-sensitive claim.",
  summary:
    "Alice improved hard-example macro F1 with the curriculum-learning rerun, but calibration still regresses and retrieval logging fails on long-context runs. The advisor pushed one validation experiment and one traceability workflow change for next week.",
  studentProgress: [
    {
      studentName: "Alice",
      completedWork: [
        "Reran the curriculum-learning baseline on the reviewer-comment benchmark.",
      ],
      currentResult:
        "Macro F1 improved on hard examples, but calibration worsens after the third curriculum stage.",
      blockers: [
        "The ablation table is still incomplete.",
        "Token-level logging fails on long-context runs.",
      ],
      riskLevel: "high",
      risks: [
        "Calibration still regresses after the final curriculum stage.",
        "Trace logging crashes before evidence links are written.",
      ],
      nextStep:
        "Finalize the hard-negative ablation table and isolate the logging failure before the next meeting.",
      unresolvedQuestions: [
        "Can the hard-example gain survive without hurting calibration error?",
      ],
    },
  ],
  advisorIdeas: [
    {
      id: "idea-hard-negative",
      title: "Keep the hard-negative ablation in next week's plan",
      summary:
        "The advisor wants a tighter validation pass on the hard-example improvement, not another broad experiment branch.",
      suggestedExperiment:
        "Run one final hard-negative curriculum ablation and report both macro F1 and calibration error.",
      recommendedReading: [
        "Curriculum Learning for Robust Classification",
        "Calibration Under Distribution Shift",
      ],
      validationMetrics: ["macro F1", "calibration error"],
      evidenceStatus: "Validation-first, evidence optional",
      sourceChunkIds: ["chunk-0004"],
    },
    {
      id: "idea-traceability",
      title: "Test retrieval-assisted logging for transcript traceability",
      summary:
        "The workflow should keep every exported action item attached to one transcript slice so the advisor can jump straight to source context.",
      suggestedExperiment:
        "Instrument retrieval-assisted logging on the failing long-context run and confirm every task keeps one trace anchor.",
      recommendedReading: [
        "Grounded Meeting Agents With Retrieval Traces",
      ],
      validationMetrics: ["trace coverage"],
      evidenceStatus: "Helpful for demo credibility",
      sourceChunkIds: ["chunk-0005"],
    },
  ],
  actionItems: [
    {
      id: "task-001",
      title: "Prepare the hard-negative curriculum ablation table",
      owner: "Alice",
      dueDate: "Friday",
      priority: "high",
      status: "open",
      successMetrics: ["macro F1", "calibration error"],
      rationale:
        "This is the fastest path to validate the advisor's main request for next week.",
      sourceLabel: "Derived from advisor idea + current blocker",
    },
    {
      id: "task-002",
      title: "Instrument retrieval-assisted logging for transcript traceability",
      owner: "Bob",
      dueDate: "Tuesday",
      priority: "medium",
      status: "in progress",
      successMetrics: ["trace coverage"],
      rationale:
        "The dashboard demo depends on showing an action item that can jump back to a transcript slice.",
      sourceLabel: "Derived from advisor idea",
    },
    {
      id: "task-003",
      title: "Share the failing traces with Bob",
      owner: "Alice",
      dueDate: "Monday",
      priority: "medium",
      status: "open",
      successMetrics: ["trace bundle delivered"],
      rationale:
        "Bob cannot finish the logging fix until Alice passes over the failing traces.",
      sourceLabel: "Derived from discussion follow-up",
    },
  ],
  readingList: [
    {
      id: "reading-001",
      title: "Curriculum Learning for Robust Classification",
      reason:
        "Use this first to tighten the hard-negative experiment and keep the ablation small.",
      priority: "high",
      sourceUrl: "https://example.org/curriculum",
      studentName: "Alice",
    },
    {
      id: "reading-002",
      title: "Calibration Under Distribution Shift",
      reason:
        "This one is the fastest entry point for diagnosing the calibration regression after stage three.",
      priority: "high",
      sourceUrl: "https://example.org/calibration",
      studentName: "Alice",
    },
    {
      id: "reading-003",
      title: "Grounded Meeting Agents With Retrieval Traces",
      reason:
        "Read this before instrumenting the logging pipeline so the demo keeps a visible evidence trail.",
      priority: "medium",
      sourceUrl: "https://example.org/retrieval",
      studentName: "Bob",
    },
  ],
  claims: [
    {
      id: "claim-001",
      text:
        "Curriculum learning consistently improves hard-example macro F1 in small-data settings.",
      speaker: "Prof. Chen",
      verdict: "needs_verification",
      confidence: "medium",
      transcriptSnippet:
        "One claim we should verify is whether curriculum learning consistently improves hard-example macro F1 in small-data settings.",
      sourceChunkIds: ["chunk-0008"],
      evidenceCards: [
        {
          id: "evidence-001",
          sourceTitle: "Curriculum Learning for Robust Classification",
          sourceUrl: "https://example.org/curriculum",
          sourceType: "paper",
          stance: "needs verification",
          confidence: "medium",
          snippet:
            "The paper reports gains on hard examples, but does not isolate the small-data condition strongly enough.",
        },
      ],
    },
  ],
  transcriptTimeline: [
    {
      chunkId: "chunk-0001",
      timestamp: "00:00:06",
      speaker: "Alice",
      text:
        "This week I reran the curriculum-learning baseline on the reviewer-comment benchmark and reached 74 percent macro F1.",
    },
    {
      chunkId: "chunk-0002",
      timestamp: "00:00:18",
      speaker: "Alice",
      text:
        "The improvement comes mostly from hard examples, but calibration still gets worse after the third curriculum stage.",
    },
    {
      chunkId: "chunk-0003",
      timestamp: "00:00:31",
      speaker: "Alice",
      text:
        "I still do not have a clean ablation table, and the long-context runs fail when logging token-level evidence.",
    },
    {
      chunkId: "chunk-0004",
      timestamp: "00:00:46",
      speaker: "Prof. Chen",
      text:
        "Keep the hard-negative curriculum ablation in next week's plan and report macro F1 plus calibration error.",
    },
    {
      chunkId: "chunk-0005",
      timestamp: "00:00:59",
      speaker: "Prof. Chen",
      text:
        "Also test retrieval-assisted logging so we can trace every action item back to a transcript slice.",
    },
    {
      chunkId: "chunk-0006",
      timestamp: "00:01:12",
      speaker: "Prof. Chen",
      text:
        "Before the next meeting, read one paper on curriculum learning, one on calibration under imbalance, and one on retrieval-grounded meeting agents.",
    },
    {
      chunkId: "chunk-0007",
      timestamp: "00:01:26",
      speaker: "Bob",
      text:
        "I can help instrument the logging pipeline if Alice shares the failing traces.",
    },
    {
      chunkId: "chunk-0008",
      timestamp: "00:01:39",
      speaker: "Prof. Chen",
      text:
        "One claim we should verify is whether curriculum learning consistently improves hard-example macro F1 in small-data settings.",
    },
  ],
  briefing: {
    summary:
      "Briefing for the next meeting: two advisor ideas need validation, three open tasks are still active, and the calibration regression remains the top risk.",
    focusQuestions: [
      "Can Alice keep the hard-example gain without worsening calibration error?",
      "Will Bob recover trace coverage on the long-context logging failure before Tuesday?",
      "Does the small-data curriculum-learning claim need stronger external evidence?",
    ],
    recommendedAgenda: [
      {
        title: "Address the calibration regression before anything else",
        reason:
          "It is the highest-risk blocker in the current meeting state and directly affects the main experiment.",
        priority: "high",
      },
      {
        title: "Review the hard-negative ablation table",
        reason:
          "This is the clearest validation artifact for the advisor's top idea.",
        priority: "high",
      },
      {
        title: "Check retrieval-assisted logging trace coverage",
        reason:
          "The demo's transcript traceability depends on this workflow fix.",
        priority: "medium",
      },
    ],
  },
  deliverables: [
    {
      key: "weekly-report",
      label: "Weekly Report",
      title: "Weekly Report - EvidenceFlow Demo Project",
      content: `# Weekly Report: EvidenceFlow Demo Project

## Meeting
- Demo Weekly Group Meeting
- Alice improved hard-example macro F1, but calibration still regresses and retrieval logging fails on long-context runs.

## Student Progress
- Alice reran the curriculum-learning baseline and improved hard-example macro F1.
- The current blocker is the incomplete ablation table plus the logging failure.

## Advisor Ideas
- Keep the hard-negative curriculum ablation in next week's plan.
- Test retrieval-assisted logging for transcript traceability.

## Open Tasks
- Prepare the hard-negative curriculum ablation table.
- Instrument retrieval-assisted logging for transcript traceability.
- Share the failing traces with Bob.`,
    },
    {
      key: "next-meeting-briefing",
      label: "Briefing",
      title: "Briefing - EvidenceFlow Demo Project",
      content: `# Next Meeting Briefing

## Summary
Two advisor ideas need validation, three open tasks remain, and calibration regression is still the top risk.

## Recommended Agenda
- Address the calibration regression.
- Review the hard-negative ablation table.
- Check retrieval-assisted logging trace coverage.

## Focus Questions
- Can the gain survive without hurting calibration?
- Will trace coverage survive the long-context logging failure?
- Does the small-data claim need stronger evidence?`,
    },
    {
      key: "next-week-plan",
      label: "Next-Week Plan",
      title: "Next-Week Plan - EvidenceFlow Demo Project",
      content: `# Next-Week Research Plan

## Priority Tasks
- Finalize the hard-negative ablation and calibration report.
- Enable retrieval-assisted logging on the failing long-context run.
- Share the failing traces with Bob.

## Recommended Reading
- Curriculum Learning for Robust Classification
- Calibration Under Distribution Shift
- Grounded Meeting Agents With Retrieval Traces`,
    },
    {
      key: "presentation-outline",
      label: "Presentation Outline",
      title: "Presentation Outline - EvidenceFlow Demo Project",
      content: `# Presentation Outline

## 1. What happened this week
- Alice reran the curriculum-learning baseline and improved hard-example macro F1.

## 2. What still blocks execution
- Calibration still regresses after stage three.
- Retrieval logging fails on long-context runs.

## 3. What happens next
- Show the ablation table.
- Show the trace logging fix.
- Close the evidence gap around the small-data claim.`,
    },
  ],
};
