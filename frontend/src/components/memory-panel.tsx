"use client";

import { dashboardCopy, getOriginLayerLabel, getPriorityText, getStatusText } from "./dashboard-copy";
import type { DashboardLanguage, ProjectMemoryData } from "./dashboard-types";

type MemoryPanelProps = {
  language: DashboardLanguage;
  memory: ProjectMemoryData | null;
  isReady: boolean;
  isLoading: boolean;
  errorMessage: string;
};

function getMemoryPanelCopy(language: DashboardLanguage) {
  if (language === "zh") {
    return {
      panelTitle: "项目记忆",
      loading: "刷新中",
      memorySummary: "可复用上下文",
      openTaskMemory: "滚动中的任务",
      nextMeetingContext: "下次组会上下文",
      recentDecisions: "最近决策",
      meetingsOnRecord: "历史组会",
      taskOrigin: "来源层",
      sourceMeeting: "来源组会",
      noOpenTasks: "当前没有仍在滚动的任务。",
      noContext: "当前没有需要滚入下次组会的上下文。",
      noDecisions: "当前还没有记录下来的关键决策。",
      noMeetings: "当前还没有历史组会记录。",
      empty: "处理完一次 meeting 后，这里会显示可复用 memory、滚动任务和下次 briefing 上下文。",
    };
  }

  return {
    panelTitle: "Project Memory",
    loading: "Refreshing",
    memorySummary: "Reusable context",
    openTaskMemory: "Open task memory",
    nextMeetingContext: "Next-meeting context",
    recentDecisions: "Recent decisions",
    meetingsOnRecord: "Meetings on record",
    taskOrigin: "Origin layer",
    sourceMeeting: "Source meeting",
    noOpenTasks: "No open tasks are currently rolling forward.",
    noContext: "No extra next-meeting context is currently queued.",
    noDecisions: "No project decisions are stored yet.",
    noMeetings: "No meetings have been stored yet.",
    empty: "After one meeting is processed, this panel shows reusable memory, rolling tasks, and next-briefing context.",
  };
}

export function MemoryPanel({
  language,
  memory,
  isReady,
  isLoading,
  errorMessage,
}: MemoryPanelProps) {
  const copy = dashboardCopy[language];
  const localCopy = getMemoryPanelCopy(language);

  return (
    <section className="panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">{copy.memoryInUse}</p>
          <h3>{localCopy.panelTitle}</h3>
        </div>
        <span className="status-pill status-pill-soft">
          {isLoading ? localCopy.loading : `${memory?.memoryUsage.priorMeetingCount ?? 0} meeting(s)`}
        </span>
      </div>

      {!isReady ? (
        <div className="empty-panel">
          <p>{localCopy.empty}</p>
        </div>
      ) : (
        <>
          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}

          {memory ? (
            <>
              <div className="memory-summary-strip">
                <p className="eyebrow">{localCopy.memorySummary}</p>
                <p className="supporting-copy">
                  {`${memory.memoryUsage.priorMeetingCount} prior meeting(s), ${memory.memoryUsage.openTaskCount} carryover task(s), ${memory.memoryUsage.recentDecisionCount} prior decision(s).`}
                </p>
              </div>

              <div className="subsection">
                <div className="subsection-header">
                  <p className="eyebrow">{localCopy.openTaskMemory}</p>
                  <h4>{copy.execution}</h4>
                </div>
                {memory.openActionItems.length > 0 ? (
                  <ul className="task-list">
                    {memory.openActionItems.map((item) => (
                      <li className="task-card memory-list-card" key={item.id}>
                        <div className="task-card-top">
                          <strong>{item.title}</strong>
                          <span className={`priority-pill priority-${item.priority}`}>
                            {getPriorityText(language, item.priority)}
                          </span>
                        </div>
                        <p className="task-meta">
                          {item.owner} / {copy.due} {item.dueDate} / {getStatusText(language, item.status)}
                        </p>
                        <dl className="detail-list memory-detail-list">
                          <div>
                            <dt>{localCopy.taskOrigin}</dt>
                            <dd>{getOriginLayerLabel(language, item.originLayer)}</dd>
                          </div>
                          <div>
                            <dt>{localCopy.sourceMeeting}</dt>
                            <dd>{item.meetingTitle || item.meetingId || "unknown"}</dd>
                          </div>
                        </dl>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="supporting-copy">{localCopy.noOpenTasks}</p>
                )}
              </div>

              <div className="subsection">
                <div className="subsection-header">
                  <p className="eyebrow">{localCopy.nextMeetingContext}</p>
                  <h4>{copy.briefing}</h4>
                </div>
                {memory.briefing.items.length > 0 ? (
                  <ul className="agenda-list">
                    {memory.briefing.items.map((item) => (
                      <li className="memory-list-card memory-context-card" key={item.id}>
                        <strong>{item.title}</strong>
                        <p className="supporting-copy">{getOriginLayerLabel(language, item.originLayer)}</p>
                        <p>{item.reason}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="supporting-copy">{localCopy.noContext}</p>
                )}
              </div>

              <div className="subsection">
                <div className="subsection-header">
                  <p className="eyebrow">{localCopy.recentDecisions}</p>
                  <h4>{copy.sourceExplanation}</h4>
                </div>
                {memory.recentDecisions.length > 0 ? (
                  <ul className="agenda-list">
                    {memory.recentDecisions.map((decision) => (
                      <li className="memory-list-card memory-context-card" key={decision.id}>
                        <strong>{decision.title}</strong>
                        <p className="supporting-copy">
                          {decision.meetingTitle || decision.meetingId || "unknown"} / {decision.decidedBy}
                        </p>
                        <p>{decision.rationale}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="supporting-copy">{localCopy.noDecisions}</p>
                )}
              </div>

              <div className="subsection">
                <div className="subsection-header">
                  <p className="eyebrow">{localCopy.meetingsOnRecord}</p>
                  <h4>{copy.meetingContext}</h4>
                </div>
                {memory.meetings.length > 0 ? (
                  <ul className="agenda-list">
                    {memory.meetings.slice(0, 4).map((meeting) => (
                      <li className="memory-list-card memory-context-card" key={meeting.meetingId}>
                        <strong>{meeting.title}</strong>
                        <p className="supporting-copy">{meeting.createdAt}</p>
                        <p>{meeting.summary}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="supporting-copy">{localCopy.noMeetings}</p>
                )}
              </div>
            </>
          ) : (
            <div className="empty-panel">
              <p>{copy.memoryEmpty}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
