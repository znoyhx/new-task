"use client";

import type { ClaimData } from "./dashboard-types";

type EvidencePanelProps = {
  claims: ClaimData[];
  activeClaimId: string | null;
  isReady: boolean;
  onSelectClaim: (claimId: string) => void;
};

function formatVerdict(verdict: ClaimData["verdict"]) {
  if (verdict === "needs_verification") {
    return "Needs verification";
  }
  return verdict.charAt(0).toUpperCase() + verdict.slice(1);
}

export function EvidencePanel({
  claims,
  activeClaimId,
  isReady,
  onSelectClaim,
}: EvidencePanelProps) {
  if (!isReady) {
    return (
      <section className="panel">
        <div className="panel-header compact-header">
          <div>
            <p className="eyebrow">Evidence</p>
            <h3>Reference Basis</h3>
          </div>
        </div>
        <div className="empty-panel">
          <p>The evidence lane appears only when the meeting contains a claim worth checking.</p>
        </div>
      </section>
    );
  }

  const activeClaim = claims.find((claim) => claim.id === activeClaimId) ?? claims[0] ?? null;

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Evidence</p>
          <h3>Reference Basis</h3>
        </div>
        <span className="status-pill status-pill-soft">Secondary but traceable</span>
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
                {formatVerdict(claim.verdict)}
              </span>
            </div>
            <p className="claim-meta">
              {claim.speaker} / confidence {claim.confidence}
            </p>
            <p>{claim.transcriptSnippet}</p>
          </button>
        ))}
      </div>

      {activeClaim ? (
        <div className="subsection">
          <div className="subsection-header">
            <p className="eyebrow">Evidence Cards</p>
            <h4>{formatVerdict(activeClaim.verdict)}</h4>
          </div>
          <ul className="evidence-list">
            {activeClaim.evidenceCards.map((card) => (
              <li className="evidence-card" key={card.id}>
                <div className="evidence-card-top">
                  <strong>{card.sourceTitle}</strong>
                  <span className={`stance-pill stance-${card.stance.replace(" ", "-")}`}>
                    {card.stance}
                  </span>
                </div>
                <p>{card.snippet}</p>
                <div className="evidence-footer">
                  <span>
                    {card.sourceType} / confidence {card.confidence}
                  </span>
                  <a href={card.sourceUrl} target="_blank" rel="noreferrer">
                    Open source
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
