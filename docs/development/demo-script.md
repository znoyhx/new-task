# EvidenceFlow Agent Demo Script

## Goal

Show a stable 5 to 7 minute flow from meeting import to next-week execution, while making the agent orchestration, memory reuse, and deliverable carryover visible enough for a competition demo.

## Demo Assets

- Transcript: `data/samples/demo_meeting_transcript.md`
- Audio: `data/samples/demo_meeting_audio.wav`
- Expected structure: `data/samples/demo_expected_output.md`
- Continuity story:
  - Meeting A: use the demo transcript or audio once to seed project memory
  - Meeting B: rerun a follow-up transcript under the same project to show carryover in briefing and deliverables

## Demo Setup

- Ensure the backend environment already has local audio dependencies installed:
  - `python-multipart`
  - `faster-whisper`
- For a faster live demo on CPU, set `FASTER_WHISPER_MODEL_SIZE=tiny.en` before starting the backend.
- Warm up the audio path once before presenting if the model has not been downloaded yet, otherwise the first run will spend extra time downloading and loading the Whisper model.

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
- Narrate the visible orchestration panel, not just the spinner:
  - active agent
  - agent goal
  - input source
  - output target
  - fallback strategy
- Call out the main stages in agent language:
  - `主控 Agent` confirms the meeting is reviewable
  - `记忆管家 Agent` checks whether prior project memory should shape the run
  - `推进 Agent` extracts progress, captures ideas, and turns them into next-week execution
  - `推荐阅读 Agent` proposes the smallest reading set that unblocks the next week
  - `证据猎手 Agent` only activates when a claim materially affects next-step decisions

### 2A. Show the Audio Import Path

- Switch the meeting input mode from `Transcript` to `Audio`.
- Select `data/samples/demo_meeting_audio.wav`.
- Start processing again and point out that the UI now shows the longer audio-specific chain:
  - audio upload
  - local transcription
  - transcript parsing
  - progress extraction
  - idea capture
  - evidence retrieval
  - plan generation
- Mention that the original audio, generated transcript, parsed chunks, and transcription metadata all stay in local storage.

### 3. Review the Main Outputs

- In the middle column, show:
  - Alice's weekly progress
  - the calibration regression risk
  - the incomplete ablation table blocker
  - the two advisor ideas
- In the transcript timeline, click the highlighted claim or evidence item to show traceability back to the originating transcript slice.
- In the orchestration area and result cards, explicitly point out the explanation layer:
  - action items show where they came from
  - reading recommendations show which idea or blocker they support
  - claims show why verification was triggered
  - briefing items show whether they come from current transcript or history memory

### 4. Review the Execution Panel

- In the right column, show:
  - next-week action items
  - recommended reading
  - the optional claim and evidence lane
  - the briefing and export panel
- Emphasize that planning and reading stay visually primary, while evidence remains secondary but traceable.
- Make one action item your anchor example and narrate:
  - owner
  - due date
  - success metric
  - why it exists
  - whether it comes from the current meeting, prior memory, or evidence retrieval

### 5. Export Deliverables

- Open the briefing panel.
- Cycle through the four Markdown deliverables:
  - weekly report
  - next-meeting briefing
  - next-week research plan
  - presentation outline
- Mention that the backend generates these from project memory, not from raw transcript text alone.

### 6. Show Continuity Across Meetings

- Keep the same project selected.
- Import a second follow-up meeting.
- During processing, point out that `记忆管家 Agent` now reports prior meetings and open carryover tasks.
- On the result screen, show:
  - the memory summary strip
  - briefing items marked as coming from `history memory`
  - action items that cite prior memory in their source explanation
  - deliverables with a `Carryover From Earlier Meetings` section
- The key line to say here is:
  - `The second meeting is not starting from zero. The agent is reusing last week's unresolved work and rolling it forward into next week's execution.`

## Suggested Talk Track

`EvidenceFlow is not just a meeting summarizer. It turns a weekly research meeting into next-week execution.`

`The visible agent layer matters here: the controller coordinates the run, memory decides what must carry over, execution turns ideas into tasks, reading supports the plan, and evidence only activates when a claim really matters.`

`The second meeting proves continuity. The agent reads long-term memory, carries unfinished work into the new briefing, and exports deliverables that already know what is still open.`

## Validation Checklist

- The transcript loads without manual editing.
- The audio sample imports without needing a filesystem `audio_path` in the browser.
- The processing states appear in order.
- The orchestration panel shows the current agent, goal, inputs, outputs, and fallback.
- The audio flow shows `audio upload`, `local transcription`, and `transcript parsing` before the downstream agent stages.
- Student progress, advisor ideas, and action items all render.
- Action items, reading recommendations, claims, and briefing items all show source explanations.
- At least one evidence-sensitive claim is visible.
- Markdown deliverables are non-empty and readable.
- On the second meeting, memory usage is non-empty and at least one carryover item is visible in the briefing or deliverables.
