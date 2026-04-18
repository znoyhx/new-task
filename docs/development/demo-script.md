# EvidenceFlow Agent Demo Script

## Goal

Show a stable 5-minute flow from transcript import to research execution outputs without changing the product direction defined in the PRD and UI spec.

## Demo Assets

- Transcript: `data/samples/demo_meeting_transcript.md`
- Expected structure: `data/samples/demo_expected_output.md`

## Demo Flow

### 1. Start on the Dashboard

- Open the Research Cockpit dashboard.
- Point out the three-column layout:
  - left: project and meeting context
  - middle: meeting understanding
  - right: execution and evidence outputs
- Show the upload-first workflow and say that the product is designed to convert a weekly group meeting into next-week execution.

### 2. Load the Demo Transcript

- Paste or load `data/samples/demo_meeting_transcript.md`.
- Start processing.
- Narrate the visible stages:
  - transcript parsing
  - progress extraction
  - idea capture
  - evidence retrieval
  - plan generation

### 3. Review the Main Outputs

- In the middle column, show:
  - Alice's weekly progress
  - the calibration regression risk
  - the incomplete ablation table blocker
  - the two advisor ideas
- In the transcript timeline, click the highlighted claim or evidence item to show traceability back to the originating transcript slice.

### 4. Review the Execution Panel

- In the right column, show:
  - next-week action items
  - recommended reading
  - the optional claim and evidence lane
  - the briefing and export panel
- Emphasize that planning and reading stay visually primary, while evidence remains secondary but traceable.

### 5. Export Deliverables

- Open the briefing panel.
- Cycle through the four Markdown deliverables:
  - weekly report
  - next-meeting briefing
  - next-week research plan
  - presentation outline
- Mention that the backend generates these from project memory, not from raw transcript text alone.

## Suggested Talk Track

`EvidenceFlow is not just a meeting summarizer. It turns a weekly research meeting into next-week execution.`

`The system extracts student progress, captures advisor ideas, produces actionable tasks and reading, keeps evidence traceability available, and generates briefing-ready deliverables from project memory.`

## Validation Checklist

- The transcript loads without manual editing.
- The processing states appear in order.
- Student progress, advisor ideas, and action items all render.
- At least one evidence-sensitive claim is visible.
- Markdown deliverables are non-empty and readable.
