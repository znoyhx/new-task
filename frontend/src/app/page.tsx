type RiskLevel = "Low" | "Medium" | "High";

type StudentProgress = {
  student: string;
  completed: string;
  result: string;
  blocker: string;
  risk: RiskLevel;
  nextStep: string;
};

type AdvisorIdea = {
  title: string;
  summary: string;
  experiment: string;
  reading: string;
  metric: string;
  evidence: string;
};

type ActionItem = {
  title: string;
  owner: string;
  dueDate: string;
  metric: string;
};

type ReadingItem = {
  title: string;
  reason: string;
  priority: string;
};

type TimelineEvent = {
  time: string;
  speaker: string;
  text: string;
};

const navigation = ["Dashboard", "Meetings", "Students", "Evidence", "Briefings", "Memory"];

const studentProgress: StudentProgress[] = [
  {
    student: "Yuan Chen",
    completed: "Finished the first retrieval-baseline run on 3 weekly meeting transcripts.",
    result: "Recall improved on action-item detection, but advisor ideas still bleed into summary blocks.",
    blocker: "Speaker turns are not normalized yet, so prompt context stays noisy.",
    risk: "Medium",
    nextStep: "Stabilize transcript chunking before adding progress extraction."
  },
  {
    student: "Lin Zhou",
    completed: "Drafted the evidence card criteria and reviewed citation traceability requirements.",
    result: "The evidence lane should stay secondary to next-week planning in the MVP.",
    blocker: "No persisted memory structure exists yet for project-level reuse.",
    risk: "Low",
    nextStep: "Lock the backend scaffolding and provider boundaries first."
  }
];

const advisorIdeas: AdvisorIdea[] = [
  {
    title: "Convert comments into validation checkpoints",
    summary: "Turn qualitative advisor comments into explicit metrics for next week's experiments.",
    experiment: "Attach one validation metric to every action item before export.",
    reading: "Look at recent literature on experiment reporting templates for research teams.",
    metric: "Every action item includes an observable success signal.",
    evidence: "Pending"
  },
  {
    title: "Keep transcript traceability visible",
    summary: "Users should always be able to jump from a plan item back to the originating transcript slice.",
    experiment: "Reserve a transcript timeline lane in the dashboard shell from day one.",
    reading: "Reference transcript-seeker style source-jump interactions later.",
    metric: "Every generated output can expose at least one transcript source anchor.",
    evidence: "Optional"
  }
];

const actionItems: ActionItem[] = [
  {
    title: "Finish repository skeleton and startup checks",
    owner: "System",
    dueDate: "This stage",
    metric: "Frontend and backend both boot locally."
  },
  {
    title: "Validate provider config contract",
    owner: "Backend",
    dueDate: "This stage",
    metric: "Config test passes with env and default paths."
  },
  {
    title: "Run DeepSeek connectivity smoke test",
    owner: "Backend",
    dueDate: "This stage",
    metric: "Real JSON response is parsed through adapter."
  }
];

const readingList: ReadingItem[] = [
  {
    title: "Adapter-first integration design notes",
    reason: "Keeps DeepSeek, OpenAlex, and Whisper swappable under backend control.",
    priority: "High"
  },
  {
    title: "Research meeting transcript UX patterns",
    reason: "Useful for the future transcript timeline and source-jump interaction.",
    priority: "Medium"
  }
];

const timeline: TimelineEvent[] = [
  {
    time: "09:00",
    speaker: "Student",
    text: "This week I finished the retrieval baseline and found two noisy transcript segments."
  },
  {
    time: "09:04",
    speaker: "Advisor",
    text: "Good. Turn that into a cleaner structure first, then define what next week's validation looks like."
  },
  {
    time: "09:07",
    speaker: "Advisor",
    text: "Keep the evidence view available, but do not let it overshadow the action plan."
  }
];

function RiskBadge({ risk }: { risk: RiskLevel }) {
  const riskClass =
    risk === "High" ? "risk-high" : risk === "Medium" ? "risk-medium" : "risk-low";

  return (
    <span className={`risk-badge ${riskClass}`}>
      <span className="risk-dot" aria-hidden="true" />
      {risk} risk
    </span>
  );
}

