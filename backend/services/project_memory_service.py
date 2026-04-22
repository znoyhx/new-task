from __future__ import annotations

from typing import Sequence

from backend.config import Settings, get_settings
from backend.schemas.action_item import ActionItem
from backend.schemas.claim import Claim
from backend.schemas.meeting import ParsedTranscript
from backend.schemas.project_memory import (
    KeyPaperMemory,
    ProjectDecision,
    ProjectMeetingRecord,
    ProjectMemorySnapshot,
    ProjectMemoryVectorRecord,
    ProjectRecord,
)
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import StudentProgress
from backend.storage.lancedb_store import LanceDBStore
from backend.storage.sqlite_store import SQLiteStore


class ProjectMemoryService:
    def __init__(
        self,
        sqlite_store: SQLiteStore | None = None,
        vector_store: LanceDBStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        resolved_settings = settings or get_settings()
        self.sqlite_store = sqlite_store or SQLiteStore(resolved_settings.sqlite_path)
        self.vector_store = vector_store or LanceDBStore(resolved_settings.lancedb_path)

    def remember_meeting(
        self,
        project: ProjectRecord,
        meeting: ProjectMeetingRecord,
        *,
        decisions: Sequence[ProjectDecision] = (),
        action_items: Sequence[ActionItem] = (),
        claims: Sequence[Claim] = (),
        advisor_ideas: Sequence[ResearchIdea] = (),
        student_progress: Sequence[StudentProgress] = (),
        key_papers: Sequence[KeyPaperMemory] = (),
        transcript: ParsedTranscript | None = None,
    ) -> ProjectMemorySnapshot:
        self.sqlite_store.save_project(project)
        self.sqlite_store.save_meeting(meeting)

        normalized_decisions = [
            decision.model_copy(
                update={
                    "project_id": project.project_id,
                    "meeting_id": meeting.meeting_id,
                }
            )
            for decision in decisions
        ]
        normalized_action_items = [
            action_item.model_copy(
                update={
                    "meeting_id": meeting.meeting_id,
                }
            )
            for action_item in action_items
        ]
        normalized_claims = [
            claim.model_copy(update={"meeting_id": meeting.meeting_id})
            for claim in claims
        ]
        normalized_advisor_ideas = [
            idea.model_copy(update={"meeting_id": meeting.meeting_id})
            for idea in advisor_ideas
        ]
        normalized_student_progress = [
            progress.model_copy(update={"meeting_id": meeting.meeting_id})
            for progress in student_progress
        ]
        normalized_key_papers = [
            paper.model_copy(
                update={
                    "project_id": project.project_id,
                    "meeting_id": meeting.meeting_id,
                }
            )
            for paper in key_papers
        ]

        self.sqlite_store.save_decisions(project.project_id, meeting.meeting_id, normalized_decisions)
        self.sqlite_store.save_action_items(project.project_id, meeting.meeting_id, normalized_action_items)
        self.sqlite_store.save_claims(project.project_id, meeting.meeting_id, normalized_claims)
        self.sqlite_store.save_advisor_ideas(project.project_id, meeting.meeting_id, normalized_advisor_ideas)
        self.sqlite_store.save_student_progress(project.project_id, meeting.meeting_id, normalized_student_progress)
        self.sqlite_store.save_key_papers(project.project_id, meeting.meeting_id, normalized_key_papers)

        vector_records = self._build_vector_records(
            project_id=project.project_id,
            meeting_id=meeting.meeting_id,
            transcript=transcript,
            decisions=normalized_decisions,
            action_items=normalized_action_items,
            claims=normalized_claims,
            advisor_ideas=normalized_advisor_ideas,
            student_progress=normalized_student_progress,
            key_papers=normalized_key_papers,
        )
        if vector_records:
            self.vector_store.upsert_records(vector_records)

        return self.load_project_memory(project.project_id)

    def load_project_memory(
        self,
        project_id: str,
        *,
        query: str | None = None,
        limit: int = 5,
    ) -> ProjectMemorySnapshot:
        snapshot = ProjectMemorySnapshot(
            project=self.sqlite_store.load_project(project_id),
            meetings=self.sqlite_store.load_meetings(project_id),
            decisions=self.sqlite_store.load_decisions(project_id),
            action_items=self.sqlite_store.load_action_items(project_id),
            claims=self.sqlite_store.load_claims(project_id),
            advisor_ideas=self.sqlite_store.load_advisor_ideas(project_id),
            student_progress=self.sqlite_store.load_student_progress(project_id),
            key_papers=self.sqlite_store.load_key_papers(project_id),
            relevant_context=[],
        )
        if query:
            snapshot = snapshot.model_copy(
                update={
                    "relevant_context": self.vector_store.search(project_id, query, limit=limit)
                }
            )
        return snapshot

    def update_action_item_status(
        self,
        project_id: str,
        *,
        meeting_id: str,
        title: str,
        owner: str,
        status: str,
    ) -> ActionItem | None:
        updated_action_item = self.sqlite_store.update_action_item_status(
            project_id,
            meeting_id=meeting_id,
            title=title,
            owner=owner,
            status=status,
        )
        if updated_action_item is None:
            return None

        self.vector_store.upsert_records(
            [
                ProjectMemoryVectorRecord(
                    entry_id=self._action_item_entry_id(meeting_id, updated_action_item),
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="action_item",
                    text=(
                        f"{updated_action_item.title}. "
                        f"owner={updated_action_item.owner}. "
                        f"deadline={updated_action_item.deadline}"
                    ),
                    metadata={
                        "priority": updated_action_item.priority,
                        "status": updated_action_item.status,
                    },
                )
            ]
        )
        return updated_action_item

    def _build_vector_records(
        self,
        *,
        project_id: str,
        meeting_id: str,
        transcript: ParsedTranscript | None,
        decisions: Sequence[ProjectDecision],
        action_items: Sequence[ActionItem],
        claims: Sequence[Claim],
        advisor_ideas: Sequence[ResearchIdea],
        student_progress: Sequence[StudentProgress],
        key_papers: Sequence[KeyPaperMemory],
    ) -> list[ProjectMemoryVectorRecord]:
        records: list[ProjectMemoryVectorRecord] = []

        if transcript is not None:
            for chunk in transcript.chunks:
                records.append(
                    ProjectMemoryVectorRecord(
                        entry_id=f"{meeting_id}:{chunk.chunk_id}",
                        project_id=project_id,
                        meeting_id=meeting_id,
                        entry_type="meeting_chunk",
                        text=f"{chunk.speaker}: {chunk.text}",
                        metadata={
                            "speaker": chunk.speaker,
                            "timestamp_start": chunk.timestamp_start,
                            "timestamp_end": chunk.timestamp_end,
                        },
                    )
                )

        for decision in decisions:
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=f"{meeting_id}:decision:{decision.id}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="decision",
                    text=f"{decision.title}. {decision.rationale}",
                    metadata={"decided_by": decision.decided_by},
                )
            )

        for action_item in action_items:
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=self._action_item_entry_id(meeting_id, action_item),
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="action_item",
                    text=f"{action_item.title}. owner={action_item.owner}. deadline={action_item.deadline}",
                    metadata={"priority": action_item.priority, "status": action_item.status},
                )
            )

        for claim in claims:
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=f"{meeting_id}:claim:{claim.id or claim.text}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="claim",
                    text=f"{claim.text}. snippet={claim.transcript_snippet}",
                    metadata={
                        "speaker": claim.speaker,
                        "verification_status": claim.verification_status,
                    },
                )
            )

        for idea in advisor_ideas:
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=f"{meeting_id}:advisor_idea:{idea.id or idea.idea_text}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="advisor_idea",
                    text=f"{idea.idea_text}. validation={idea.expected_validation}",
                    metadata={"student_name": idea.student_name},
                )
            )

        for progress in student_progress:
            blockers = ", ".join(progress.blockers) or "none"
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=f"{meeting_id}:student_progress:{progress.student_name}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="student_progress",
                    text=f"{progress.student_name}: {progress.current_result}. blockers={blockers}",
                    metadata={"student_name": progress.student_name},
                )
            )

        for paper in key_papers:
            records.append(
                ProjectMemoryVectorRecord(
                    entry_id=f"{meeting_id}:key_paper:{paper.id}",
                    project_id=project_id,
                    meeting_id=meeting_id,
                    entry_type="key_paper",
                    text=f"{paper.title}. {paper.reason}",
                    metadata={"source_url": paper.source_url},
                )
            )

        return records

    def _action_item_entry_id(self, meeting_id: str, action_item: ActionItem) -> str:
        normalized_title = action_item.title.lower().replace(" ", "_")
        normalized_owner = action_item.owner.lower().replace(" ", "_")
        return f"{meeting_id}:action_item:{normalized_title}:{normalized_owner}"
