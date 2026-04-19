import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import DashboardPage from "../../app/page";
import { ActionItemsPanel } from "../action-items-panel";
import { BriefingPanel } from "../briefing-panel";
import { demoDashboardResult } from "../dashboard-data";
import { processingStagesByLanguage } from "../dashboard-copy";
import { EvidencePanel } from "../evidence-panel";
import { MeetingUpload } from "../meeting-upload";

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
      />
    </>
  );

  assert.match(markup, /下周计划/);
  assert.match(markup, /Curriculum Learning for Robust Classification/);
  assert.match(markup, /待核验/);
  assert.match(markup, /导出 Markdown/);
}

function runProcessingStageTest() {
  const markup = renderToStaticMarkup(
    <MeetingUpload
      language="zh"
      transcriptText="示例 transcript"
      runState="loading"
      activeStageIndex={2}
      errorMessage=""
      stages={processingStagesByLanguage.zh}
      onTranscriptChange={() => {}}
      onTranscriptFileLoad={() => {}}
      onLoadDemo={() => {}}
      onProcess={() => {}}
      onReset={() => {}}
    />
  );

  assert.match(markup, /解析 transcript/);
  assert.match(markup, /提取周进展/);
  assert.match(markup, /捕获导师 idea/);
  assert.match(markup, /检索证据/);
  assert.match(markup, /生成计划/);
  assert.match(markup, /组会 transcript/);
}

runDashboardShellTest();
runPanelRenderTest();
runProcessingStageTest();
console.log("frontend dashboard tests passed");
