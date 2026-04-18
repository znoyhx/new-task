from __future__ import annotations

import pytest

from backend.schemas.meeting import ParsedTranscript, TranscriptChunk
from backend.services.progress_extraction_service import (
    ProgressExtractionError,
    ProgressExtractionService,
)


class StubDeepSeekClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def chat_json(self, prompt: str, **_: object) -> dict[str, object]:
        self.prompts.append(prompt)
        return self.payload


def build_transcript() -> ParsedTranscript:
    return ParsedTranscript(
        meeting_id="meeting-123",
        chunks=[
            TranscriptChunk(
                chunk_id="chunk-0001",
                speaker="Alice",
                timestamp_start="00:01",
                text="I finished the baseline and reached 71 percent accuracy.",
            ),
            TranscriptChunk(
                chunk_id="chunk-0002",
                speaker="Prof. Chen",
                timestamp_start="00:15",
                text="Next week compare QLoRA and prepare a short table by Friday.",
            ),
        ],
    )


def test_progress_extraction_normalizes_missing_owner_and_deadline_to_unknown() -> None:
    client = StubDeepSeekClient(
        {
            "summary": "Alice reported a baseline result and one blocker.",
            "student_progress": [
                {
                    "student_name": "Alice",
                    "completed_work": ["Finished the baseline."],
                    "current_result": "71 percent accuracy.",
                    "blockers": ["GPU memory pressure."],
                    "risks": [
                        {
                            "title": "OOM on the larger model",
                            "level": "high",
                            "description": "The 13B model does not fit in memory.",
                        }
                    ],
                    "unresolved_questions": ["Will QLoRA preserve accuracy?"],
                    "next_step_suggestion": "Compare QLoRA and the smaller model.",
                    "action_items": [
                        {
                            "title": "Prepare the comparison table",
                            "priority": "high",
                            "status": "open",
                        }
                    ],
                }
            ],
        }
    )
    service = ProgressExtractionService(client=client)

    snapshot = service.extract_progress(build_transcript(), meeting_id="meeting-123")

    assert "student_progress" in client.prompts[0]
    assert snapshot.summary == "Alice reported a baseline result and one blocker."
    assert snapshot.student_progress[0].risks[0].owner == "unknown"
    assert snapshot.student_progress[0].risks[0].mitigation == "unknown"
    assert snapshot.action_items[0].owner == "unknown"
    assert snapshot.action_items[0].deadline == "unknown"
    assert snapshot.action_items[0].student_name == "Alice"


def test_progress_extraction_accepts_string_fields_and_dict_payloads() -> None:
    client = StubDeepSeekClient(
        {
            "summary": "Bob reproduced the retrieval pipeline.",
            "student_progress": {
                "student_name": "Bob",
                "completed_work": "Reproduced the retrieval pipeline.",
                "current_result": "The core path runs end to end.",
                "blockers": "The citation parser still drops equations.",
                "risks": {
                    "title": "Parser regression",
                    "level": "warning",
                    "description": "Equation-heavy papers are parsed incorrectly.",
                    "owner": "",
                    "mitigation": "",
                },
                "unresolved_questions": "Why are equations lost in the parser output?",
                "next_step": "Fix the parser and record failure cases.",
                "action_items": {
                    "title": "Fix the citation parser",
                    "owner": "",
                    "deadline": "",
                    "priority": "urgent",
                    "status": "doing",
                    "dependency_note": "",
                },
            },
        }
    )
    service = ProgressExtractionService(client=client)

    snapshot = service.extract_progress(build_transcript(), meeting_id="meeting-123")

    assert snapshot.student_progress[0].student_name == "Bob"
    assert snapshot.student_progress[0].completed_work == ["Reproduced the retrieval pipeline."]
    assert snapshot.student_progress[0].blockers == ["The citation parser still drops equations."]
    assert snapshot.student_progress[0].risks[0].level == "medium"
    assert snapshot.action_items[0].priority == "high"
    assert snapshot.action_items[0].status == "in_progress"


def test_progress_extraction_requires_non_empty_transcript() -> None:
    service = ProgressExtractionService(client=StubDeepSeekClient({}))

    with pytest.raises(ProgressExtractionError):
        service.extract_progress(ParsedTranscript(meeting_id="meeting-123", chunks=[]), meeting_id="meeting-123")
