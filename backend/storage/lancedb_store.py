from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from backend.schemas.project_memory import (
    ProjectMemorySearchHit,
    ProjectMemoryVectorRecord,
)

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class LanceDBStore:
    """
    Local memory store with a LanceDB-shaped interface.

    The repository does not yet ship LanceDB or local embedding dependencies, so this
    implementation persists records on disk and provides deterministic lexical search.
    """

    def __init__(self, base_path: Path | str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.records_path = self.base_path / "project_memory_records.json"
        if not self.records_path.exists():
            self.records_path.write_text("[]", encoding="utf-8")

    def upsert_records(self, records: Iterable[ProjectMemoryVectorRecord]) -> None:
        existing = {
            record["entry_id"]: record
            for record in self._load_raw_records()
        }
        for record in records:
            existing[record.entry_id] = record.model_dump(mode="json")
        self.records_path.write_text(
            json.dumps(list(existing.values()), ensure_ascii=True, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def search(self, project_id: str, query: str, *, limit: int = 5) -> list[ProjectMemorySearchHit]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[ProjectMemorySearchHit] = []
        for raw_record in self._load_raw_records():
            record = ProjectMemoryVectorRecord.model_validate(raw_record)
            if record.project_id != project_id:
                continue

            score = self._score_record(record.text, query_tokens)
            if score <= 0:
                continue

            hits.append(
                ProjectMemorySearchHit(
                    entry_id=record.entry_id,
                    project_id=record.project_id,
                    meeting_id=record.meeting_id,
                    entry_type=record.entry_type,
                    text=record.text,
                    score=score,
                    metadata=record.metadata,
                )
            )

        hits.sort(key=lambda item: (-item.score, item.entry_id))
        return hits[:limit]

    def _load_raw_records(self) -> list[dict[str, object]]:
        try:
            payload = json.loads(self.records_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def _tokenize(self, text: str) -> set[str]:
        return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)}

    def _score_record(self, text: str, query_tokens: set[str]) -> float:
        text_tokens = self._tokenize(text)
        if not text_tokens:
            return 0.0

        overlap = query_tokens & text_tokens
        score = len(overlap) / max(len(query_tokens), 1)
        normalized_text = text.lower()
        normalized_query = " ".join(sorted(query_tokens))
        if normalized_query and normalized_query in normalized_text:
            score += 0.5
        return round(score, 4)
