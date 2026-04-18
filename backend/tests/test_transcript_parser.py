from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from backend.config import load_settings
from backend.schemas.meeting import MeetingImportRequest
from backend.services.transcript_parser_service import TranscriptParserService
from backend.services.transcription_service import TranscriptionService


def make_workspace_temp_dir() -> Path:
    temp_root = Path("backend/tests/.tmp")
    temp_root.mkdir(parents=True, exist_ok=True)
    workspace = (temp_root / f"transcript-{uuid4().hex[:8]}").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def test_transcript_parser_segments_speaker_turns_and_timestamps() -> None:
    parser = TranscriptParserService()
    transcript = """
    [00:00:03] Alice: I finished dataset cleaning.
    Still checking label noise.

    [00:00:18] Bob: The baseline F1 reached 0.72.
    [00:00:32-00:00:41] Prof. Chen: Compare against the ablation and prepare a plot.
    """

    parsed = parser.parse_transcript(transcript, meeting_id="meeting-demo")

    assert parsed.meeting_id == "meeting-demo"
    assert parsed.chunk_count == 3
    assert [chunk.speaker for chunk in parsed.chunks] == ["Alice", "Bob", "Prof. Chen"]
    assert parsed.chunks[0].start_seconds == 3.0
    assert parsed.chunks[0].end_seconds == 18.0
    assert "Still checking label noise." in parsed.chunks[0].text
    assert parsed.chunks[2].end_seconds == 41.0
    assert parsed.speakers == ["Alice", "Bob", "Prof. Chen"]


def test_transcript_parser_supports_speaker_first_headers_and_unknown_lines() -> None:
    parser = TranscriptParserService()
    transcript = """
    Alice [00:01:05]: Reran the retrieval benchmark.
    Accuracy improved by 2 points.
    Follow-up note without a new header.
    """

    parsed = parser.parse_transcript(transcript)

    assert parsed.chunk_count == 1
    assert parsed.chunks[0].speaker == "Alice"
    assert parsed.chunks[0].start_seconds == 65.0
    assert "Accuracy improved by 2 points." in parsed.chunks[0].text
    assert "Follow-up note without a new header." in parsed.chunks[0].text


def test_transcription_service_imports_transcript_and_persists_parsed_output() -> None:
    data_dir = make_workspace_temp_dir()
    try:
        settings = load_settings(
            env={"DATA_DIR": str(data_dir)},
            repo_root=Path.cwd(),
            dotenv_path=Path.cwd() / "missing.env",
        )
        service = TranscriptionService(settings=settings)
        request = MeetingImportRequest(
            source_type="transcript",
            transcript_text="[00:00:01] Alice: Finished the baseline.\n[00:00:09] Bob: Need more ablations.",
        )

        response = service.import_meeting(request)

        assert Path(response.meeting.transcript_path).exists()
        assert Path(response.meeting.parsed_transcript_path).exists()
        assert response.transcript.chunk_count == 2
        saved = service.load_transcript(response.meeting.meeting_id)
        assert saved.chunks[1].speaker == "Bob"
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)
