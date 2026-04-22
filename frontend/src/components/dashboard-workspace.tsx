"use client";

import { startTransition, useEffect, useState } from "react";

import { demoTranscript } from "./dashboard-data";
import { ActionItemsPanel } from "./action-items-panel";
import {
  type ActionItemStatusUpdateResult,
  DashboardApiError,
  fetchDeliverable,
  fetchProjectMemory,
  processMeetingAudio,
  processMeetingTranscript,
  updateActionItemStatus,
} from "./dashboard-api";
import { BriefingPanel } from "./briefing-panel";
import {
  audioProcessingStagesByLanguage,
  dashboardCopy,
  getRiskLabel,
  navigationByLanguage,
  processingStagesByLanguage,
} from "./dashboard-copy";
import { EvidencePanel } from "./evidence-panel";
import { MemoryPanel } from "./memory-panel";
import { MeetingUpload } from "./meeting-upload";
import type {
  ActionItemData,
  ActionItemStatusValue,
  DashboardLanguage,
  DashboardResultData,
  DashboardRunState,
  DeliverableKey,
  DeliverablePreview,
  ProjectMemoryData,
} from "./dashboard-types";

type MeetingInputMode = "transcript" | "audio";

function formatFileSize(sizeBytes: number, language: DashboardLanguage) {
  if (sizeBytes < 1024 * 1024) {
    const sizeKb = Math.max(1, Math.round(sizeBytes / 1024));
    return language === "zh" ? `${sizeKb} KB` : `${sizeKb} KB`;
  }
  const sizeMb = (sizeBytes / (1024 * 1024)).toFixed(1);
  return language === "zh" ? `${sizeMb} MB` : `${sizeMb} MB`;
}

