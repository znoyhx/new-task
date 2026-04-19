"use client";

import type {
  DashboardLanguage,
  DashboardRunState,
  ProcessingStage,
} from "./dashboard-types";
import { dashboardCopy } from "./dashboard-copy";

type MeetingInputMode = "transcript" | "audio";

type MeetingUploadProps = {
  language: DashboardLanguage;
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
  inputMode?: MeetingInputMode;
  selectedAudioFileName?: string;
  selectedAudioFileSizeLabel?: string;
  onInputModeChange?: (value: MeetingInputMode) => void;
  onAudioFileLoad?: (file: File | null) => void;
  onClearAudio?: () => void;
};

export function MeetingUpload({
  language,
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
  inputMode = "transcript",
  selectedAudioFileName = "",
  selectedAudioFileSizeLabel = "",
  onInputModeChange,
  onAudioFileLoad,
  onClearAudio,
}: MeetingUploadProps) {
  const copy = dashboardCopy[language];
  const isAudioMode = inputMode === "audio";
  const heading = isAudioMode ? copy.uploadHeadingAudio : copy.uploadHeading;
  const processLabel = isAudioMode ? copy.processAudio : copy.process;

  return (
    <section className="panel panel-elevated upload-panel" aria-labelledby="meeting-upload-title">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{copy.meetingProcessing}</p>
          <h2 id="meeting-upload-title">{heading}</h2>
        </div>
        <div className="button-row">
          <button className="button button-secondary" type="button" onClick={onLoadDemo}>
            {copy.loadDemo}
          </button>
          <button
            className="button button-primary"
            type="button"
            onClick={onProcess}
            disabled={runState === "loading"}
          >
            {runState === "loading" ? copy.processing : processLabel}
          </button>
        </div>
      </div>

      <div className="upload-grid">
        <div className="input-column">
          <div className="mode-toggle-section">
            <p className="input-label mode-toggle-label">{copy.inputModeLabel}</p>
            <div className="mode-toggle" role="tablist" aria-label={copy.inputModeLabel}>
              <button
                className={`mode-toggle-button ${!isAudioMode ? "mode-toggle-button-active" : ""}`}
                type="button"
                onClick={() => onInputModeChange?.("transcript")}
              >
                {copy.transcriptInputMode}
              </button>
              <button
                className={`mode-toggle-button ${isAudioMode ? "mode-toggle-button-active" : ""}`}
                type="button"
                onClick={() => onInputModeChange?.("audio")}
              >
                {copy.audioInputMode}
              </button>
            </div>
          </div>

          {isAudioMode ? (
            <>
              <label className="input-label" htmlFor="audio-file">
                {copy.selectAudioFile}
              </label>
              <label className="file-input-label" htmlFor="audio-file">
                {copy.supportedAudioFormats}
              </label>
              <input
                id="audio-file"
                className="file-input"
                type="file"
                accept=".mp3,.wav,.m4a,.mp4,.webm,audio/*"
                onChange={(event) => onAudioFileLoad?.(event.target.files?.[0] ?? null)}
              />
              <div className="audio-file-summary" aria-live="polite">
                <p className="eyebrow">{copy.selectedAudioLabel}</p>
                <strong>{selectedAudioFileName || copy.noAudioSelected}</strong>
                {selectedAudioFileSizeLabel ? (
                  <p className="field-hint">{selectedAudioFileSizeLabel}</p>
                ) : null}
                <p className="field-hint">{copy.localTranscriptionNote}</p>
              </div>
              {selectedAudioFileName ? (
                <button className="button button-ghost" type="button" onClick={onClearAudio}>
                  {copy.clearSelectedAudio}
                </button>
              ) : null}
            </>
          ) : (
            <>
              <label className="input-label" htmlFor="transcript-input">
                {copy.meetingTranscript}
              </label>
              <label className="file-input-label" htmlFor="transcript-file">
                {copy.importTranscriptFile}
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
                placeholder={copy.transcriptPlaceholder}
                spellCheck={false}
              />
            </>
          )}
          <div className="button-row button-row-compact">
            <button className="button button-ghost" type="button" onClick={onReset}>
              {copy.resetReviewState}
            </button>
            <p className="field-hint">{copy.uploadHint}</p>
          </div>
          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
        </div>

        <div className="stage-column">
          <p className="eyebrow">{copy.processingStages}</p>
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
