"use client";

import type {
  BriefingData,
  DeliverableKey,
  DeliverablePreview,
} from "./dashboard-types";

type BriefingPanelProps = {
  briefing: BriefingData;
  deliverables: DeliverablePreview[];
  selectedDeliverableKey: DeliverableKey | null;
  isReady: boolean;
  onSelectDeliverable: (key: DeliverableKey) => void;
  onExportDeliverable: (deliverable: DeliverablePreview) => void;
};

export function BriefingPanel({
  briefing,
  deliverables,
  selectedDeliverableKey,
  isReady,
  onSelectDeliverable,
  onExportDeliverable,
}: BriefingPanelProps) {
  const selectedDeliverable =
    deliverables.find((item) => item.key === selectedDeliverableKey) ?? deliverables[0] ?? null;

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Briefing</p>
          <h3>Delivery Artifacts</h3>
        </div>
        <span className="status-pill status-pill-brand">Markdown-ready</span>
      </div>

      {!isReady ? (
        <div className="empty-panel">
          <p>Once the meeting is processed, this panel exposes briefing items and exportable Markdown.</p>
        </div>
      ) : (
        <>
          <p className="briefing-summary">{briefing.summary}</p>

          <div className="subsection">
            <div className="subsection-header">
              <p className="eyebrow">Focus Questions</p>
              <h4>What the advisor should press on</h4>
            </div>
            <ul className="agenda-list">
              {briefing.focusQuestions.map((question) => (
                <li key={question}>
                  <p>{question}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="deliverable-tabs" role="tablist" aria-label="Deliverables">
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
                {deliverable.label}
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
                  Export Markdown
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
