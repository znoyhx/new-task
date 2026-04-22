from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectRecord,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import StudentProgress

ModelT = TypeVar("ModelT", bound=BaseModel)


class SQLiteStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def save_project(self, project: ProjectRecord) -> ProjectRecord:
        payload = project.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (project_id, name, description, domain, created_at)
                VALUES (:project_id, :name, :description, :domain, :created_at)
                ON CONFLICT(project_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    domain = excluded.domain,
                    created_at = excluded.created_at
                """,
                payload,
            )
        return project

    def save_meeting(self, meeting: ProjectMeetingRecord) -> ProjectMeetingRecord:
        payload = meeting.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO meetings (meeting_id, project_id, title, summary, created_at)
                VALUES (:meeting_id, :project_id, :title, :summary, :created_at)
                ON CONFLICT(meeting_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    title = excluded.title,
                    summary = excluded.summary,
                    created_at = excluded.created_at
                """,
                payload,
            )
        return meeting

    def save_decisions(self, project_id: str, meeting_id: str, decisions: list[ProjectDecision]) -> None:
        self._save_models(
            "decisions",
            project_id=project_id,
            meeting_id=meeting_id,
            models=decisions,
            get_record_id=lambda record: record.id,
            get_sort_text=lambda record: record.title,
            get_created_at=lambda record: record.created_at.isoformat(),
        )

    def save_action_items(self, project_id: str, meeting_id: str, action_items: list[ActionItem]) -> None:
        self._save_models(
            "action_items",
            project_id=project_id,
            meeting_id=meeting_id,
            models=action_items,
            get_record_id=lambda record: f"{meeting_id}:action:{record.title.lower()}:{record.owner.lower()}",
            get_sort_text=lambda record: record.title,
            get_created_at=lambda _record: "",
        )

    def save_claims(self, project_id: str, meeting_id: str, claims: list[Claim]) -> None:
        self._save_models(
            "claims",
            project_id=project_id,
            meeting_id=meeting_id,
            models=claims,
            get_record_id=lambda record: record.id or f"{meeting_id}:claim:{record.text.lower()}",
            get_sort_text=lambda record: record.text,
            get_created_at=lambda _record: "",
        )

    def save_advisor_ideas(self, project_id: str, meeting_id: str, advisor_ideas: list[ResearchIdea]) -> None:
        self._save_models(
            "advisor_ideas",
            project_id=project_id,
            meeting_id=meeting_id,
            models=advisor_ideas,
            get_record_id=lambda record: record.id or f"{meeting_id}:idea:{record.idea_text.lower()}",
            get_sort_text=lambda record: record.idea_text,
            get_created_at=lambda _record: "",
        )

    def save_student_progress(self, project_id: str, meeting_id: str, student_progress: list[StudentProgress]) -> None:
        self._save_models(
            "student_progress",
            project_id=project_id,
            meeting_id=meeting_id,
            models=student_progress,
            get_record_id=lambda record: f"{meeting_id}:progress:{record.student_name.lower()}",
            get_sort_text=lambda record: record.student_name,
            get_created_at=lambda _record: "",
        )

    def save_key_papers(self, project_id: str, meeting_id: str, key_papers: list[KeyPaperMemory]) -> None:
        self._save_models(
            "key_papers",
            project_id=project_id,
            meeting_id=meeting_id,
            models=key_papers,
            get_record_id=lambda record: record.id,
            get_sort_text=lambda record: record.title,
            get_created_at=lambda record: record.added_at.isoformat(),
        )

    def load_project(self, project_id: str) -> ProjectRecord | None:
        row = self._fetch_one(
            "SELECT project_id, name, description, domain, created_at FROM projects WHERE project_id = ?",
            (project_id,),
        )
        if row is None:
            return None
        return ProjectRecord.model_validate(dict(row))

    def load_meetings(self, project_id: str) -> list[ProjectMeetingRecord]:
        rows = self._fetch_all(
            """
            SELECT meeting_id, project_id, title, summary, created_at
            FROM meetings
            WHERE project_id = ?
            ORDER BY created_at ASC, meeting_id ASC
            """,
            (project_id,),
        )
        return [ProjectMeetingRecord.model_validate(dict(row)) for row in rows]

    def load_decisions(self, project_id: str) -> list[ProjectDecision]:
        return self._load_models("decisions", project_id, ProjectDecision)

    def load_action_items(self, project_id: str) -> list[ActionItem]:
        return self._load_models("action_items", project_id, ActionItem)

    def update_action_item_status(
        self,
        project_id: str,
        *,
        meeting_id: str,
        title: str,
        owner: str,
        status: str,
    ) -> ActionItem | None:
        record_id = f"{meeting_id}:action:{title.lower()}:{owner.lower()}"
        row = self._fetch_one(
            """
            SELECT payload_json
            FROM action_items
            WHERE project_id = ? AND record_id = ?
            """,
            (project_id, record_id),
        )
        if row is None:
            return None

        action_item = ActionItem.model_validate_json(row["payload_json"])
        updated_action_item = action_item.model_copy(update={"status": status})

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE action_items
                SET payload_json = ?
                WHERE project_id = ? AND record_id = ?
                """,
                (
                    json.dumps(updated_action_item.model_dump(mode="json"), ensure_ascii=True, sort_keys=True),
                    project_id,
                    record_id,
                ),
            )
        return updated_action_item

    def load_claims(self, project_id: str) -> list[Claim]:
        return self._load_models("claims", project_id, Claim)

    def load_advisor_ideas(self, project_id: str) -> list[ResearchIdea]:
        return self._load_models("advisor_ideas", project_id, ResearchIdea)

    def load_student_progress(self, project_id: str) -> list[StudentProgress]:
        return self._load_models("student_progress", project_id, StudentProgress)

    def load_key_papers(self, project_id: str) -> list[KeyPaperMemory]:
        return self._load_models("key_papers", project_id, KeyPaperMemory)

    def _save_models(
        self,
        table_name: str,
        *,
        project_id: str,
        meeting_id: str,
        models: list[ModelT],
        get_record_id,
        get_sort_text,
        get_created_at,
    ) -> None:
        with self._connect() as connection:
            for model in models:
                payload_json = json.dumps(model.model_dump(mode="json"), ensure_ascii=True, sort_keys=True)
                connection.execute(
                    f"""
                    INSERT INTO {table_name} (record_id, project_id, meeting_id, sort_text, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_id) DO UPDATE SET
                        project_id = excluded.project_id,
                        meeting_id = excluded.meeting_id,
                        sort_text = excluded.sort_text,
                        payload_json = excluded.payload_json,
                        created_at = excluded.created_at
                    """,
                    (
                        get_record_id(model),
                        project_id,
                        meeting_id,
                        get_sort_text(model),
                        payload_json,
                        get_created_at(model),
                    ),
                )

    def _load_models(self, table_name: str, project_id: str, model_type: type[ModelT]) -> list[ModelT]:
        rows = self._fetch_all(
            f"""
            SELECT payload_json
            FROM {table_name}
            WHERE project_id = ?
            ORDER BY COALESCE(created_at, '') ASC, sort_text ASC, record_id ASC
            """,
            (project_id,),
        )
        models: list[ModelT] = []
        for row in rows:
            models.append(model_type.model_validate_json(row["payload_json"]))
        return models

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(query, params)
            return cursor.fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._connect() as connection:
            cursor = connection.execute(query, params)
            return list(cursor.fetchall())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meetings (
                    meeting_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS action_items (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS claims (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS advisor_ideas (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS student_progress (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS key_papers (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT NOT NULL,
                    sort_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT
                );
                """
            )
