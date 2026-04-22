import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import DashboardPage from "../../app/page";
import { ActionItemsPanel } from "../action-items-panel";
import { BriefingPanel } from "../briefing-panel";
import { demoDashboardResult } from "../dashboard-data";
import { processingStagesByLanguage } from "../dashboard-copy";
import { EvidencePanel } from "../evidence-panel";
import { MeetingUpload } from "../meeting-upload";
import { MemoryPanel } from "../memory-panel";

function runDashboardShellTest() {
  const markup = renderToStaticMarkup(<DashboardPage />);

  assert.match(markup, /EvidenceFlow Agent/);
  assert.match(markup, /界面语言/);
  assert.match(markup, /导入 transcript，并把它转成下周执行计划。/);
  assert.match(markup, /加载演示 transcript/);
  assert.match(markup, /上传一段组会 transcript，生成第一版研究计划。/);
}

function runPanelRenderTest() {
  const markup = renderToStaticMarkup(
    <>
      <ActionItemsPanel
        language="zh"
        actionItems={demoDashboardResult.actionItems}
        readingList={demoDashboardResult.readingList}
        agenda={demoDashboardResult.briefing.recommendedAgenda}
        isReady
        onUpdateStatus={() => {}}
      />
      <EvidencePanel
        language="zh"
        claims={demoDashboardResult.claims}
        activeClaimId={demoDashboardResult.claims[0]?.id ?? null}
        isReady
        onSelectClaim={() => {}}
      />
      <BriefingPanel
        language="zh"
        briefing={demoDashboardResult.briefing}
        deliverables={demoDashboardResult.deliverables}
        selectedDeliverableKey={demoDashboardResult.deliverables[0]?.key ?? null}
        isReady
        onSelectDeliverable={() => {}}
        onExportDeliverable={() => {}}
        memoryUsage={demoDashboardResult.orchestration.memoryUsage ?? null}
      />
      <MemoryPanel
        language="en"
        memory={{
          projectId: "project-001",
          projectName: "Integration Project",
          meetings: [
            {
              meetingId: "meeting-history-001",
              title: "History Meeting",
              summary: "Original ablation request.",
              createdAt: "April 11, 2026",
            },
          ],
          recentDecisions: [
            {
              id: "decision-001",
              meetingId: "meeting-history-001",
              meetingTitle: "History Meeting",
              title: "Keep the ablation in scope",
              rationale: "It remains the fastest validation path.",
              decidedBy: "Prof. Chen",
            },
          ],
          openActionItems: [
            {
              id: "meeting-history-001::carry forward the ablation checklist::alice",
              meetingId: "meeting-history-001",
              meetingTitle: "History Meeting",
              title: "Carry forward the ablation checklist",
              owner: "Alice",
              dueDate: "Friday",
              priority: "high",
              status: "open",
              originLayer: "history_memory",
            },
          ],
          briefing: {
            summary: "Project memory summary.",
            focusQuestions: ["What still blocks execution?"],
            recommendedAgenda: [],
            items: [
              {
                id: "briefing-001",
                itemType: "carryover_task",
                title: "Carry forward the ablation checklist",
                reason: "Still unfinished and relevant this week.",
                originLayer: "history_memory",
                attributions: [],
              },
            ],
          },
          memoryUsage: {
            projectId: "project-001",
            priorMeetingCount: 1,
            openTaskCount: 1,
            recentDecisionCount: 1,
            relevantContextCount: 0,
            memoryInUse: [],
          },
        }}
        isReady
        isLoading={false}
        errorMessage=""
      />
    </>
  );

  assert.match(markup, /下周计划/);
  assert.match(markup, /Curriculum Learning for Robust Classification/);
  assert.match(markup, /待核验/);
  assert.match(markup, /导出 Markdown/);
  assert.match(markup, /Project Memory/);
  assert.match(markup, /Carry forward the ablation checklist/);
}

function runProcessingStageTest() {
  const markup = renderToStaticMarkup(
    <MeetingUpload
      language="zh"
      transcriptText="绀轰緥 transcript"
      runState="loading"
      activeStageIndex={2}
      errorMessage=""
      stages={processingStagesByLanguage.zh}
      onTranscriptChange={() => {}}
      onTranscriptFileLoad={() => {}}
      onLoadDemo={() => {}}
      onProcess={() => {}}
      onReset={() => {}}
      activeOrchestrationStage={processingStagesByLanguage.zh[2]}
    />
  );

  assert.match(markup, /解析 transcript/);
  assert.match(markup, /提取周进展/);
  assert.match(markup, /捕获导师 idea/);
  assert.match(markup, /检索证据/);
  assert.match(markup, /生成计划/);
  assert.match(markup, /组会 transcript/);
  assert.match(markup, /Agent 编排/);
}

runDashboardShellTest();
runPanelRenderTest();
runProcessingStageTest();
console.log("frontend dashboard tests passed");
