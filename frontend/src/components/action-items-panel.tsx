import type {
  ActionItemData,
  ActionItemStatusValue,
  BriefingAgendaItemData,
  DashboardLanguage,
  ReadingItemData,
} from "./dashboard-types";
import {
  dashboardCopy,
  getOriginLayerLabel,
  getPriorityText,
  getStatusText,
} from "./dashboard-copy";

type ActionItemsPanelProps = {
  language: DashboardLanguage;
  actionItems: ActionItemData[];
  readingList: ReadingItemData[];
  agenda: BriefingAgendaItemData[];
  isReady: boolean;
  updatingActionId?: string | null;
  statusErrorMessage?: string;
  onUpdateStatus?: (item: ActionItemData, nextStatus: ActionItemStatusValue) => void;
};

const actionStatusOptions: ActionItemStatusValue[] = [
  "open",
  "in_progress",
  "blocked",
  "done",
  "unknown",
];

function getStatusControlCopy(language: DashboardLanguage) {
  if (language === "zh") {
    return {
      label: "任务状态",
      updating: "更新中",
    };
  }

  return {
    label: "Task status",
    updating: "Updating",
  };
}

export function ActionItemsPanel({
  language,
  actionItems,
  readingList,
  agenda,
  isReady,
  updatingActionId,
  statusErrorMessage,
  onUpdateStatus,
}: ActionItemsPanelProps) {
  const copy = dashboardCopy[language];
  const statusCopy = getStatusControlCopy(language);

  if (!isReady) {
    return (
      <section className="panel">
        <div className="panel-header compact-header">
          <div>
            <p className="eyebrow">{copy.execution}</p>
            <h3>{copy.nextWeekPlan}</h3>
          </div>
        </div>
        <div className="empty-panel">
          <p>{copy.emptyUploadPrompt}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">{copy.execution}</p>
          <h3>{copy.nextWeekPlan}</h3>
        </div>
        <span className="status-pill status-pill-brand">{copy.actionReady}</span>
      </div>

      <ul className="task-list">
        {actionItems.map((item) => (
          <li className="task-card" key={item.id}>
            <div className="task-card-top">
              <strong>{item.title}</strong>
              <div className="task-card-actions">
                <span className={`priority-pill priority-${item.priority}`}>
                  {getPriorityText(language, item.priority)}
                </span>
                {onUpdateStatus ? (
                  <label className="status-control">
                    <span className="status-control-label">
                      {updatingActionId === item.id ? statusCopy.updating : statusCopy.label}
                    </span>
                    <select
                      className="status-select"
                      aria-label={`${statusCopy.label}: ${item.title}`}
                      value={item.status}
                      disabled={updatingActionId === item.id}
                      onChange={(event) => {
                        const nextStatus = event.target.value as ActionItemStatusValue;
                        if (nextStatus !== item.status) {
                          onUpdateStatus(item, nextStatus);
                        }
                      }}
                    >
                      {actionStatusOptions.map((statusOption) => (
                        <option key={statusOption} value={statusOption}>
                          {getStatusText(language, statusOption)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
              </div>
            </div>
            <p className="task-meta">
              {item.owner} / {copy.due} {item.dueDate} / {getStatusText(language, item.status)}
            </p>
            <p className="task-rationale">{item.rationale}</p>
            <p className="supporting-copy">{item.outputSummary}</p>
            <details className="task-details">
              <summary>{copy.whyTaskExists}</summary>
              <p>{item.sourceLabel}</p>
              <ul className="metric-list">
                {item.successMetrics.map((metric) => (
                  <li key={metric}>{metric}</li>
                ))}
              </ul>
              <ul className="explanation-list">
                {item.attributions.map((attribution) => (
                  <li key={`${item.id}-${attribution.label}`}>
                    <strong>{getOriginLayerLabel(language, attribution.originLayer)}</strong>
                    <p>{`${attribution.label}: ${attribution.detail}`}</p>
                  </li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
      {statusErrorMessage ? <p className="inline-error">{statusErrorMessage}</p> : null}

      <div className="subsection">
        <div className="subsection-header">
          <p className="eyebrow">{copy.reading}</p>
          <h4>{copy.recommendedReading}</h4>
        </div>
        <ul className="reading-list">
          {readingList.map((item) => (
            <li className="reading-card" key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <p>{item.reason}</p>
                <p className="supporting-copy">{item.outputSummary}</p>
                <ul className="explanation-list">
                  {item.attributions.map((attribution) => (
                    <li key={`${item.id}-${attribution.label}`}>
                      <strong>{getOriginLayerLabel(language, attribution.originLayer)}</strong>
                      <p>{`${attribution.label}: ${attribution.detail}`}</p>
                    </li>
                  ))}
                </ul>
              </div>
              <span className={`priority-pill priority-${item.priority}`}>
                {getPriorityText(language, item.priority)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="subsection">
        <div className="subsection-header">
          <p className="eyebrow">{copy.agenda}</p>
          <h4>{copy.recommendedAgenda}</h4>
        </div>
        <ul className="agenda-list">
          {agenda.map((item) => (
            <li key={item.title}>
              <strong>{item.title}</strong>
              <p>{item.reason}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
