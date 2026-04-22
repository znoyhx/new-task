# EvidenceFlow Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MVP for a weekly research-group progress agent that converts student updates and advisor ideas into next-week research plans, reading recommendations, project memory, and delivery artifacts.

**Architecture:** The system uses a Next.js frontend and a FastAPI backend. The backend owns all agent orchestration, local transcription, local memory, and evidence retrieval through adapter layers so model and search providers stay swappable.

**Tech Stack:** Next.js, React, TypeScript, FastAPI, Python, SQLite, LanceDB, DeepSeek Chat API, faster-whisper or whisper.cpp, fastembed or sentence-transformers.

**Verification Rule:** Every agent feature must pass both local tests and one real request to the configured DeepSeek API before it is considered complete.

**Subagent Rule:** Subagents may be used when tasks can be split into non-overlapping write scopes or parallel validation work. Do not use subagents for tightly coupled blocking edits, and always review subagent output before accepting it.

---

### Task 1: Scaffold Repository Structure

**Files:**
- Create: `frontend/`
- Create: `backend/`
- Create: `backend/api/`
- Create: `backend/agents/`
- Create: `backend/services/`
- Create: `backend/adapters/`
- Create: `backend/schemas/`
- Create: `backend/tests/`

**Step 1: Create the backend entrypoint**

Create `backend/app.py` with a FastAPI health route.

**Step 2: Create the frontend shell**

Initialize `frontend/` with a minimal app shell and dashboard page.

**Step 3: Verify startup**

Run backend and frontend dev servers separately and confirm both serve a default page.

**Step 4: Commit**

```bash
git add backend frontend
git commit -m "chore: scaffold evidenceflow app structure"
```

### Task 2: Add Configuration and Provider Adapters

**Files:**
- Create: `backend/config.py`
- Create: `backend/adapters/deepseek_client.py`
- Create: `backend/adapters/openalex_adapter.py`
- Create: `backend/adapters/whisper_adapter.py`
- Test: `backend/tests/test_config.py`

**Step 1: Write failing tests for configuration loading**

Test DeepSeek key loading and default local-storage paths.

**Step 2: Implement minimal config**

Support `DEEPSEEK_API_KEY`, local database path, embeddings provider, and transcription backend.

**Step 3: Add adapter interfaces**

Implement thin wrappers with mockable methods only:
- `chat_json()`
- `search_works()`
- `transcribe_file()`

**Step 4: Run tests**

Run:

```bash
pytest backend/tests/test_config.py -v
```

**Step 5: Commit**

```bash
git add backend/config.py backend/adapters backend/tests/test_config.py
git commit -m "feat: add provider config and adapter interfaces"
```

### Task 3: Implement Meeting Import and Transcript Processing

**Files:**
- Create: `backend/api/meetings.py`
- Create: `backend/services/transcription_service.py`
- Create: `backend/services/transcript_parser_service.py`
- Create: `backend/schemas/meeting.py`
- Test: `backend/tests/test_transcript_parser.py`

**Step 1: Write failing parser tests**

Cover transcript segmentation into speaker turns and timestamped chunks.

**Step 2: Implement transcript parser**

Normalize transcript input into structured chunks.

**Step 3: Add import endpoint**

Support transcript upload first, audio upload second.

**Step 4: Run tests**

```bash
pytest backend/tests/test_transcript_parser.py -v
```

**Step 5: Commit**

```bash
git add backend/api/meetings.py backend/services backend/schemas/meeting.py backend/tests/test_transcript_parser.py
git commit -m "feat: add meeting import and transcript parsing"
```

### Task 3A: Implement Meeting Audio Parsing and Upload Flow

**Files:**
- Modify: `backend/api/meetings.py`
- Modify: `backend/adapters/whisper_adapter.py`
- Modify: `backend/services/transcription_service.py`
- Modify: `backend/schemas/meeting.py`
- Test: `backend/tests/test_meetings_api.py`
- Test: `backend/tests/test_transcript_parser.py`

**Step 1: Write failing tests for audio upload and local transcription**

Cover:
- multipart audio upload
- supported / unsupported audio formats
- local transcription adapter result normalization
- persisted audio metadata and parsed transcript output

**Step 2: Implement local audio import endpoint**

Keep `POST /api/meetings/import` for JSON transcript or local `audio_path` import, and add a dedicated browser upload endpoint for audio files so the frontend does not need filesystem paths.

