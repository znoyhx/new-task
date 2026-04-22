"use client";

import {
  dashboardCopy,
  getEvidenceStanceLabel,
  getOriginLayerLabel,
  getVerdictLabel,
} from "./dashboard-copy";
import type { ClaimData, DashboardLanguage } from "./dashboard-types";

type EvidencePanelProps = {
  language: DashboardLanguage;
  claims: ClaimData[];
  activeClaimId: string | null;
  isReady: boolean;
  onSelectClaim: (claimId: string) => void;
};

export function EvidencePanel({
  language,
  claims,
  activeClaimId,
  isReady,
  onSelectClaim,
}: EvidencePanelProps) {
  const copy = dashboardCopy[language];

  if (!isReady) {
    return (
      <section className="panel">
        <div className="panel-header compact-header">
          <div>
            <p className="eyebrow">{copy.evidence}</p>
            <h3>{copy.referenceBasis}</h3>
          </div>
        </div>
        <div className="empty-panel">
          <p>{copy.evidenceEmpty}</p>
        </div>
      </section>
    );
  }

  const activeClaim = claims.find((claim) => claim.id === activeClaimId) ?? claims[0] ?? null;

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">{copy.evidence}</p>
          <h3>{copy.referenceBasis}</h3>
        </div>
        <span className="status-pill status-pill-soft">{copy.evidenceSecondary}</span>
      </div>

      <div className="claim-list">
        {claims.map((claim) => (
          <button
            key={claim.id}
            className={`claim-card ${claim.id === activeClaim?.id ? "claim-card-active" : ""}`}
            type="button"
            onClick={() => onSelectClaim(claim.id)}
          >
            <div className="claim-card-top">
              <strong>{claim.text}</strong>
              <span className={`stance-pill stance-${claim.verdict.replace("_", "-")}`}>
                {getVerdictLabel(language, claim.verdict)}
              </span>
            </div>
            <p className="claim-meta">
              {claim.speaker} / {copy.confidence} {claim.confidence}
            </p>
            <p>{claim.transcriptSnippet}</p>
            <p className="supporting-copy">{claim.triggerReason}</p>
          </button>
        ))}
      </div>

      {activeClaim ? (
        <div className="subsection">
          <div className="subsection-header">
            <p className="eyebrow">{copy.evidenceCards}</p>
            <h4>{getVerdictLabel(language, activeClaim.verdict)}</h4>
          </div>
          <ul className="evidence-list">
            <li className="evidence-card">
              <strong>{activeClaim.outputSummary}</strong>
              <ul className="explanation-list">
                {activeClaim.attributions.map((attribution) => (
                  <li key={`${activeClaim.id}-${attribution.label}`}>
                    <strong>{getOriginLayerLabel(language, attribution.originLayer)}</strong>
                    <p>{`${attribution.label}: ${attribution.detail}`}</p>
                  </li>
                ))}
              </ul>
            </li>
            {activeClaim.evidenceCards.map((card) => (
              <li className="evidence-card" key={card.id}>
                <div className="evidence-card-top">
                  <strong>{card.sourceTitle}</strong>
                  <span className={`stance-pill stance-${card.stance.replace(" ", "-")}`}>
                    {getEvidenceStanceLabel(language, card.stance)}
                  </span>
                </div>
                <p>{card.snippet}</p>
                <div className="evidence-footer">
                  <span>
                    {card.sourceType} / {copy.confidence} {card.confidence}
                  </span>
                  <a href={card.sourceUrl} target="_blank" rel="noreferrer">
                    {copy.openSource}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
