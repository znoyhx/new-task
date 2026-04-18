from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from backend.adapters.whisper_adapter import WhisperAdapter
from backend.config import Settings, get_settings
from backend.schemas.meeting import (
    MeetingImportRequest,
    MeetingImportResponse,
    MeetingRecord,
    MeetingStatus,
    ParsedTranscript,
    TranscriptChunk,
)
from backend.schemas.student_progress import MeetingProgressSnapshot
from backend.services.transcript_parser_service import TranscriptParserService


class AudioTranscriber(Protocol):
    def transcribe_file(self, file_path: str | Path) -> dict[str, Any]:
        ...


class TranscriptionServiceError(RuntimeError):
    """Raised when meeting import or transcript persistence fails."""


class TranscriptionService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        parser: TranscriptParserService | None = None,
        audio_transcriber: AudioTranscriber | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.parser = parser or TranscriptParserService()
        self.audio_transcriber = audio_transcriber or WhisperAdapter(self.settings)

    def import_meeting(self, request: MeetingImportRequest) -> MeetingImportResponse:
        meeting_id = self._generate_meeting_id()
        meeting_dir = self._meeting_dir(meeting_id)
        meeting_dir.mkdir(parents=True, exist_ok=True)

        if request.source_type == "transcript":
            transcript_text = self._load_transcript_text(request)
            parsed_transcript = self.parser.parse_transcript(transcript_text, meeting_id=meeting_id)
            audio_path: Path | None = None
        else:
            audio_path = self._resolve_existing_file(request.audio_path)
            transcript_text, parsed_transcript = self._transcribe_audio(audio_path, meeting_id=meeting_id)

        transcript_path = meeting_dir / "transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        parsed_transcript_path = meeting_dir / "transcript_chunks.json"
        parsed_transcript_path.write_text(
            parsed_transcript.model_dump_json(indent=2),
            encoding="utf-8",
        )

        meeting = MeetingRecord(
            meeting_id=meeting_id,
            meeting_title=request.meeting_title,
            source_type=request.source_type,
            status="imported",
            created_at=datetime.now(timezone.utc),
            transcript_path=str(transcript_path),
            parsed_transcript_path=str(parsed_transcript_path),
            audio_path=str(audio_path) if audio_path else None,
            progress_path=None,
        )
        self._write_meeting_record(meeting)
        return MeetingImportResponse(meeting=meeting, transcript=parsed_transcript)

    def load_meeting(self, meeting_id: str) -> MeetingRecord:
        meeting_path = self._meeting_dir(meeting_id) / "meeting.json"
        if not meeting_path.exists():
            raise FileNotFoundError(f"Meeting metadata not found for '{meeting_id}'.")
        return MeetingRecord.model_validate_json(meeting_path.read_text(encoding="utf-8"))

    def load_transcript(self, meeting_id: str) -> ParsedTranscript:
        meeting = self.load_meeting(meeting_id)
        transcript_path = Path(meeting.parsed_transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Parsed transcript not found for '{meeting_id}'.")
        return ParsedTranscript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    def save_progress_snapshot(
        self,
        meeting_id: str,
        snapshot: MeetingProgressSnapshot,
    ) -> MeetingRecord:
        meeting = self.load_meeting(meeting_id)
        progress_path = self._meeting_dir(meeting_id) / "progress.json"
        progress_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

        updated_meeting = meeting.model_copy(
            update={
                "status": self._coerce_status("processed"),
                "progress_path": str(progress_path),
            }
        )
        self._write_meeting_record(updated_meeting)
        return updated_meeting

    def load_progress_snapshot(self, meeting_id: str) -> MeetingProgressSnapshot:
        meeting = self.load_meeting(meeting_id)
        if not meeting.progress_path:
            raise FileNotFoundError(f"Meeting '{meeting_id}' has not been processed yet.")

        progress_path = Path(meeting.progress_path)
        if not progress_path.exists():
            raise FileNotFoundError(f"Saved progress snapshot not found for '{meeting_id}'.")

        return MeetingProgressSnapshot.model_validate_json(progress_path.read_text(encoding="utf-8"))

    def _load_transcript_text(self, request: MeetingImportRequest) -> str:
        if request.transcript_text:
            return request.transcript_text.strip()
        if request.transcript_path:
            transcript_path = self._resolve_existing_file(request.transcript_path)
            return transcript_path.read_text(encoding="utf-8").strip()
        raise TranscriptionServiceError("Transcript import requires transcript_text or transcript_path.")

    def _transcribe_audio(self, audio_path: Path, *, meeting_id: str) -> tuple[str, ParsedTranscript]:
        try:
            payload = self.audio_transcriber.transcribe_file(audio_path)
        except NotImplementedError as exc:
            raise TranscriptionServiceError(str(exc)) from exc

        transcript_text = str(payload.get("text", "")).strip()
        segments = payload.get("segments")
        if segments:
            parsed_transcript = self._parse_audio_segments(segments, meeting_id=meeting_id)
            if not transcript_text:
                transcript_text = "\n".join(
                    f"{chunk.speaker}: {chunk.text}" if chunk.speaker else chunk.text
                    for chunk in parsed_transcript.chunks
                )
            return transcript_text, parsed_transcript

        if not transcript_text:
            raise TranscriptionServiceError("Audio transcription did not return text or segments.")

        return transcript_text, self.parser.parse_transcript(transcript_text, meeting_id=meeting_id)

    def _parse_audio_segments(self, segments: Any, *, meeting_id: str) -> ParsedTranscript:
        if not isinstance(segments, list):
            raise TranscriptionServiceError("Audio transcription segments must be a list.")

        chunks: list[TranscriptChunk] = []
        for index, raw_segment in enumerate(segments, start=1):
            if not isinstance(raw_segment, dict):
                continue
            text = str(raw_segment.get("text", "")).strip()
            if not text:
                continue

            start_seconds = self._coerce_float(raw_segment.get("start"))
            end_seconds = self._coerce_float(raw_segment.get("end"))
            chunks.append(
                TranscriptChunk(
                    chunk_id=f"chunk-{index:04d}",
                    speaker=str(raw_segment.get("speaker", "Unknown")).strip() or "Unknown",
                    text=text,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    timestamp_start=self._format_seconds(start_seconds),
                    timestamp_end=self._format_seconds(end_seconds),
                    source_line_start=index,
                    source_line_end=index,
                )
            )

        return ParsedTranscript(meeting_id=meeting_id, chunks=chunks)

    def _write_meeting_record(self, meeting: MeetingRecord) -> None:
        meeting_path = self._meeting_dir(meeting.meeting_id) / "meeting.json"
        meeting_path.parent.mkdir(parents=True, exist_ok=True)
        meeting_path.write_text(meeting.model_dump_json(indent=2), encoding="utf-8")

    def _meeting_dir(self, meeting_id: str) -> Path:
        return self.settings.data_dir / "meetings" / meeting_id

    def _generate_meeting_id(self) -> str:
        return f"meeting-{uuid4().hex[:12]}"

    def _resolve_existing_file(self, raw_path: str | Path | None) -> Path:
        if raw_path is None:
            raise TranscriptionServiceError("A file path is required.")
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.settings.repo_root / path
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path

    def _coerce_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_seconds(self, value: float | None) -> str | None:
        if value is None:
            return None

        total_seconds = int(value)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _coerce_status(self, value: str) -> MeetingStatus:
        if value not in {"imported", "processed"}:
            return "imported"
        return value