**Step 3: Implement the Whisper adapter**

Implement one local transcription backend end-to-end first:
- default backend: `faster-whisper`
- output: `text + segments`
- map segment timestamps into `TranscriptChunk`

Do not introduce any paid or hosted transcription provider.

**Step 4: Persist audio source and transcription metadata**

Save:
- original audio file
- generated transcript
- parsed transcript chunks
- transcription backend and warnings

All data must stay in local storage.

**Step 5: Run backend tests**

```bash
pytest backend/tests/test_meetings_api.py backend/tests/test_transcript_parser.py -v
```

**Step 6: Run one end-to-end audio-driven live validation**

Import a real local sample audio file, produce a transcript, then run one real DeepSeek-backed review path on that transcript-derived meeting to confirm the audio path reaches the same downstream agent workflow.

**Step 7: Commit**

```bash
git add backend/api/meetings.py backend/adapters/whisper_adapter.py backend/services/transcription_service.py backend/schemas/meeting.py backend/tests/test_meetings_api.py backend/tests/test_transcript_parser.py
git commit -m "feat: add local meeting audio parsing flow"
```

### Task 4: Implement Weekly Progress and Risk Extraction

**Files:**
- Create: `backend/services/progress_extraction_service.py`
- Create: `backend/schemas/action_item.py`
- Create: `backend/schemas/risk.py`
- Create: `backend/schemas/student_progress.py`
- Test: `backend/tests/test_progress_extraction_service.py`

**Step 1: Write failing tests**

Assert extraction returns student progress objects with completed work, current result, blockers, risks, and unresolved questions.

**Step 2: Implement extraction prompt flow**

Use DeepSeek JSON output and schema validation.

**Step 3: Add fallback behavior**

If owner or deadline is missing, mark as `unknown` instead of hallucinating.

**Step 4: Run tests**

```bash
pytest backend/tests/test_progress_extraction_service.py -v
```

**Step 5: Commit**

```bash
git add backend/services/progress_extraction_service.py backend/schemas backend/tests/test_progress_extraction_service.py
git commit -m "feat: extract weekly research progress and risks"
```

### Task 5: Implement Advisor Idea Capture, Reading Recommendations, and Research Plan Generation

**Files:**
- Create: `backend/services/idea_capture_service.py`
- Create: `backend/services/research_plan_service.py`
- Create: `backend/services/reading_recommendation_service.py`
- Create: `backend/schemas/research_idea.py`
- Create: `backend/schemas/reading_recommendation.py`
- Test: `backend/tests/test_research_plan_service.py`

**Step 1: Write failing tests**

Cover:
- advisor idea extraction
- next-week plan generation
- reading recommendation generation

**Step 2: Implement advisor idea capture**

Extract advisor suggestions into structured research ideas with suggested validation and recommended reading.

**Step 3: Implement research plan generation**

Turn ideas and blockers into actionable next-week tasks with owners, success metrics, and due dates.

**Step 4: Implement reading recommendations**

Generate a prioritized reading list based on idea topic, blocker type, and project context.

**Step 5: Run tests**

```bash
pytest backend/tests/test_research_plan_service.py -v
```

**Step 6: Commit**

```bash
git add backend/services backend/schemas backend/tests/test_research_plan_service.py
git commit -m "feat: add advisor idea capture and action plan generation"
```

### Task 6: Implement Optional Evidence Verification Layer

**Files:**
- Create: `backend/services/claim_extraction_service.py`
- Create: `backend/services/evidence_retrieval_service.py`
- Create: `backend/services/claim_verification_service.py`
- Create: `backend/schemas/claim.py`
- Create: `backend/schemas/evidence_card.py`
- Test: `backend/tests/test_claim_verification_service.py`

**Step 1: Write failing tests**

Cover:
- claim extraction
- evidence retrieval result mapping
- verdict classification (`supported`, `contradicted`, `needs_verification`)

**Step 2: Implement claim extraction**

Extract only high-value factual or strategic statements, not every sentence.

**Step 3: Implement evidence retrieval**

Start with OpenAlex search and map top results into evidence cards.

**Step 4: Implement verification**

Use DeepSeek to compare claim text with evidence snippets and produce a verdict.

**Step 5: Run tests**

```bash
pytest backend/tests/test_claim_verification_service.py -v
```

**Step 6: Commit**

```bash
git add backend/services backend/schemas backend/tests/test_claim_verification_service.py
git commit -m "feat: add optional evidence verification layer"
```

