# EvidenceFlow Agent

EvidenceFlow Agent is a local-first research cockpit for weekly group meetings. It turns a transcript into structured student progress, advisor ideas, next-week action items, recommended reading, evidence-aware claims, project memory, briefing output, and Markdown deliverables.

## Structure

- `backend/`: FastAPI backend, agent orchestration, local storage, tests
- `frontend/`: Next.js dashboard implementing the three-column Research Cockpit workflow
- `data/samples/`: fixed demo transcript and expected output notes
- `docs/`: product docs, development notes, implementation plan, demo script

## Run

Backend:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

If `next dev` is blocked in the current environment, use:

```powershell
cd frontend
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

## Test

Backend:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run test:frontend
```

## Demo

Use the fixed transcript in [demo_meeting_transcript.md](D:/SomeFunnyProjFromGithub/NewTask/data/samples/demo_meeting_transcript.md) and the walkthrough in [demo-script.md](D:/SomeFunnyProjFromGithub/NewTask/docs/development/demo-script.md).
