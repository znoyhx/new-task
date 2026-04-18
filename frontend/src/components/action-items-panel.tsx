import type {
  ActionItemData,
  BriefingAgendaItemData,
  ReadingItemData,
} from "./dashboard-types";

type ActionItemsPanelProps = {
  actionItems: ActionItemData[];
  readingList: ReadingItemData[];
  agenda: BriefingAgendaItemData[];
  isReady: boolean;
};

export function ActionItemsPanel({
  actionItems,
  readingList,
  agenda,
  isReady,
}: ActionItemsPanelProps) {
  if (!isReady) {
    return (
      <section className="panel sticky-card">
        <div className="panel-header compact-header">
          <div>
            <p className="eyebrow">Execution</p>
            <h3>Next-Week Plan</h3>
          </div>
        </div>
        <div className="empty-panel">
          <p>Upload a meeting transcript to generate the first research plan.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel sticky-card">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Execution</p>
          <h3>Next-Week Plan</h3>
        </div>
        <span className="status-pill status-pill-brand">Action-ready</span>
      </div>

      <ul className="task-list">
        {actionItems.map((item) => (
          <li className="task-card" key={item.id}>
            <div className="task-card-top">
              <strong>{item.title}</strong>
              <span className={`priority-pill priority-${item.priority}`}>{item.priority}</span>
            </div>
            <p className="task-meta">
              {item.owner} / due {item.dueDate} / {item.status}
            </p>
            <p className="task-rationale">{item.rationale}</p>
            <details className="task-details">
              <summary>Why this task exists</summary>
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
          <p className="eyebrow">Reading</p>
          <h4>Recommended Reading</h4>
        </div>
        <ul className="reading-list">
          {readingList.map((item) => (
            <li className="reading-card" key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <p>{item.reason}</p>
              </div>
              <span className={`priority-pill priority-${item.priority}`}>{item.priority}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="subsection">
        <div className="subsection-header">
          <p className="eyebrow">Agenda</p>
          <h4>Recommended Agenda</h4>
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
