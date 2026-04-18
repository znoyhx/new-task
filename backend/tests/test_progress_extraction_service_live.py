from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend.adapters.deepseek_client import DeepSeekClient
from backend.config import load_settings
from backend.services.progress_extraction_service import ProgressExtractionService
from backend.services.transcript_parser_service import TranscriptParserService

LIVE_TRANSCRIPT = """
[00:00:05] Alice: This week I trained the baseline on 3k samples and reached 71 percent accuracy.
[00:00:18] Alice: The blocker is GPU memory. The 13B model runs out of memory at batch size four.
[00:00:31] Prof. Chen: Next week run a QLoRA variant and compare it with the smaller model. Prepare a short result table by Friday.
[00:00:45] Bob: I reproduced the retrieval pipeline, but the citation parser still drops equations in long papers.
[00:00:58] Prof. Chen: Bob, fix the parser and record failure cases before next Tuesday.
"""


def test_live_progress_extraction_with_deepseek() -> None:
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        pytest.skip("Repository .env file is required for the DeepSeek live test.")

    settings = load_settings(env={}, repo_root=Path.cwd(), dotenv_path=dotenv_path)
    if not settings.deepseek_api_key:
        pytest.skip("DEEPSEEK_API_KEY is not configured.")

    transcript = TranscriptParserService().parse_transcript(
        LIVE_TRANSCRIPT,
        meeting_id="live-progress-extraction",
    )
    service = ProgressExtractionService(client=DeepSeekClient(settings))

    started_at = time.time()
    snapshot = service.extract_progress(transcript, meeting_id="live-progress-extraction")
    elapsed_seconds = time.time() - started_at

    print(f"live_progress_input_lines={len(LIVE_TRANSCRIPT.strip().splitlines())}")
    print(f"live_progress_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_progress_summary={snapshot.summary}")
    print(f"live_progress_schema_ok={bool(snapshot.student_progress)}")

    names = {entry.student_name for entry in snapshot.student_progress}
    assert "Alice" in names
    assert snapshot.summary
    assert all(item.owner for item in snapshot.action_items)
    assert all(item.deadline for item in snapshot.action_items)
