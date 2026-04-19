from __future__ import annotations

import mimetypes
import os
import shutil
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
    TranscriptionMetadata,
    TranscriptChunk,
)
from backend.schemas.student_progress import MeetingProgressSnapshot
from backend.services.transcript_parser_service import TranscriptParserService

SUPPORTED_AUDIO_FORMATS: dict[str, set[str]] = {
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "audio/m4a"},
    ".mp4": {"audio/mp4", "video/mp4"},
    ".webm": {"audio/webm", "video/webm"},
}
DEFAULT_MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024


class AudioTranscriber(Protocol):
    def transcribe_file(
        self,
        file_path: str | Path,
        *,
        language_hint: str | None = None,
    ) -> dict[str, Any]:
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
        if request.source_type == "transcript":
            transcript_text = self._load_transcript_text(request)
            parsed_transcript = self.parser.parse_transcript(transcript_text)
            return self._persist_import(
                meeting_title=request.meeting_title,
                source_type="transcript",
                transcript_text=transcript_text,
                parsed_transcript=parsed_transcript,
            )

        source_audio_path = self._resolve_existing_file(request.audio_path)
        filename = source_audio_path.name
        content_type = self._resolve_audio_content_type(
            filename=filename,
            content_type=self._guess_content_type(filename),
        )
        size_bytes = source_audio_path.stat().st_size
        self._validate_audio_source(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        meeting_id, meeting_dir = self._create_meeting_workspace()
        stored_audio_path = self._copy_audio_into_workspace(meeting_dir, source_audio_path)
        transcript_text, parsed_transcript, metadata = self._transcribe_audio(
            stored_audio_path,
            meeting_id=meeting_id,
            audio_filename=filename,
            audio_content_type=content_type,
            audio_size_bytes=size_bytes,
            language_hint=request.language_hint,
        )
        return self._persist_import(
            meeting_id=meeting_id,
            meeting_dir=meeting_dir,
            meeting_title=request.meeting_title,
            source_type="audio",
            transcript_text=transcript_text,
            parsed_transcript=parsed_transcript,
            audio_path=stored_audio_path,
            transcription_metadata=metadata,
        )

    def import_uploaded_audio(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        meeting_title: str | None = None,
        language_hint: str | None = None,
    ) -> MeetingImportResponse:
        safe_filename = self._sanitize_filename(filename)
        resolved_content_type = self._resolve_audio_content_type(
            filename=safe_filename,
            content_type=content_type,
        )
        self._validate_audio_source(
            filename=safe_filename,
            content_type=resolved_content_type,
            size_bytes=len(file_bytes),
        )

        meeting_id, meeting_dir = self._create_meeting_workspace()
        stored_audio_path = self._store_uploaded_audio(
            meeting_dir,
            file_bytes=file_bytes,
            filename=safe_filename,
        )
        transcript_text, parsed_transcript, metadata = self._transcribe_audio(
            stored_audio_path,
            meeting_id=meeting_id,
            audio_filename=safe_filename,
            audio_content_type=resolved_content_type,
            audio_size_bytes=len(file_bytes),
            language_hint=language_hint,
        )
        return self._persist_import(
            meeting_id=meeting_id,
            meeting_dir=meeting_dir,
            meeting_title=meeting_title,
            source_type="audio",
            transcript_text=transcript_text,
            parsed_transcript=parsed_transcript,
            audio_path=stored_audio_path,
            transcription_metadata=metadata,
        )

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

    def load_transcription_metadata(self, meeting_id: str) -> TranscriptionMetadata:
        meeting = self.load_meeting(meeting_id)
        if not meeting.transcription_metadata_path:
            raise FileNotFoundError(f"Meeting '{meeting_id}' does not have transcription metadata.")

        metadata_path = Path(meeting.transcription_metadata_path)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Transcription metadata not found for '{meeting_id}'.")
        return TranscriptionMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))

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

    def _persist_import(
        self,
        *,
        meeting_id: str | None = None,
        meeting_dir: Path | None = None,
        meeting_title: str | None,
        source_type: str,
        transcript_text: str,
        parsed_transcript: ParsedTranscript,
        audio_path: Path | None = None,
        transcription_metadata: TranscriptionMetadata | None = None,
    ) -> MeetingImportResponse:
        resolved_meeting_id = meeting_id or self._generate_meeting_id()
        resolved_meeting_dir = meeting_dir or self._meeting_dir(resolved_meeting_id)
        resolved_meeting_dir.mkdir(parents=True, exist_ok=True)
        resolved_transcript = (
            parsed_transcript
            if parsed_transcript.meeting_id == resolved_meeting_id
            else parsed_transcript.model_copy(update={"meeting_id": resolved_meeting_id})
        )

        transcript_path = resolved_meeting_dir / "transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        parsed_transcript_path = resolved_meeting_dir / "transcript_chunks.json"
        parsed_transcript_path.write_text(
            resolved_transcript.model_dump_json(indent=2),
            encoding="utf-8",
        )

        metadata_path: Path | None = None
        if transcription_metadata is not None:
            metadata = transcription_metadata.model_copy(
                update={
                    "audio_path": str(audio_path) if audio_path else transcription_metadata.audio_path,
                    "transcript_path": str(transcript_path),
                    "parsed_transcript_path": str(parsed_transcript_path),
                    "segment_count": resolved_transcript.chunk_count,
                }
            )
            metadata_path = resolved_meeting_dir / "transcription_metadata.json"
            metadata_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        else:
            metadata = None

        meeting = MeetingRecord(
            meeting_id=resolved_meeting_id,
            meeting_title=meeting_title,
            source_type=source_type,
            status="imported",
            created_at=datetime.now(timezone.utc),
            transcript_path=str(transcript_path),
            parsed_transcript_path=str(parsed_transcript_path),
            audio_path=str(audio_path) if audio_path else None,
            progress_path=None,
            transcription_metadata_path=str(metadata_path) if metadata_path else None,
            audio_filename=metadata.audio_filename if metadata else None,
            audio_content_type=metadata.audio_content_type if metadata else None,
            audio_size_bytes=metadata.audio_size_bytes if metadata else None,
            transcription_backend=metadata.backend if metadata else None,
            transcription_language=metadata.detected_language if metadata else None,
            transcription_status=metadata.status if metadata else "not_requested",
            transcription_warning_messages=list(metadata.warning_messages) if metadata else [],
        )
        self._write_meeting_record(meeting)
        return MeetingImportResponse(meeting=meeting, transcript=resolved_transcript)

    def _transcribe_audio(
        self,
        audio_path: Path,
        *,
        meeting_id: str,
        audio_filename: str,
        audio_content_type: str | None,
        audio_size_bytes: int,
        language_hint: str | None,
    ) -> tuple[str, ParsedTranscript, TranscriptionMetadata]:
        try:
            payload = self.audio_transcriber.transcribe_file(
                audio_path,
                language_hint=language_hint,
            )
        except (NotImplementedError, RuntimeError, ValueError) as exc:
            raise TranscriptionServiceError(str(exc)) from exc

        transcript_text = str(payload.get("text", "")).strip()
        segments = payload.get("segments")
        warning_messages = self._normalize_warnings(payload.get("warnings"))
        detected_language = self._normalize_optional_string(
            payload.get("language") or payload.get("detected_language")
        )
        if segments:
            parsed_transcript = self._parse_audio_segments(segments, meeting_id=meeting_id)
            if not transcript_text:
                transcript_text = "\n".join(
                    f"{chunk.speaker}: {chunk.text}" if chunk.speaker else chunk.text
                    for chunk in parsed_transcript.chunks
                )
        else:
            if not transcript_text:
                raise TranscriptionServiceError(
                    "Local transcription did not return any usable transcript text."
                )
            parsed_transcript = self.parser.parse_transcript(transcript_text, meeting_id=meeting_id)

        if not transcript_text.strip():
            raise TranscriptionServiceError("The generated transcript is empty after normalization.")

        metadata = TranscriptionMetadata(
            status="completed",
            backend=str(payload.get("backend") or self.settings.transcription_backend),
            language_hint=language_hint,
            detected_language=detected_language,
            warning_messages=warning_messages,
            elapsed_seconds=self._coerce_float(payload.get("elapsed_seconds")),
            duration_seconds=self._coerce_float(payload.get("duration_seconds")),
            segment_count=parsed_transcript.chunk_count,
            audio_filename=audio_filename,
            audio_content_type=audio_content_type,
            audio_size_bytes=audio_size_bytes,
            audio_path=str(audio_path),
        )
        return transcript_text, parsed_transcript, metadata

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

    def _create_meeting_workspace(self) -> tuple[str, Path]:
        meeting_id = self._generate_meeting_id()
        meeting_dir = self._meeting_dir(meeting_id)
        meeting_dir.mkdir(parents=True, exist_ok=True)
        return meeting_id, meeting_dir

    def _write_meeting_record(self, meeting: MeetingRecord) -> None:
        meeting_path = self._meeting_dir(meeting.meeting_id) / "meeting.json"
        meeting_path.parent.mkdir(parents=True, exist_ok=True)
        meeting_path.write_text(meeting.model_dump_json(indent=2), encoding="utf-8")

    def _meeting_dir(self, meeting_id: str) -> Path:
        return self.settings.data_dir / "meetings" / meeting_id

    def _generate_meeting_id(self) -> str:
        return f"meeting-{uuid4().hex[:12]}"

    def _sanitize_filename(self, filename: str | None) -> str:
        sanitized = Path(filename or "").name.strip()
        if not sanitized:
            raise TranscriptionServiceError("Uploaded audio file must include a valid filename.")
        return sanitized

    def _store_uploaded_audio(self, meeting_dir: Path, *, file_bytes: bytes, filename: str) -> Path:
        if not file_bytes:
            raise TranscriptionServiceError("Uploaded audio file is empty.")
        source_dir = meeting_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(filename).suffix.lower()
        stored_audio_path = source_dir / f"original{extension}"
        stored_audio_path.write_bytes(file_bytes)
        return stored_audio_path

    def _copy_audio_into_workspace(self, meeting_dir: Path, source_audio_path: Path) -> Path:
        source_dir = meeting_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        extension = source_audio_path.suffix.lower()
        stored_audio_path = source_dir / f"original{extension}"
        shutil.copy2(source_audio_path, stored_audio_path)
        return stored_audio_path

    def _resolve_existing_file(self, raw_path: str | Path | None) -> Path:
        if raw_path is None:
            raise TranscriptionServiceError("A file path is required.")
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.settings.repo_root / path
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path

    def _resolve_audio_content_type(self, *, filename: str, content_type: str | None) -> str | None:
        if content_type:
            return content_type.strip().lower()
        return self._guess_content_type(filename)

    def _guess_content_type(self, filename: str) -> str | None:
        guessed, _ = mimetypes.guess_type(filename)
        return guessed.lower() if guessed else None

    def _validate_audio_source(
        self,
        *,
        filename: str,
        content_type: str | None,
        size_bytes: int,
    ) -> None:
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_AUDIO_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_AUDIO_FORMATS))
            raise TranscriptionServiceError(
                f"Unsupported audio format '{extension or 'unknown'}'. Supported formats: {supported}."
            )

        normalized_content_type = (content_type or "").strip().lower()
        if (
            normalized_content_type
            and normalized_content_type != "application/octet-stream"
            and normalized_content_type not in SUPPORTED_AUDIO_FORMATS[extension]
        ):
            raise TranscriptionServiceError(
                f"Audio content type '{normalized_content_type}' does not match file extension '{extension}'."
            )

        if size_bytes <= 0:
            raise TranscriptionServiceError("Audio file is empty.")

        max_audio_size_bytes = self._max_audio_size_bytes()
        if size_bytes > max_audio_size_bytes:
            limit_mb = max_audio_size_bytes // (1024 * 1024)
            raise TranscriptionServiceError(
                f"Audio file is too large. The maximum supported size is {limit_mb} MB."
            )

    def _max_audio_size_bytes(self) -> int:
        raw_value = os.getenv("EVIDENCEFLOW_MAX_AUDIO_SIZE_MB")
        if not raw_value:
            return DEFAULT_MAX_AUDIO_SIZE_BYTES
        try:
            megabytes = int(raw_value)
        except ValueError:
            return DEFAULT_MAX_AUDIO_SIZE_BYTES
        return max(megabytes, 1) * 1024 * 1024

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

    def _normalize_optional_string(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _normalize_warnings(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, list):
            warnings: list[str] = []
            for item in value:
                normalized = self._normalize_optional_string(item)
                if normalized:
                    warnings.append(normalized)
            return warnings
        normalized = self._normalize_optional_string(value)
        return [normalized] if normalized else []

    def _coerce_status(self, value: str) -> MeetingStatus:
        if value not in {"imported", "processed"}:
            return "imported"
        return value