export function DashboardWorkspace() {
  const [language, setLanguage] = useState<DashboardLanguage>("zh");
  const [inputMode, setInputMode] = useState<MeetingInputMode>("transcript");
  const [transcriptText, setTranscriptText] = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [runState, setRunState] = useState<DashboardRunState>("idle");
  const [activeStageIndex, setActiveStageIndex] = useState(-1);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorMeta, setErrorMeta] = useState<{
    stage?: string;
    agent?: string;
    fallback?: string;
  } | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [selectedDeliverableKey, setSelectedDeliverableKey] =
    useState<DeliverableKey | null>("weekly-report");
  const [result, setResult] = useState<DashboardResultData | null>(null);
  const [projectMemory, setProjectMemory] = useState<ProjectMemoryData | null>(null);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);
  const [memoryErrorMessage, setMemoryErrorMessage] = useState("");
  const [updatingActionId, setUpdatingActionId] = useState<string | null>(null);
  const [actionStatusErrorMessage, setActionStatusErrorMessage] = useState("");

  const copy = dashboardCopy[language];
  const navigation = navigationByLanguage[language];
  const plannedStages =
    inputMode === "audio"
      ? audioProcessingStagesByLanguage[language]
      : processingStagesByLanguage[language];
  const isReady = runState === "ready" && result !== null;
  const visibleStages = isReady ? result.orchestration.stages : plannedStages;
  const activeOrchestrationStage =
    runState === "loading"
      ? plannedStages[Math.max(activeStageIndex, 0)] ?? null
      : isReady
        ? result.orchestration.stages[result.orchestration.stages.length - 1] ?? null
        : null;
  const activeClaim = result?.claims.find((claim) => claim.id === activeClaimId) ?? result?.claims[0] ?? null;
  const highlightedChunkIds = activeClaim?.sourceChunkIds ?? [];
  const selectedAudioFileName = audioFile?.name ?? "";
  const selectedAudioFileSizeLabel = audioFile ? formatFileSize(audioFile.size, language) : "";
  const effectiveMemoryUsage = projectMemory?.memoryUsage ?? result?.orchestration.memoryUsage ?? null;

  useEffect(() => {
    if (projectMemory && result) {
      syncMemoryIntoResult(projectMemory);
    }
  }, [projectMemory, result?.meetingId]);

  function syncMemoryIntoResult(nextMemory: ProjectMemoryData) {
    setResult((currentResult) => {
      if (!currentResult) {
        return currentResult;
      }
      return {
        ...currentResult,
        briefing: nextMemory.briefing,
        orchestration: {
          ...currentResult.orchestration,
          memoryUsage: nextMemory.memoryUsage,
        },
      };
    });
  }

  async function refreshProjectMemory(projectId: string, currentMeetingId: string) {
    setIsMemoryLoading(true);
    setMemoryErrorMessage("");

    try {
      const nextMemory = await fetchProjectMemory(projectId, currentMeetingId);
      setProjectMemory(nextMemory);
      syncMemoryIntoResult(nextMemory);
    } catch (error) {
      setMemoryErrorMessage(
        error instanceof Error
          ? error.message
          : language === "zh"
            ? "项目记忆刷新失败。"
            : "Project memory refresh failed."
      );
    } finally {
      setIsMemoryLoading(false);
    }
  }

  async function handleProcess() {
    if (inputMode === "transcript" && !transcriptText.trim()) {
      setRunState("error");
      setErrorMessage(copy.emptyUploadPrompt);
      setErrorMeta(null);
      return;
    }
    if (inputMode === "audio" && !audioFile) {
      setRunState("error");
      setErrorMessage(copy.emptyAudioUploadPrompt);
      setErrorMeta(null);
      return;
    }

    setErrorMessage("");
    setErrorMeta(null);
    setRunState("loading");
    setResult(null);
    setProjectMemory(null);
    setMemoryErrorMessage("");
    setActionStatusErrorMessage("");
    setUpdatingActionId(null);
    setActiveClaimId(null);
    setActiveStageIndex(0);

    const stageTimer = window.setInterval(() => {
      setActiveStageIndex((currentIndex) => {
        if (currentIndex >= plannedStages.length - 1) {
          return currentIndex;
        }
        return currentIndex + 1;
      });
    }, 650);

    try {
      const processedResult =
        inputMode === "audio" && audioFile
          ? await processMeetingAudio(audioFile, {
              meetingTitle: audioFile.name.replace(/\.[^.]+$/, "") || "Audio Meeting",
            })
          : await processMeetingTranscript(transcriptText);
      window.clearInterval(stageTimer);
      setActiveStageIndex(plannedStages.length - 1);

      startTransition(() => {
        setRunState("ready");
        setResult(processedResult);
        setProjectMemory(null);
        setActiveClaimId(processedResult.claims[0]?.id ?? null);
        setSelectedDeliverableKey(processedResult.deliverables[0]?.key ?? null);
        setErrorMeta(null);
      });
      void refreshProjectMemory(processedResult.projectId, processedResult.meetingId);
    } catch (error) {
      window.clearInterval(stageTimer);
      setRunState("error");
      if (error instanceof DashboardApiError) {
        setErrorMessage(error.message);
        setErrorMeta({
          stage: error.stage,
          agent: error.agent,
          fallback: error.fallback,
        });
        return;
      }
      setErrorMessage(
        error instanceof Error
          ? error.message
          : language === "zh"
            ? "组会处理失败。"
            : "Meeting processing failed."
      );
      setErrorMeta(null);
    }
  }

  function handleLoadDemo() {
    setInputMode("transcript");
    setAudioFile(null);
    setTranscriptText(demoTranscript);
    setErrorMessage("");
    setErrorMeta(null);
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
      setErrorMeta(null);
    };
    reader.onerror = () => {
      setErrorMessage(
        language === "zh"
          ? "选中的 transcript 文件无法读取。"
          : "The selected transcript file could not be read."
      );
      setErrorMeta(null);
    };
    reader.readAsText(file);
  }

  function handleAudioFileLoad(file: File | null) {
    setAudioFile(file);
    setErrorMessage("");
    setErrorMeta(null);
    if (runState === "error") {
      setRunState("idle");
    }
  }

  function handleInputModeChange(nextMode: MeetingInputMode) {
    setInputMode(nextMode);
    setErrorMessage("");
    setErrorMeta(null);
    if (runState === "error") {
      setRunState("idle");
    }
  }

  function handleReset() {
    setRunState("idle");
    setActiveStageIndex(-1);
    setErrorMessage("");
    setErrorMeta(null);
    setResult(null);
    setProjectMemory(null);
    setIsMemoryLoading(false);
    setMemoryErrorMessage("");
    setUpdatingActionId(null);
    setActionStatusErrorMessage("");
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
      setErrorMessage(
        error instanceof Error
          ? error.message
          : language === "zh"
            ? "刷新交付物失败。"
            : "Deliverable refresh failed."
      );
    }
  }

  async function handleUpdateActionStatus(
    item: ActionItemData,
    nextStatus: ActionItemStatusValue
  ) {
    if (!result || item.status === nextStatus) {
      return;
    }

    const projectId = result.projectId;
    const currentMeetingId = result.meetingId;
    const activeDeliverableKey = selectedDeliverableKey;

    setUpdatingActionId(item.id);
    setActionStatusErrorMessage("");

    try {
      const updateResult: ActionItemStatusUpdateResult = await updateActionItemStatus(projectId, {
        meetingId: item.meetingId,
        title: item.title,
        owner: item.owner,
        status: nextStatus,
        currentMeetingId,
      });

      setProjectMemory(updateResult.projectMemory);
      setResult((currentResult) => {
        if (!currentResult) {
          return currentResult;
        }

        return {
          ...currentResult,
          actionItems: currentResult.actionItems.map((actionItem) =>
            actionItem.id === item.id
              ? {
                  ...actionItem,
                  status: updateResult.updatedActionItem.status,
                }
              : actionItem
          ),
          briefing: updateResult.projectMemory.briefing,
          orchestration: {
            ...currentResult.orchestration,
            memoryUsage: updateResult.projectMemory.memoryUsage,
          },
        };
      });

      if (activeDeliverableKey) {
        const deliverable = await fetchDeliverable(projectId, activeDeliverableKey);
        setResult((currentResult) => {
          if (!currentResult) {
            return currentResult;
          }

          return {
            ...currentResult,
            deliverables: currentResult.deliverables.map((itemDeliverable) =>
              itemDeliverable.key === deliverable.key ? deliverable : itemDeliverable
            ),
          };
        });
      }
    } catch (error) {
      setActionStatusErrorMessage(
        error instanceof Error
          ? error.message
          : language === "zh"
            ? "任务状态更新失败。"
            : "Task status update failed."
      );
    } finally {
      setUpdatingActionId(null);
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
            <p className="eyebrow">{copy.brandEyebrow}</p>
            <h1>{copy.brandTitle}</h1>
            <p className="supporting-copy">{copy.brandSubtitle}</p>
          </div>
        </div>

        <section className="panel language-panel">
          <p className="eyebrow">{copy.languageLabel}</p>
          <div className="language-toggle" role="tablist" aria-label={copy.languageLabel}>
            <button
              type="button"
              className={`language-button ${language === "zh" ? "language-button-active" : ""}`}
              onClick={() => setLanguage("zh")}
            >
              中文
            </button>
            <button
              type="button"
              className={`language-button ${language === "en" ? "language-button-active" : ""}`}
              onClick={() => setLanguage("en")}
            >
              English
            </button>
          </div>
        </section>

        <section className="panel">
          <p className="eyebrow">{copy.activeProject}</p>
          <strong className="panel-title">{result?.projectName ?? copy.defaultProjectName}</strong>
          <p className="supporting-copy">{copy.projectDescription}</p>
        </section>

        <nav className="panel nav-panel" aria-label="Primary navigation">
          <p className="eyebrow">{copy.navigationTitle}</p>
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
              <p className="eyebrow">{copy.meetingContext}</p>
              <strong className="panel-title">{result?.meetingTitle ?? copy.defaultMeetingName}</strong>
            </div>
            <span className="status-pill status-pill-soft">
              {result ? result.meetingStatus : copy.fixedDemo}
            </span>
          </div>
          <p className="supporting-copy">{copy.sampleNarrative}</p>
        </section>
      </aside>

      <section className="center-column">
        <MeetingUpload
          language={language}
          transcriptText={transcriptText}
          runState={runState}
          activeStageIndex={activeStageIndex}
          errorMessage={errorMessage}
          stages={visibleStages}
          onTranscriptChange={setTranscriptText}
          onTranscriptFileLoad={handleTranscriptFileLoad}
          onLoadDemo={handleLoadDemo}
          onProcess={handleProcess}
          onReset={handleReset}
          inputMode={inputMode}
          selectedAudioFileName={selectedAudioFileName}
          selectedAudioFileSizeLabel={selectedAudioFileSizeLabel}
          onInputModeChange={handleInputModeChange}
          onAudioFileLoad={handleAudioFileLoad}
          onClearAudio={() => setAudioFile(null)}
          activeOrchestrationStage={activeOrchestrationStage}
          errorMeta={errorMeta}
        />

        {isReady && result ? (
          <>
            <section className="panel panel-elevated summary-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">{copy.meetingSummary}</p>
                  <h2>{result.meetingTitle}</h2>
                  <p className="supporting-copy">
                    {result.meetingDate} / {result.meetingStatus}
                  </p>
                </div>
                <span className="status-pill status-pill-brand">{copy.readyForReview}</span>
              </div>
              <p className="summary-copy">{result.summary}</p>
              <div className="memory-summary-strip">
                <p className="eyebrow">{copy.memoryInUse}</p>
                {effectiveMemoryUsage && effectiveMemoryUsage.priorMeetingCount > 0 ? (
                  <p className="supporting-copy">
                    {`${effectiveMemoryUsage.priorMeetingCount} prior meeting(s), ${effectiveMemoryUsage.openTaskCount} carryover task(s), ${effectiveMemoryUsage.recentDecisionCount} decision(s).`}
                  </p>
                ) : (
                  <p className="supporting-copy">{copy.memoryEmpty}</p>
                )}
              </div>
              <div className="summary-stats">
                <div>
                  <strong>{result.studentProgress.length}</strong>
                  <span>{copy.studentView}</span>
                </div>
                <div>
                  <strong>{result.advisorIdeas.length}</strong>
                  <span>{copy.advisorIdeas}</span>
                </div>
                <div>
                  <strong>{result.actionItems.length}</strong>
                  <span>{copy.openActions}</span>
                </div>
                <div>
                  <strong>{result.claims.length}</strong>
                  <span>{copy.evidenceClaims}</span>
                </div>
              </div>
            </section>

            <section className="panel orchestration-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">{copy.agentOrchestration}</p>
                  <h3>{result.orchestration.controllerAgentName}</h3>
                  <p className="supporting-copy">
                    {`${result.orchestration.llmProvider} / ${result.orchestration.llmModel}`}
                  </p>
                </div>
              </div>
              <div className="orchestration-grid">
                {result.orchestration.stages.map((stage) => (
                  <article className="orchestration-stage" key={stage.key}>
                    <div className="section-inline">
                      <div>
                        <p className="eyebrow">{stage.agentName}</p>
                        <strong>{stage.label}</strong>
                      </div>
                      <span className="status-pill status-pill-soft">{stage.status}</span>
                    </div>
                    <p className="supporting-copy">{stage.agentGoal}</p>
                    <dl className="detail-list">
                      <div>
                        <dt>{copy.inputSource}</dt>
                        <dd>{stage.inputSource}</dd>
                      </div>
                      <div>
                        <dt>{copy.outputTarget}</dt>
                        <dd>{stage.outputTarget}</dd>
                      </div>
                      <div>
                        <dt>{copy.fallbackStrategy}</dt>
                        <dd>{stage.fallback}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>

            <section className="content-section">
              <div className="section-header">
                <div>
                  <p className="eyebrow">{copy.progressTitle}</p>
                  <h3>{copy.progressTitle}</h3>
                </div>
              </div>
              <div className="card-grid">
                {result.studentProgress.map((student) => (
                  <article className="panel progress-card" key={student.studentName}>
                    <div className="section-inline">
                      <div>
                        <p className="eyebrow">{copy.studentLabel}</p>
                        <h4>{student.studentName}</h4>
                      </div>
                      <span className={`priority-pill priority-${student.riskLevel}`}>
                        {getRiskLabel(language, student.riskLevel)}
                      </span>
                    </div>

                    <dl className="detail-list">
                      <div>
                        <dt>{copy.completed}</dt>
                        <dd>{student.completedWork.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>{copy.currentResult}</dt>
                        <dd>{student.currentResult}</dd>
                      </div>
                      <div>
                        <dt>{copy.blockers}</dt>
                        <dd>{student.blockers.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>{copy.risks}</dt>
                        <dd>{student.risks.join(" ")}</dd>
                      </div>
                      <div>
                        <dt>{copy.nextStep}</dt>
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
                  <p className="eyebrow">{copy.advisorSignals}</p>
                  <h3>{copy.newIdeas}</h3>
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
                        {copy.addToPlan}
                      </button>
                    </div>
                    <dl className="detail-list">
                      <div>
                        <dt>{copy.summary}</dt>
                        <dd>{idea.summary}</dd>
                      </div>
                      <div>
                        <dt>{copy.suggestedExperiment}</dt>
                        <dd>{idea.suggestedExperiment}</dd>
                      </div>
                      <div>
                        <dt>{copy.validationMetrics}</dt>
                        <dd>{idea.validationMetrics.join(", ")}</dd>
                      </div>
                      <div>
                        <dt>{copy.recommendedReading}</dt>
                        <dd>{idea.recommendedReading.join(", ")}</dd>
                      </div>
                      <div>
                        <dt>{copy.evidenceStatus}</dt>
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
                  <p className="eyebrow">{copy.traceability}</p>
                  <h3>{copy.transcriptTimeline}</h3>
                </div>
                <span className="section-note">{copy.transcriptHint}</span>
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
            <p className="eyebrow">{copy.reviewState}</p>
            <h2>{copy.emptyReviewTitle}</h2>
            <p className="supporting-copy">{copy.emptyReviewBody}</p>
          </section>
        )}
      </section>

      <aside className="right-column">
        <ActionItemsPanel
          language={language}
          actionItems={result?.actionItems ?? []}
          readingList={result?.readingList ?? []}
          agenda={result?.briefing.recommendedAgenda ?? []}
          isReady={isReady}
          updatingActionId={updatingActionId}
          statusErrorMessage={actionStatusErrorMessage}
          onUpdateStatus={handleUpdateActionStatus}
        />
        <EvidencePanel
          language={language}
          claims={result?.claims ?? []}
          activeClaimId={activeClaim?.id ?? null}
          isReady={isReady}
          onSelectClaim={setActiveClaimId}
        />
        <BriefingPanel
          language={language}
          briefing={
            result?.briefing ?? {
              summary: "",
              focusQuestions: [],
              recommendedAgenda: [],
              items: [],
            }
          }
          deliverables={result?.deliverables ?? []}
          selectedDeliverableKey={selectedDeliverableKey}
          isReady={isReady}
          onSelectDeliverable={handleSelectDeliverable}
          onExportDeliverable={handleExportDeliverable}
          memoryUsage={effectiveMemoryUsage}
        />
        <MemoryPanel
          language={language}
          memory={projectMemory}
          isReady={isReady}
          isLoading={isMemoryLoading}
          errorMessage={memoryErrorMessage}
        />
      </aside>
    </main>
  );
}
