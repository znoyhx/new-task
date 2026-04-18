import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";

import DashboardPage from "../../app/page";
import { ActionItemsPanel } from "../action-items-panel";
import { BriefingPanel } from "../briefing-panel";
import { demoDashboardResult, demoTranscript, processingStages } from "../dashboard-data";
import { EvidencePanel } from "../evidence-panel";
import { MeetingUpload } from "../meeting-upload";

function runDashboardShellTest() {
  const markup = renderToStaticMarkup(<DashboardPage />);

  assert.match(markup, /EvidenceFlow Agent/);
  assert.match(markup, /Import a transcript and turn it into next-week execution\./);
  assert.match(markup, /Load Demo Transcript/);
  assert.match(markup, /Upload a meeting transcript to generate the first research plan\./);
}

function runPanelRenderTest() {
  const markup = renderToStaticMarkup(
    <>
      <ActionItemsPanel
        actionItems={demoDashboardResult.actionItems}
        readingList={demoDashboardResult.readingList}
        agenda={demoDashboardResult.briefing.recommendedAgenda}
        isReady
      />
      <EvidencePanel
        claims={demoDashboardResult.claims}
        activeClaimId={demoDashboardResult.claims[0]?.id ?? null}
        isReady
        onSelectClaim={() => {}}
      />
      <BriefingPanel
        briefing={demoDashboardResult.briefing}
        deliverables={demoDashboardResult.deliverables}
        selectedDeliverableKey={demoDashboardResult.deliverables[0]?.key ?? null}
        isReady
        onSelectDeliverable={() => {}}
        onExportDeliverable={() => {}}
      />
    </>
  );

  assert.match(markup, /Next-Week Plan/);
  assert.match(markup, /Curriculum Learning for Robust Classification/);
  assert.match(markup, /Needs verification/);
  assert.match(markup, /Export Markdown/);
}

function runProcessingStageTest() {
  const markup = renderToStaticMarkup(
    <MeetingUpload
      transcriptText={demoTranscript}
      runState="loading"
      activeStageIndex={2}
      errorMessage=""
      stages={processingStages}
      onTranscriptChange={() => {}}
      onTranscriptFileLoad={() => {}}
      onLoadDemo={() => {}}
      onProcess={() => {}}
      onReset={() => {}}
    />
  );

  assert.match(markup, /Transcript parsing/);
  assert.match(markup, /Progress extraction/);
  assert.match(markup, /Idea capture/);
  assert.match(markup, /Evidence retrieval/);
  assert.match(markup, /Plan generation/);
  assert.match(markup, /Meeting transcript/);
}

runDashboardShellTest();
runPanelRenderTest();
runProcessingStageTest();
console.log("frontend dashboard tests passed");
