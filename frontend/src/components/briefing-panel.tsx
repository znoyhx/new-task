"use client";

import { dashboardCopy, getDeliverableLabel } from "./dashboard-copy";
import type {
  BriefingData,
  DashboardLanguage,
  DeliverableKey,
  DeliverablePreview,
} from "./dashboard-types";

type BriefingPanelProps = {
  language: DashboardLanguage;
  briefing: BriefingData;
  deliverables: DeliverablePreview[];
  selectedDeliverableKey: DeliverableKey | null;
  isReady: boolean;
  onSelectDeliverable: (key: DeliverableKey) => void;
  onExportDeliverable: (deliverable: DeliverablePreview) => void;
};

export function BriefingPanel({
  language,
  briefing,
  deliverables,
  selectedDeliverableKey,
  isReady,
  onSelectDeliverable,
  onExportDeliverable,
}: BriefingPanelProps) {
  const copy = dashboardCopy[language];
  const selectedDeliverable =
    deliverables.find((item) => item.key === selectedDeliverableKey) ?? deliverables[0] ?? null;

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">{copy.briefing}</p>
          <h3>{copy.deliveryArtifacts}</h3>
        </div>
        <span className="status-pill status-pill-brand">{copy.markdownReady}</span>
      </div>

      {!isReady ? (
        <div className="empty-panel">
          <p>{copy.briefingEmpty}</p>
        </div>
      ) : (
        <>
          <p className="briefing-summary">{briefing.summary}</p>

          <div className="subsection">
            <div className="subsection-header">
              <p className="eyebrow">{copy.focusQuestions}</p>
              <h4>{copy.advisorFocus}</h4>
            </div>
            <ul className="agenda-list">
              {briefing.focusQuestions.map((question) => (
                <li key={question}>
                  <p>{question}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="deliverable-tabs" role="tablist" aria-label={copy.deliverablesAria}>
            {deliverables.map((deliverable) => (
              <button
                key={deliverable.key}
                type="button"
                role="tab"
                aria-selected={deliverable.key === selectedDeliverable?.key}
                className={`deliverable-tab ${
                  deliverable.key === selectedDeliverable?.key ? "deliverable-tab-active" : ""
                }`}
                onClick={() => onSelectDeliverable(deliverable.key)}
              >
                {getDeliverableLabel(language, deliverable.key)}
              </button>
            ))}
          </div>

          {selectedDeliverable ? (
            <div className="deliverable-preview">
              <div className="deliverable-preview-header">
                <strong>{selectedDeliverable.title}</strong>
                <button
                  className="button button-secondary button-mini"
                  type="button"
                  onClick={() => onExportDeliverable(selectedDeliverable)}
                >
                  {copy.exportMarkdown}
                </button>
              </div>
              <pre>{selectedDeliverable.content}</pre>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
