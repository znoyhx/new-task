from __future__ import annotations

import pytest

from backend.schemas.meeting import ParsedTranscript, TranscriptChunk
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot, StudentProgress
from backend.services.idea_capture_service import IdeaCaptureError, IdeaCaptureService
from backend.services.reading_recommendation_service import ReadingRecommendationService
from backend.services.research_plan_service import ResearchPlanError, ResearchPlanService


class StubDeepSeekClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def chat_json(self, prompt: str, **_: object) -> dict[str, object]:
        self.prompts.append(prompt)
        return self.payload


def build_transcript() -> ParsedTranscript:
    return ParsedTranscript(
        meeting_id="meeting-idea-plan",
        chunks=[
            TranscriptChunk(
                chunk_id="chunk-0001",
                speaker="Alice",
                timestamp_start="00:05",
                text="I trained the baseline model and reached 71 percent macro F1.",
            ),
            TranscriptChunk(
                chunk_id="chunk-0002",
                speaker="Prof. Chen",
                timestamp_start="00:24",
                text=(
                    "Next week test curriculum learning and add a hard-negative ablation. "
                    "Validate with macro F1 and calibration error. Also read the focal loss paper."
                ),
            ),
        ],
    )


def build_progress() -> MeetingProgressSnapshot:
    return MeetingProgressSnapshot(
        meeting_id="meeting-idea-plan",
        summary="Alice reported a baseline result and a data imbalance blocker.",
        student_progress=[
            StudentProgress(
                meeting_id="meeting-idea-plan",
                student_name="Alice",
                completed_work=["Trained the baseline model."],
                current_result="71 percent macro F1.",
                blockers=["The hard examples are still poorly classified."],
            )
        ],
    )


def build_ideas() -> list[ResearchIdea]:
    return [
        ResearchIdea(
            id="meeting-idea-plan-idea-01",
            meeting_id="meeting-idea-plan",
            student_name="Alice",
            idea_text="Test curriculum learning with hard-negative sampling.",
            suggested_by="Prof. Chen",
            expected_validation="Show macro F1 gain without hurting calibration.",
            validation_metrics=["macro F1", "calibration error"],
        )
    ]


def test_idea_capture_service_normalizes_nested_output() -> None:
    client = StubDeepSeekClient(
        {
            "summary": "Prof. Chen proposed one concrete experiment direction for Alice.",
            "ideas": [
                {
                    "student_name": "Alice",
                    "idea": "Try curriculum learning with a hard-negative ablation.",
                    "speaker": "Prof. Chen",
                    "validation_goal": "Improve macro F1 while keeping calibration stable.",
                    "validation_metrics": ["macro F1", "calibration error"],
                    "next_actions": [
                        {
                            "task": "Run the curriculum learning experiment",
                            "owner": "",
                            "priority": "urgent",
                            "reason": "It is the main hypothesis for next week.",
                        }
                    ],
                    "recommended_reading": [
                        {
                            "title": "Focal Loss for Dense Object Detection",
                            "source_url": "https://arxiv.org/abs/1708.02002",
                            "reason": "Useful for handling hard examples and imbalance.",
                            "priority": "high",
                        }
                    ],
                }
            ],
        }
    )
    service = IdeaCaptureService(client=client)

    result = service.capture_ideas(build_transcript())

    assert "validation_metrics" in client.prompts[0]
    assert result.summary == "Prof. Chen proposed one concrete experiment direction for Alice."
    assert len(result.ideas) == 1
    assert result.ideas[0].suggested_by == "Prof. Chen"
    assert result.ideas[0].next_actions[0].owner == "unknown"
    assert result.ideas[0].next_actions[0].priority == "high"
    assert result.ideas[0].recommended_reading[0].idea_id == result.ideas[0].id


def test_research_plan_service_backfills_success_metrics_from_idea() -> None:
    client = StubDeepSeekClient(
        {
            "summary": "Alice should focus on one validation experiment and one reporting task.",
            "tasks": [
                {
                    "idea_id": "meeting-idea-plan-idea-01",
                    "student_name": "",
                    "title": "Run the curriculum learning experiment on the full validation split",
                    "owner": "",
                    "deadline": "Friday",
                    "priority": "critical",
                    "dependency_note": "",
                    "rationale": "This directly validates the advisor's proposed direction.",
                }
            ],
            "questions_to_answer": ["Does curriculum learning improve macro F1 on hard examples?"],
        }
    )
    service = ResearchPlanService(client=client)

    result = service.generate_plan(
        build_transcript(),
        build_ideas(),
        progress=build_progress(),
    )

    assert "success_metrics" in client.prompts[0]
    assert result.summary == "Alice should focus on one validation experiment and one reporting task."
    assert result.tasks[0].student_name == "Alice"
    assert result.tasks[0].owner == "unknown"
    assert result.tasks[0].due_date == "Friday"
    assert result.tasks[0].priority == "high"
    assert result.tasks[0].success_metrics == ["macro F1", "calibration error"]
    assert result.questions_to_answer == ["Does curriculum learning improve macro F1 on hard examples?"]


def test_reading_recommendation_service_normalizes_single_dict_payload() -> None:
    client = StubDeepSeekClient(
        {
            "summary": "Alice mainly needs one paper about imbalance-aware training.",
            "recommended_reading": {
                "idea_id": "meeting-idea-plan-idea-01",
                "student_name": "",
                "title": "Curriculum Learning",
                "source_url": "",
                "reason": "It gives a direct recipe for ordering training examples by difficulty.",
                "priority": "urgent",
            },
        }
    )
    service = ReadingRecommendationService(client=client)

    result = service.generate_recommendations(
        build_transcript(),
        build_ideas(),
        progress=build_progress(),
    )

    assert "canonical source URLs" in client.prompts[0]
    assert result.summary == "Alice mainly needs one paper about imbalance-aware training."
    assert len(result.recommendations) == 1
    assert result.recommendations[0].student_name == "Alice"
    assert result.recommendations[0].source_url == "unknown"
    assert result.recommendations[0].priority == "high"


def test_idea_capture_requires_non_empty_transcript() -> None:
    service = IdeaCaptureService(client=StubDeepSeekClient({}))

    with pytest.raises(IdeaCaptureError):
        service.capture_ideas(ParsedTranscript(meeting_id="meeting-123", chunks=[]))


def test_research_plan_requires_at_least_one_idea() -> None:
    service = ResearchPlanService(client=StubDeepSeekClient({}))

    with pytest.raises(ResearchPlanError):
        service.generate_plan(build_transcript(), [], progress=build_progress())
