from __future__ import annotations

import time
from pathlib import Path

import pytest

from backend.adapters.deepseek_client import DeepSeekClient
from backend.config import load_settings
from backend.schemas.claim import Claim
from backend.schemas.evidence_card import EvidenceCard
from backend.services.claim_extraction_service import ClaimExtractionService
from backend.services.claim_verification_service import ClaimVerificationService
from backend.services.transcript_parser_service import TranscriptParserService

LIVE_TRANSCRIPT = """
[00:00:05] Alice: This week I trained the baseline on 3k samples and reached 71 percent accuracy.
[00:00:18] Alice: The blocker is GPU memory. The 13B model runs out of memory at batch size four.
[00:00:31] Prof. Chen: Next week compare QLoRA with the smaller model and prepare a short result table by Friday.
[00:00:45] Bob: I reproduced the retrieval pipeline, but the citation parser still drops equations in long papers.
"""


def load_live_settings_or_skip():
    dotenv_path = Path.cwd() / ".env"
    if not dotenv_path.exists():
        pytest.skip("Repository .env file is required for the DeepSeek live tests.")

    settings = load_settings(env={}, repo_root=Path.cwd(), dotenv_path=dotenv_path)
    if not settings.deepseek_api_key:
        pytest.skip("DEEPSEEK_API_KEY is not configured.")
    return settings


def test_live_claim_extraction_with_deepseek() -> None:
    settings = load_live_settings_or_skip()
    transcript = TranscriptParserService().parse_transcript(
        LIVE_TRANSCRIPT,
        meeting_id="live-claim-extraction",
    )
    service = ClaimExtractionService(client=DeepSeekClient(settings))

    started_at = time.time()
    result = service.extract_claims(transcript, meeting_id="live-claim-extraction")
    elapsed_seconds = time.time() - started_at

    print(f"live_claim_extraction_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_claim_extraction_summary={result.summary}")
    print(f"live_claim_extraction_count={len(result.claims)}")
    print(f"live_claim_extraction_schema_ok={all(claim.text for claim in result.claims)}")

    assert result.summary
    assert result.claims
    assert any(claim.claim_kind in {"factual", "strategic"} for claim in result.claims)
    assert any(claim.speaker != "unknown" for claim in result.claims)


def test_live_claim_verification_with_deepseek() -> None:
    settings = load_live_settings_or_skip()
    claim = Claim(
        id="live-claim-verify-01",
        meeting_id="live-claim-verification",
        text="The baseline reached 71 percent accuracy on 3k samples.",
        speaker="Alice",
        claim_kind="factual",
        transcript_snippet="This week I trained the baseline on 3k samples and reached 71 percent accuracy.",
    )
    evidence_cards = [
        EvidenceCard(
            id="live-ev-001",
            claim_id="live-claim-verify-01",
            source_title="Meeting note excerpt",
            source_url="unknown",
            source_type="transcript",
            snippet="Alice reported that the baseline on 3k samples reached 71 percent accuracy.",
        ),
        EvidenceCard(
            id="live-ev-002",
            claim_id="live-claim-verify-01",
            source_title="Advisor follow-up",
            source_url="unknown",
            source_type="project_note",
            snippet="Prof. Chen asked for a QLoRA comparison next week, which assumes the 71 percent baseline is current.",
        ),
    ]
    service = ClaimVerificationService(client=DeepSeekClient(settings))

    started_at = time.time()
    result = service.verify_claim(claim, evidence_cards)
    elapsed_seconds = time.time() - started_at

    print(f"live_claim_verification_elapsed_seconds={elapsed_seconds:.2f}")
    print(f"live_claim_verification_summary={result.summary}")
    print(f"live_claim_verification_verdict={result.verdict}")
    print(f"live_claim_verification_schema_ok={all(card.reason for card in result.evidence_cards)}")

    assert result.summary
    assert result.verdict in {"supported", "contradicted", "needs_verification"}
    assert result.evidence_cards
    assert all(card.stance in {"support", "contradict", "needs_verification"} for card in result.evidence_cards)
    assert all(card.reason for card in result.evidence_cards)
