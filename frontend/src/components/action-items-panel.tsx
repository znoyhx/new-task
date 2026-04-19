import type {
  ActionItemData,
  BriefingAgendaItemData,
  DashboardLanguage,
  ReadingItemData,
} from "./dashboard-types";
import { dashboardCopy, getPriorityText, getStatusText } from "./dashboard-copy";

type ActionItemsPanelProps = {
  language: DashboardLanguage;
  actionItems: ActionItemData[];
  readingList: ReadingItemData[];
  agenda: BriefingAgendaItemData[];
  isReady: boolean;
};

export function ActionItemsPanel({
  language,
  actionItems,
  readingList,
  agenda,
  isReady,
}: ActionItemsPanelProps) {
  const copy = dashboardCopy[language];

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
              <span className={`priority-pill priority-${item.priority}`}>
                {getPriorityText(language, item.priority)}
              </span>
            </div>
            <p className="task-meta">
              {item.owner} / {copy.due} {item.dueDate} / {getStatusText(language, item.status)}
            </p>
            <p className="task-rationale">{item.rationale}</p>
            <details className="task-details">
              <summary>{copy.whyTaskExists}</summary>
              <p>{item.sourceLabel}</p>
              <ul className="metric-list">
                {item.successMetrics.map((metric) => (
                  <li key={metric}>{metric}</li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>

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
