from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend.adapters.deepseek_client import DeepSeekClient
from backend.config import load_settings
from backend.schemas.research_idea import ResearchIdea
from backend.schemas.student_progress import MeetingProgressSnapshot, StudentProgress
from backend.services.idea_capture_service import IdeaCaptureService
from backend.services.reading_recommendation_service import ReadingRecommendationService
from backend.services.research_plan_service import ResearchPlanService
from backend.services.transcript_parser_service import TranscriptParserService

LIVE_TRANSCRIPT = """
[00:00:05] Alice: This week I trained the baseline classifier and reached 71 percent macro F1 on the validation split.
[00:00:18] Alice: The blocker is that hard examples are still misclassified, and calibration gets worse after aggressive reweighting.
[00:00:31] Prof. Chen: Next week test curriculum learning with a hard-negative ablation. Validate the change with macro F1 and calibration error.
[00:00:45] Prof. Chen: Start by reading one paper on curriculum learning and one paper on imbalance-aware losses. Prepare a short comparison table by Friday.
[00:00:58] Bob: I fixed the data export script, but I am not part of Alice's experiment thread.
"""


def load_live_settings_or_skip():
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        pytest.skip("Repository .env file is required for the DeepSeek live tests.")

    settings = load_settings(env={}, repo_root=Path.cwd(), dotenv_path=dotenv_path)
    if not settings.deepseek_api_key:
        pytest.skip("DEEPSEEK_API_KEY is not configured.")
    return settings


def build_live_transcript():
    return TranscriptParserService().parse_transcript(
        LIVE_TRANSCRIPT,
        meeting_id="live-task-5",
    )


def build_live_progress() -> MeetingProgressSnapshot:
    return MeetingProgressSnapshot(
        meeting_id="live-task-5",
        summary="Alice has a strong baseline but still struggles with hard examples and calibration.",
        student_progress=[
            StudentProgress(
                meeting_id="live-task-5",
                student_name="Alice",
                completed_work=["Trained the baseline classifier."],
                current_result="71 percent macro F1 on validation.",
                blockers=[
                    "Hard examples are still misclassified.",
                    "Calibration worsens after aggressive reweighting.",
                ],
            )
        ],
    )


def build_live_ideas() -> list[ResearchIdea]:
    return [
        ResearchIdea(
            id="live-task-5-idea-01",
            meeting_id="live-task-5",
            student_name="Alice",
            idea_text="Test curriculum learning with a hard-negative ablation.",
            suggested_by="Prof. Chen",
            expected_validation="Improve macro F1 on hard examples without hurting calibration.",
            validation_metrics=["macro F1", "calibration error"],
        )
    ]


def test_live_advisor_idea_capture_with_deepseek() -> None:
    settings = load_live_settings_or_skip()
    service = IdeaCaptureService(client=DeepSeekClient(settings))

    started_at = time.time()
    result = service.capture_ideas(build_live_transcript(), meeting_id="live-task-5")
    elapsed_seconds = time.time() - started_at

    print(f"live_idea_capture_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_idea_capture_summary={result.summary}")
    print(f"live_idea_capture_count={len(result.ideas)}")

    assert result.summary
    assert result.ideas
    assert any(idea.idea_text for idea in result.ideas)
    assert any(idea.validation_metrics or idea.next_actions for idea in result.ideas)


def test_live_next_week_research_plan_with_deepseek() -> None:
    settings = load_live_settings_or_skip()
    service = ResearchPlanService(client=DeepSeekClient(settings))

    started_at = time.time()
    result = service.generate_plan(
        build_live_transcript(),
        build_live_ideas(),
        progress=build_live_progress(),
        meeting_id="live-task-5",
    )
    elapsed_seconds = time.time() - started_at

    print(f"live_research_plan_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_research_plan_summary={result.summary}")
    print(f"live_research_plan_task_count={len(result.tasks)}")

    assert result.summary
    assert result.tasks
    assert any(task.success_metrics for task in result.tasks)
    assert all(task.title for task in result.tasks)
    assert all(task.owner for task in result.tasks)


def test_live_reading_recommendations_with_deepseek() -> None:
    settings = load_live_settings_or_skip()
    service = ReadingRecommendationService(client=DeepSeekClient(settings))

    started_at = time.time()
    result = service.generate_recommendations(
        build_live_transcript(),
        build_live_ideas(),
        progress=build_live_progress(),
        meeting_id="live-task-5",
    )
    elapsed_seconds = time.time() - started_at

    print(f"live_reading_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_reading_summary={result.summary}")
    print(f"live_reading_count={len(result.recommendations)}")

    assert result.summary
    assert result.recommendations
    assert all(item.title for item in result.recommendations)
    assert all(item.reason for item in result.recommendations)
    assert all(item.priority in {"low", "medium", "high"} for item in result.recommendations)
