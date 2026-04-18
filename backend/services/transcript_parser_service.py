from __future__ import annotations

import re

from backend.schemas.meeting import ParsedTranscript, TranscriptChunk

TIMESTAMP_TOKEN = r"\d{1,2}:\d{2}(?::\d{2})?"
TIMESTAMP_RANGE_TOKEN = rf"{TIMESTAMP_TOKEN}(?:\s*(?:-|–|—|to|->|~)\s*{TIMESTAMP_TOKEN})?"
SPEAKER_SEPARATOR = r"(?:[:：]|\s+-\s+)"


class TranscriptParserService:
    leading_timestamp_pattern = re.compile(
        rf"^\s*(?:\[(?P<timestamp>{TIMESTAMP_RANGE_TOKEN})\]|(?P<plain_timestamp>{TIMESTAMP_RANGE_TOKEN}))\s+"
        rf"(?P<speaker>[^:：-]+?)\s*{SPEAKER_SEPARATOR}\s*(?P<text>.+)\s*$"
    )
    speaker_first_pattern = re.compile(
        rf"^\s*(?P<speaker>[^:：\[\(]+?)\s*(?:[\[\(](?P<timestamp>{TIMESTAMP_RANGE_TOKEN})[\]\)])?\s*{SPEAKER_SEPARATOR}\s*"
        rf"(?P<text>.+)\s*$"
    )

    def parse_transcript(self, transcript_text: str, *, meeting_id: str | None = None) -> ParsedTranscript:
        normalized_input = transcript_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized_input:
            return ParsedTranscript(meeting_id=meeting_id, chunks=[])

        drafts: list[dict[str, object]] = []
        current: dict[str, object] | None = None

        for line_number, raw_line in enumerate(normalized_input.split("\n"), start=1):
            line = raw_line.strip()
            if not line:
                continue

            matched = self._match_turn_header(line)
            if matched:
                if current:
                    drafts.append(current)
                current = {
                    "speaker": matched["speaker"],
                    "text": matched["text"],
                    "timestamp_start": matched["timestamp_start"],
                    "timestamp_end": matched["timestamp_end"],
                    "start_seconds": self._timestamp_to_seconds(matched["timestamp_start"]),
                    "end_seconds": self._timestamp_to_seconds(matched["timestamp_end"]),
                    "source_line_start": line_number,
                    "source_line_end": line_number,
                }
                continue

            if current is None:
                current = {
                    "speaker": "Unknown",
                    "text": line,
                    "timestamp_start": None,
                    "timestamp_end": None,
                    "start_seconds": None,
                    "end_seconds": None,
                    "source_line_start": line_number,
                    "source_line_end": line_number,
                }
            else:
                current["text"] = f"{current['text']}\n{line}".strip()
                current["source_line_end"] = line_number

        if current:
            drafts.append(current)

        chunks = self._finalize_chunks(drafts)
        return ParsedTranscript(meeting_id=meeting_id, chunks=chunks)

    def _match_turn_header(self, line: str) -> dict[str, str | None] | None:
        for pattern in (self.leading_timestamp_pattern, self.speaker_first_pattern):
            match = pattern.match(line)
            if not match:
                continue

            speaker = (match.group("speaker") or "Unknown").strip() or "Unknown"
            timestamp_token = match.groupdict().get("timestamp") or match.groupdict().get("plain_timestamp")
            timestamp_start, timestamp_end = self._split_timestamp_range(timestamp_token)
            return {
                "speaker": speaker,
                "text": (match.group("text") or "").strip(),
                "timestamp_start": timestamp_start,
                "timestamp_end": timestamp_end,
            }
        return None

    def _split_timestamp_range(self, token: str | None) -> tuple[str | None, str | None]:
        if not token:
            return None, None

        parts = re.split(r"\s*(?:-|–|—|to|->|~)\s*", token, maxsplit=1)
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[1]

    def _timestamp_to_seconds(self, token: str | None) -> float | None:
        if not token:
            return None

        parts = token.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return float(int(minutes) * 60 + int(seconds))
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(int(hours) * 3600 + int(minutes) * 60 + int(seconds))
        return None

    def _finalize_chunks(self, drafts: list[dict[str, object]]) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []

        for index, draft in enumerate(drafts, start=1):
            if draft["end_seconds"] is None and index < len(drafts):
                next_start = drafts[index]["start_seconds"]
                if isinstance(next_start, (int, float)):
                    draft["end_seconds"] = float(next_start)

            chunk = TranscriptChunk(
                chunk_id=f"chunk-{index:04d}",
                speaker=str(draft["speaker"] or "Unknown").strip() or "Unknown",
                text=str(draft["text"] or "").strip(),
                start_seconds=draft["start_seconds"],
                end_seconds=draft["end_seconds"],
                timestamp_start=draft["timestamp_start"],
                timestamp_end=draft["timestamp_end"],
                source_line_start=draft["source_line_start"],
                source_line_end=draft["source_line_end"],
            )
            chunks.append(chunk)

        return chunks
