"use client";

import { startTransition, useState } from "react";

import {
  demoTranscript,
  navigation,
  processingStages,
} from "./dashboard-data";
import { ActionItemsPanel } from "./action-items-panel";
import { fetchDeliverable, processMeetingTranscript } from "./dashboard-api";
import { BriefingPanel } from "./briefing-panel";
import { EvidencePanel } from "./evidence-panel";
import { MeetingUpload } from "./meeting-upload";
import type {
  DashboardResultData,
  DashboardRunState,
  DeliverableKey,
  DeliverablePreview,
  RiskLevel,
} from "./dashboard-types";

function formatRiskLabel(level: RiskLevel) {
  if (level === "high") {
    return "High risk";
  }
  if (level === "medium") {
    return "Medium risk";
  }
  return "Low risk";
}

export function DashboardWorkspace() {
  const [transcriptText, setTranscriptText] = useState("");
  const [runState, setRunState] = useState<DashboardRunState>("idle");
  const [activeStageIndex, setActiveStageIndex] = useState(-1);
  const [errorMessage, setErrorMessage] = useState("");
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [selectedDeliverableKey, setSelectedDeliverableKey] =
    useState<DeliverableKey | null>("weekly-report");
  const [result, setResult] = useState<DashboardResultData | null>(null);

  const isReady = runState === "ready" && result !== null;
  const activeClaim = result?.claims.find((claim) => claim.id === activeClaimId) ?? result?.claims[0] ?? null;
  const highlightedChunkIds = activeClaim?.sourceChunkIds ?? [];

  async function handleProcess() {
    if (!transcriptText.trim()) {
      setRunState("error");
      setErrorMessage("Paste a meeting transcript or load the fixed demo sample first.");
      return;
    }

    setErrorMessage("");
    setRunState("loading");
    setResult(null);
    setActiveClaimId(null);
    setActiveStageIndex(0);

    const stageTimer = window.setInterval(() => {
      setActiveStageIndex((currentIndex) => {
        if (currentIndex >= processingStages.length - 1) {
          return currentIndex;
        }
        return currentIndex + 1;
      });
    }, 650);

    try {
      const processedResult = await processMeetingTranscript(transcriptText);
      window.clearInterval(stageTimer);
      setActiveStageIndex(processingStages.length - 1);

      startTransition(() => {
        setRunState("ready");
        setResult(processedResult);
        setActiveClaimId(processedResult.claims[0]?.id ?? null);
        setSelectedDeliverableKey(processedResult.deliverables[0]?.key ?? null);
      });
    } catch (error) {
      window.clearInterval(stageTimer);
      setRunState("error");
      setErrorMessage(error instanceof Error ? error.message : "Meeting processing failed.");
    }
  }

  function handleLoadDemo() {
    setTranscriptText(demoTranscript);
    setErrorMessage("");
    if (runState === "error") {
      setRunState("idle");
    }
  }

  function handleTranscriptFileLoad(file: File | null) {
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setTranscriptText(typeof reader.result === "string" ? reader.result : "");
      setErrorMessage("");
    };
    reader.onerror = () => {
      setErrorMessage("The selected transcript file could not be read.");
    };
    reader.readAsText(file);
  }

  function handleReset() {
    setRunState("idle");
    setActiveStageIndex(-1);
    setErrorMessage("");
    setResult(null);
    setActiveClaimId(null);
    setSelectedDeliverableKey("weekly-report");
  }

  async function handleSelectDeliverable(key: DeliverableKey) {
    setSelectedDeliverableKey(key);
    if (!result) {
      return;
    }

    try {
      const deliverable = await fetchDeliverable(result.projectId, key);
      setResult((currentResult) => {
        if (!currentResult) {
          return currentResult;
        }
        const nextDeliverables = currentResult.deliverables.map((item) =>
          item.key === deliverable.key ? deliverable : item
        );
        return {
          ...currentResult,
          deliverables: nextDeliverables,
        };
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Deliverable refresh failed.");
    }
  }

  function handleExportDeliverable(deliverable: DeliverablePreview) {
    const blob = new Blob([deliverable.content], { type: "text/markdown;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${deliverable.key}.md`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <main className="dashboard-shell">
      <aside className="left-column">
        <div className="brand-panel">
          <div className="brand-mark">EF</div>
          <div>
            <p className="eyebrow">Research Cockpit</p>
            <h1>EvidenceFlow Agent</h1>
            <p className="supporting-copy">Turn a weekly group meeting into next-week execution.</p>
          </div>
        </div>

        <section className="panel">
          <p className="eyebrow">Active Project</p>
          <strong className="panel-title">{result?.projectName ?? "EvidenceFlow Demo Project"}</strong>
          <p className="supporting-copy">
            Single-workspace MVP for weekly research meetings, briefing prep, and evidence-aware follow-up.
          </p>
        </section>

        <nav className="panel nav-panel" aria-label="Primary navigation">
          <p className="eyebrow">Navigation</p>
          <ul className="nav-list">
            {navigation.map((item, index) => (
              <li key={item}>
                <button className={`nav-button ${index === 0 ? "nav-button-active" : ""}`} type="button">
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <section className="panel context-panel">
          <div className="section-inline">
            <div>
              <p className="eyebrow">Meeting Context</p>
              <strong className="panel-title">{result?.meetingTitle ?? "Demo Weekly Group Meeting"}</strong>
            </div>
            <span className="status-pill status-pill-soft">
              {result ? result.meetingStatus : "Fixed demo"}
            </span>
          </div>
          <p className="supporting-copy">
            This sample keeps the product narrative stable: one student update, two advisor ideas, three action items, and one claim that still needs evidence.
          </p>
        </section>
      </aside>

      <section className="center-column">
        <MeetingUpload
          transcriptText={transcriptText}
          runState={runState}
          activeStageIndex={activeStageIndex}
          errorMessage={errorMessage}
          stages={processingStages}
          onTranscriptChange={setTranscriptText}
          onTranscriptFileLoad={handleTranscriptFileLoad}
          onLoadDemo={handleLoadDemo}
          onProcess={handleProcess}
          onReset={handleReset}
        />

        {isReady && result ? (
          <>
            <section className="panel panel-elevated summary-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Meeting Summary</p>
                  <h2>{result.meetingTitle}</h2>
                  <p className="supporting-copy">
                    {result.meetingDate} / {result.meetingStatus}
                  </p>
                </div>
                <span className="status-pill status-pill-brand">Ready for review</span>
              </div>
              <p className="summary-copy">{result.summary}</p>
              <div className="summary-stats">
                <div>
                  <strong>{result.studentProgress.length}</strong>
                  <span>student view</span>
                </div>
                <div>
                  <strong>{result.advisorIdeas.length}</strong>
                  <span>advisor ideas</span>
                </div>
                <div>
                  <strong>{result.actionItems.length}</strong>
                  <span>open actions</span>
                </div>
                <div>
                  <strong>{result.claims.length}</strong>
                  <span>evidence claims</span>
                </div>
              </div>
            </section>

            <section className="content-section">
              <div className="section-header">
                <div>
                  <p className="eyebrow">Progress</p>
                  <h3>Student Progress</h3>
                </div>
              </div>
              <div className="card-grid">
                {result.studentProgress.map((student) => (
                  <article className="panel progress-card" key={student.studentName}>
                    <div className="section-inline">
                      <div>
                        <p className="eyebrow">Student</p>
                        <h4>{student.studentName}</h4>
                      </div>
                      <span className={`priority-pill priority-${student.riskLevel}`}>
                        {formatRiskLabel(student.riskLevel)}
                      </span>
                    </div>

                    <dl className="detail-list">
                      <div>
                        <dt>Completed</dt>
                        <dd>{student.completedWork.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>Current Result</dt>
                        <dd>{student.currentResult}</dd>
                      </div>
                      <div>
                        <dt>Blockers</dt>
                        <dd>{student.blockers.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>Risks</dt>
                        <dd>{student.risks.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>Next Step</dt>
                        <dd>{student.nextStep}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>

            <section className="content-section">
              <div className="section-header">
                <div>
                  <p className="eyebrow">Advisor Signals</p>
                  <h3>New Ideas</h3>
                </div>
              </div>
              <div className="idea-stack">
                {result.advisorIdeas.map((idea) => (
                  <article className="panel idea-card" key={idea.id}>
                    <div className="section-inline">
                      <div>
                        <p className="eyebrow">Idea</p>
                        <h4>{idea.title}</h4>
                      </div>
                      <button
                        className="button button-secondary button-mini"
                        type="button"
                        onClick={() => {
                          setActiveClaimId(result.claims[0]?.id ?? null);
                        }}
                      >
                        Add to plan
                      </button>
                    </div>
                    <dl className="detail-list">
                      <div>
                        <dt>Summary</dt>
                        <dd>{idea.summary}</dd>
                      </div>
                      <div>
                        <dt>Suggested Experiment</dt>
                        <dd>{idea.suggestedExperiment}</dd>
                      </div>
                      <div>
                        <dt>Validation Metrics</dt>
                        <dd>{idea.validationMetrics.join(", ")}</dd>
                      </div>
                      <div>
                        <dt>Recommended Reading</dt>
                        <dd>{idea.recommendedReading.join(", ")}</dd>
                      </div>
                      <div>
                        <dt>Evidence Status</dt>
                        <dd>{idea.evidenceStatus}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>

            <section className="content-section">
              <div className="section-header">
                <div>
                  <p className="eyebrow">Traceability</p>
                  <h3>Transcript Timeline</h3>
                </div>
                <span className="section-note">Click a claim in the evidence panel to highlight source chunks.</span>
              </div>
              <ol className="timeline-list">
                {result.transcriptTimeline.map((entry) => (
                  <li
                    className={`timeline-item ${
                      highlightedChunkIds.includes(entry.chunkId) ? "timeline-item-highlighted" : ""
                    }`}
                    key={entry.chunkId}
                  >
                    <div className="timeline-time">{entry.timestamp}</div>
                    <div className="timeline-content">
                      <p className="timeline-speaker">{entry.speaker}</p>
                      <p>{entry.text}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </>
        ) : runState === "loading" ? (
          <section className="loading-state">
            <div className="panel skeleton-panel">
              <div className="skeleton-line skeleton-line-title" />
              <div className="skeleton-line" />
              <div className="skeleton-line skeleton-line-short" />
            </div>
            <div className="panel skeleton-panel">
              <div className="skeleton-grid">
                <div className="skeleton-card" />
                <div className="skeleton-card" />
              </div>
            </div>
          </section>
        ) : (
          <section className="panel empty-result-panel">
            <p className="eyebrow">Review State</p>
            <h2>Upload a meeting transcript to generate the first research plan.</h2>
            <p className="supporting-copy">
              The dashboard keeps planning and reading visually primary, with evidence visible but secondary.
            </p>
          </section>
        )}
      </section>

      <aside className="right-column">
        <ActionItemsPanel
          actionItems={result?.actionItems ?? []}
          readingList={result?.readingList ?? []}
          agenda={result?.briefing.recommendedAgenda ?? []}
          isReady={isReady}
        />
        <EvidencePanel
          claims={result?.claims ?? []}
          activeClaimId={activeClaim?.id ?? null}
          isReady={isReady}
          onSelectClaim={setActiveClaimId}
        />
        <BriefingPanel
          briefing={
            result?.briefing ?? {
              summary: "",
              focusQuestions: [],
              recommendedAgenda: [],
            }
          }
          deliverables={result?.deliverables ?? []}
          selectedDeliverableKey={selectedDeliverableKey}
          isReady={isReady}
          onSelectDeliverable={handleSelectDeliverable}
          onExportDeliverable={handleExportDeliverable}
        />
      </aside>
    </main>
  );
}