export default function DashboardPage() {
  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">EF</div>
          <div>
            <p className="eyebrow">Research Cockpit</p>
            <h1>EvidenceFlow Agent</h1>
          </div>
        </div>

        <div className="project-switcher card">
          <p className="eyebrow">Active Project</p>
          <strong>Multimodal Research Automation</strong>
          <p className="muted">Single-workspace MVP scaffold for weekly group meetings.</p>
        </div>

        <nav aria-label="Primary">
          <ul className="nav-list">
            {navigation.map((item, index) => (
              <li key={item}>
                <button
                  className={`nav-item ${index === 0 ? "nav-item-active" : ""}`}
                  type="button"
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer card">
          <p className="eyebrow">Empty State</p>
          <p className="muted">
            Upload a meeting transcript to generate the first research plan.
          </p>
        </div>
      </aside>

      <section className="content-column">
        <header className="hero card">
          <div>
            <p className="eyebrow">This Week&apos;s Meeting</p>
            <h2>Import, understand, and turn advisor feedback into next-week execution.</h2>
            <p className="muted hero-copy">
              Stage 1 only sets the shell: stable layout, readable density, and clear slots for
              progress extraction, idea capture, transcript traceability, and action planning.
            </p>
          </div>
          <div className="hero-actions">
            <button className="primary-button" type="button">
              Upload Transcript
            </button>
            <button className="secondary-button" type="button">
              Preview Workflow
            </button>
          </div>
        </header>

        <section className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Overview</p>
              <h3>Student Progress</h3>
            </div>
            <span className="section-meta">2 tracked students</span>
          </div>

          <div className="card-grid">
            {studentProgress.map((item) => (
              <article className="card student-card" key={item.student}>
                <div className="card-header">
                  <div>
                    <p className="eyebrow">Student</p>
                    <h4>{item.student}</h4>
                  </div>
                  <RiskBadge risk={item.risk} />
                </div>

                <dl className="detail-list">
                  <div>
                    <dt>Completed</dt>
                    <dd>{item.completed}</dd>
                  </div>
                  <div>
                    <dt>Current Result</dt>
                    <dd>{item.result}</dd>
                  </div>
                  <div>
                    <dt>Blocker</dt>
                    <dd>{item.blocker}</dd>
                  </div>
                  <div>
                    <dt>Next Step</dt>
                    <dd>{item.nextStep}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </section>

        <section className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Advisor Signals</p>
              <h3>New Ideas</h3>
            </div>
            <span className="section-meta">Action-oriented by design</span>
          </div>

          <div className="stack">
            {advisorIdeas.map((idea) => (
              <article className="card idea-card" key={idea.title}>
                <div className="card-header">
                  <div>
                    <p className="eyebrow">Idea</p>
                    <h4>{idea.title}</h4>
                  </div>
                  <button className="secondary-button compact-button" type="button">
                    Add To Plan
                  </button>
                </div>

                <dl className="detail-list">
                  <div>
                    <dt>Summary</dt>
                    <dd>{idea.summary}</dd>
                  </div>
                  <div>
                    <dt>Suggested Experiment</dt>
                    <dd>{idea.experiment}</dd>
                  </div>
                  <div>
                    <dt>Recommended Reading</dt>
                    <dd>{idea.reading}</dd>
                  </div>
                  <div>
                    <dt>Validation Metric</dt>
                    <dd>{idea.metric}</dd>
                  </div>
                  <div>
                    <dt>Evidence Status</dt>
                    <dd>{idea.evidence}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </section>

        <section className="section-block">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Traceability</p>
              <h3>Transcript Timeline</h3>
            </div>
            <span className="section-meta">Reserved for Task 3+</span>
          </div>

          <div className="card timeline-card">
            <ul className="timeline-list">
              {timeline.map((event) => (
                <li className="timeline-item" key={`${event.time}-${event.speaker}`}>
                  <div className="timeline-time">{event.time}</div>
                  <div className="timeline-content">
                    <p className="timeline-speaker">{event.speaker}</p>
                    <p className="muted">{event.text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </section>

      <aside className="decision-column">
        <div className="decision-stack">
          <section className="card emphasis-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Decision Panel</p>
                <h3>Next-Week Plan</h3>
              </div>
              <span className="status-pill">Shell Ready</span>
            </div>
            <p className="muted">
              The MVP keeps action planning visually primary. Live generation stays out of scope
              until Task 4 and Task 5.
            </p>
            <ul className="simple-list">
              {actionItems.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong>
                  <span>
                    {item.owner} / {item.dueDate}
                  </span>
                  <p>{item.metric}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Reading</p>
                <h3>Recommended Reading</h3>
              </div>
            </div>
            <ul className="simple-list">
              {readingList.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong>
                  <span>{item.priority} priority</span>
                  <p>{item.reason}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Evidence</p>
                <h3>Reference Basis</h3>
              </div>
            </div>
            <p className="muted">
              Evidence cards remain visually secondary in the dashboard shell, matching the product
              constraint that planning stays primary.
            </p>
          </section>

          <section className="card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Export</p>
                <h3>Deliverables</h3>
              </div>
            </div>
            <p className="muted">
              Weekly report, briefing, and markdown plan export panels are reserved for later tasks.
            </p>
            <button className="secondary-button full-width" type="button">
              Export Disabled In Stage 1
            </button>
          </section>
        </div>
      </aside>
    </main>
  );
}