### Task 7: Implement Project Memory

**Files:**
- Create: `backend/storage/sqlite_store.py`
- Create: `backend/storage/lancedb_store.py`
- Create: `backend/services/project_memory_service.py`
- Create: `backend/schemas/project_memory.py`
- Test: `backend/tests/test_project_memory_service.py`

**Step 1: Write failing tests**

Cover saving and retrieving:
- decisions
- action items
- claims
- advisor ideas
- student progress
- key papers

**Step 2: Implement SQLite metadata store**

Persist projects, meetings, claims, and action items.

**Step 3: Implement vector memory**

Persist searchable meeting chunks and project notes locally.

**Step 4: Run tests**

```bash
pytest backend/tests/test_project_memory_service.py -v
```

**Step 5: Commit**

```bash
git add backend/storage backend/services/project_memory_service.py backend/schemas/project_memory.py backend/tests/test_project_memory_service.py
git commit -m "feat: add local project memory storage"
```

### Task 8: Implement Briefing and Deliverable Generation

**Files:**
- Create: `backend/services/briefing_service.py`
- Create: `backend/services/deliverable_service.py`
- Create: `backend/api/deliverables.py`
- Test: `backend/tests/test_briefing_service.py`

**Step 1: Write failing tests**

Cover briefing output sections:
- last advisor ideas
- student commitments
- open tasks
- risks
- recommended agenda

**Step 2: Implement briefing generator**

Use project memory, not raw transcript only.

**Step 3: Implement deliverable generator**

Support:
- weekly report
- next-meeting briefing
- next-week research plan
- presentation outline

**Step 4: Run tests**

```bash
pytest backend/tests/test_briefing_service.py -v
```

**Step 5: Commit**

```bash
git add backend/services/briefing_service.py backend/services/deliverable_service.py backend/api/deliverables.py backend/tests/test_briefing_service.py
git commit -m "feat: generate briefings and delivery artifacts"
```

### Task 9: Build MVP Frontend Workflow

**Files:**
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/meeting-upload.tsx`
- Create: `frontend/src/components/action-items-panel.tsx`
- Create: `frontend/src/components/evidence-panel.tsx`
- Create: `frontend/src/components/briefing-panel.tsx`
- Test: `frontend/src/components/__tests__/dashboard.test.tsx`

**Step 1: Build upload-first dashboard**

Single-page workflow:
- import meeting
- choose transcript or audio input
- view next-week plan
- view reading recommendations
- inspect optional claims and evidence
- export deliverables

**Step 2: Add traceability UI**

Show transcript snippet and source link for each claim/evidence card.

**Step 3: Add audio-processing states**

For audio imports, explicitly show:
- audio upload
- local transcription
- transcript parsing

Allow the user to review the generated transcript timeline before relying on downstream extraction output.

**Step 4: Add empty and loading states**

Make demo flow robust and readable.

**Step 5: Run frontend tests**

```bash
npm run test:frontend
```

**Step 6: Commit**

```bash
git add frontend
git commit -m "feat: add evidenceflow dashboard workflow"
```

### Task 10: Add Sample Data, Demo Script, and End-to-End Verification

**Files:**
- Create: `data/samples/demo_meeting_transcript.md`
- Create: `data/samples/demo_expected_output.md`
- Create: `data/samples/demo_meeting_audio.*`
- Create: `backend/tests/test_demo_flow.py`
- Create: `docs/development/demo-script.md`

**Step 1: Prepare fixed demo samples**

Include transcript and one sanitized short audio sample with:
- 1 student weekly progress report
- 2 advisor ideas
- 3 action items
- 2 risks
- 3 recommended readings
- 1 optional claim requiring evidence

Do not commit private meeting recordings.

**Step 2: Write end-to-end tests**

Assert the pipeline returns stable, non-empty structured output for:
- transcript import
- audio import

**Step 3: Write 5-minute demo script**

Cover:
- import
- optional audio upload path
- extract
- capture advisor ideas
- generate next-week research plan
- generate reading recommendations
- optionally verify a high-risk claim

**Step 4: Run end-to-end test**

```bash
pytest backend/tests/test_demo_flow.py -v
```

**Step 5: Commit**

```bash
git add data/samples backend/tests/test_demo_flow.py docs/development/demo-script.md
git commit -m "docs: add demo assets and end-to-end verification"
```
