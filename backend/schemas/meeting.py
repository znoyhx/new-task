from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.schemas.student_progress import MeetingProgressSnapshot

MeetingSourceType = Literal["transcript", "audio"]
MeetingStatus = Literal["imported", "processed"]
TranscriptionStatus = Literal["not_requested", "completed", "failed"]


class TranscriptChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chunk_id: str
    speaker: str = "Unknown"
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    timestamp_start: str | None = None
    timestamp_end: str | None = None
    source_line_start: int | None = None
    source_line_end: int | None = None


class ParsedTranscript(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str | None = None
    chunk_count: int = 0
    speakers: list[str] = Field(default_factory=list)
    normalized_text: str = ""
    chunks: list[TranscriptChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_derived_fields(self) -> "ParsedTranscript":
        self.chunk_count = len(self.chunks)
        if not self.speakers:
            self.speakers = list(dict.fromkeys(chunk.speaker for chunk in self.chunks if chunk.speaker))
        if not self.normalized_text:
            lines: list[str] = []
            for chunk in self.chunks:
                timestamp = chunk.timestamp_start or ""
                prefix = f"[{timestamp}] " if timestamp else ""
                lines.append(f"{prefix}{chunk.speaker}: {chunk.text}".strip())
            self.normalized_text = "\n".join(lines)
        return self


class MeetingImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_title: str | None = None
    source_type: MeetingSourceType = "transcript"
    transcript_text: str | None = None
    transcript_path: str | None = None
    audio_path: str | None = None
    language_hint: str | None = None

    @model_validator(mode="after")
    def validate_source_inputs(self) -> "MeetingImportRequest":
        if self.source_type == "transcript" and not (self.transcript_text or self.transcript_path):
            raise ValueError("Transcript import requires transcript_text or transcript_path.")
        if self.source_type == "audio" and not self.audio_path:
            raise ValueError("Audio import requires audio_path.")
        return self


class TranscriptionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: TranscriptionStatus = "completed"
    backend: str = "faster-whisper"
    language_hint: str | None = None
    detected_language: str | None = None
    warning_messages: list[str] = Field(default_factory=list)
    elapsed_seconds: float | None = None
    duration_seconds: float | None = None
    segment_count: int = 0
    audio_filename: str | None = None
    audio_content_type: str | None = None
    audio_size_bytes: int | None = None
    audio_path: str | None = None
    transcript_path: str | None = None
    parsed_transcript_path: str | None = None


class MeetingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    meeting_id: str
    meeting_title: str | None = None
    source_type: MeetingSourceType
    status: MeetingStatus = "imported"
    created_at: datetime
    transcript_path: str
    parsed_transcript_path: str
    audio_path: str | None = None
    progress_path: str | None = None
    transcription_metadata_path: str | None = None
    audio_filename: str | None = None
    audio_content_type: str | None = None
    audio_size_bytes: int | None = None
    transcription_backend: str | None = None
    transcription_language: str | None = None
    transcription_status: TranscriptionStatus = "not_requested"
    transcription_warning_messages: list[str] = Field(default_factory=list)


class MeetingImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting: MeetingRecord
    transcript: ParsedTranscript


class MeetingProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting: MeetingRecord
    transcript: ParsedTranscript
    progress: MeetingProgressSnapshot
