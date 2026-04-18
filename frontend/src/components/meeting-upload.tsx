"use client";

import type {
  DashboardRunState,
  ProcessingStage,
} from "./dashboard-types";

type MeetingUploadProps = {
  transcriptText: string;
  runState: DashboardRunState;
  activeStageIndex: number;
  errorMessage: string;
  stages: ProcessingStage[];
  onTranscriptChange: (value: string) => void;
  onTranscriptFileLoad: (file: File | null) => void;
  onLoadDemo: () => void;
  onProcess: () => void;
  onReset: () => void;
};

export function MeetingUpload({
  transcriptText,
  runState,
  activeStageIndex,
  errorMessage,
  stages,
  onTranscriptChange,
  onTranscriptFileLoad,
  onLoadDemo,
  onProcess,
  onReset,
}: MeetingUploadProps) {
  return (
    <section className="panel panel-elevated upload-panel" aria-labelledby="meeting-upload-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Meeting Processing</p>
          <h2 id="meeting-upload-title">Import a transcript and turn it into next-week execution.</h2>
        </div>
        <div className="button-row">
          <button className="button button-secondary" type="button" onClick={onLoadDemo}>
            Load Demo Transcript
          </button>
          <button
            className="button button-primary"
            type="button"
            onClick={onProcess}
            disabled={runState === "loading"}
          >
            {runState === "loading" ? "Processing..." : "Process Transcript"}
          </button>
        </div>
      </div>

      <div className="upload-grid">
        <div className="input-column">
          <label className="input-label" htmlFor="transcript-input">
            Meeting transcript
          </label>
          <label className="file-input-label" htmlFor="transcript-file">
            Import transcript file
          </label>
          <input
            id="transcript-file"
            className="file-input"
            type="file"
            accept=".txt,.md"
            onChange={(event) => onTranscriptFileLoad(event.target.files?.[0] ?? null)}
          />
          <textarea
            id="transcript-input"
            className="transcript-input"
            value={transcriptText}
            onChange={(event) => onTranscriptChange(event.target.value)}
            placeholder="Paste a weekly research meeting transcript here."
            spellCheck={false}
          />
          <div className="button-row button-row-compact">
            <button className="button button-ghost" type="button" onClick={onReset}>
              Reset Review State
            </button>
            <p className="field-hint">
              Upload-first flow: import, inspect, then export briefing-ready outputs.
            </p>
          </div>
          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
        </div>

        <div className="stage-column">
          <p className="eyebrow">Processing Stages</p>
          <ol className="stage-list">
            {stages.map((stage, index) => {
              let status = "waiting";
              if (runState === "ready") {
                status = "done";
              } else if (runState === "loading" && index < activeStageIndex) {
                status = "done";
              } else if (runState === "loading" && index === activeStageIndex) {
                status = "active";
              }

              return (
                <li className={`stage-item stage-${status}`} key={stage.key}>
                  <div className="stage-marker" aria-hidden="true" />
                  <div>
                    <strong>{stage.label}</strong>
                    <p>{stage.description}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
