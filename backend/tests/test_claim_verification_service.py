from __future__ import annotations

import pytest

from backend.schemas.claim import Claim
from backend.schemas.evidence_card import EvidenceCard
from backend.schemas.meeting import ParsedTranscript, TranscriptChunk
from backend.services.claim_extraction_service import (
    ClaimExtractionError,
    ClaimExtractionService,
)
from backend.services.claim_verification_service import ClaimVerificationService
from backend.services.evidence_retrieval_service import EvidenceRetrievalService


class StubChatJsonClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def chat_json(self, prompt: str, **_: object) -> dict[str, object]:
        self.prompts.append(prompt)
        return self.payload


class StubOpenAlexClient:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = results
        self.queries: list[str] = []

    def search_works(self, query: str, **_: object) -> list[dict[str, object]]:
        self.queries.append(query)
        return self.results


def build_transcript() -> ParsedTranscript:
    return ParsedTranscript(
        meeting_id="meeting-claim-001",
        chunks=[
            TranscriptChunk(
                chunk_id="chunk-0001",
                speaker="Alice",
                timestamp_start="00:05",
                text="The baseline reached 71 percent accuracy on 3k samples.",
            ),
            TranscriptChunk(
                chunk_id="chunk-0002",
                speaker="Prof. Chen",
                timestamp_start="00:20",
                text="Next week compare QLoRA with the smaller model before Friday.",
            ),
            TranscriptChunk(
                chunk_id="chunk-0003",
                speaker="Bob",
                timestamp_start="00:35",
                text="I am still debugging the parser.",
            ),
        ],
    )


def test_claim_extraction_normalizes_high_value_claims_and_links_source_chunks() -> None:
    client = StubChatJsonClient(
        {
            "summary": "Two claims matter for follow-up.",
            "claims": [
                {
                    "text": "The baseline reached 71 percent accuracy on 3k samples.",
                    "speaker": "Alice",
                    "timestamp_start": "00:05",
                    "transcript_snippet": "The baseline reached 71 percent accuracy on 3k samples.",
                    "claim_kind": "factual",
                    "confidence": "strong",
                },
                {
                    "text": "Compare QLoRA with the smaller model before Friday.",
                    "speaker": "Prof. Chen",
                    "timestamp_start": "00:20",
                    "claim_kind": "strategy",
                    "confidence": "tentative",
                },
            ],
        }
    )
    service = ClaimExtractionService(client=client)

    result = service.extract_claims(build_transcript(), meeting_id="meeting-claim-001")

    assert "highest-value claims" in client.prompts[0]
    assert result.summary == "Two claims matter for follow-up."
    assert len(result.claims) == 2
    assert result.claims[0].source_chunk_ids == ["chunk-0001"]
    assert result.claims[0].confidence == "high"
    assert result.claims[1].claim_kind == "strategic"
    assert result.claims[1].confidence == "low"
    assert result.claims[1].source_chunk_ids == ["chunk-0002"]


def test_claim_extraction_requires_non_empty_transcript() -> None:
    service = ClaimExtractionService(client=StubChatJsonClient({}))

    with pytest.raises(ClaimExtractionError):
        service.extract_claims(ParsedTranscript(meeting_id="meeting-claim-001", chunks=[]))


def test_evidence_retrieval_maps_openalex_results_to_evidence_cards() -> None:
    claim = Claim(
        id="claim-001",
        meeting_id="meeting-claim-001",
        text="Curriculum learning improves macro F1 on hard examples.",
        speaker="Prof. Chen",
    )
    search_client = StubOpenAlexClient(
        [
            {
                "id": "https://openalex.org/W123",
                "title": "Curriculum Learning for Robust Classification",
                "source_url": "https://example.org/paper",
                "publication_year": 2024,
                "authors": ["Ada Lovelace", "Grace Hopper"],
                "raw": {
                    "abstract_inverted_index": {
                        "Curriculum": [0],
                        "learning": [1],
                        "improves": [2],
                        "robustness": [3],
                    },
                    "relevance_score": 0.91,
                },
            }
        ]
    )
    service = EvidenceRetrievalService(search_client=search_client)

    result = service.retrieve_evidence(claim, max_results=3)

    assert search_client.queries == ["Curriculum learning improves macro F1 on hard examples."]
    assert result.claim_id == "claim-001"
    assert len(result.evidence_cards) == 1
    evidence = result.evidence_cards[0]
    assert evidence.claim_id == "claim-001"
    assert evidence.source_title == "Curriculum Learning for Robust Classification"
    assert evidence.stance == "needs_verification"
    assert evidence.snippet.startswith("Curriculum learning improves robustness")
    assert evidence.score == 0.91


@pytest.mark.parametrize(
    ("raw_verdict", "expected_verdict"),
    [
        ("support", "supported"),
        ("contradict", "contradicted"),
        ("mixed", "needs_verification"),
    ],
)
def test_claim_verification_classifies_supported_contradicted_and_needs_verification(
    raw_verdict: str,
    expected_verdict: str,
) -> None:
    claim = Claim(
        id="claim-001",
        meeting_id="meeting-claim-001",
        text="The baseline reached 71 percent accuracy on 3k samples.",
        speaker="Alice",
    )
    evidence_cards = [
        EvidenceCard(
            id="ev-001",
            claim_id="claim-001",
            source_title="Experiment note",
            source_url="unknown",
            source_type="project_note",
            snippet="The baseline reached 71 percent accuracy on 3k samples.",
        )
    ]
    client = StubChatJsonClient(
        {
            "summary": "Verification complete.",
            "verdict": raw_verdict,
            "confidence": "strong",
            "evidence_assessments": [
                {
                    "evidence_id": "ev-001",
                    "stance": raw_verdict,
                    "reason": "The snippet directly addresses the claim.",
                    "confidence": "strong",
                }
            ],
        }
    )
    service = ClaimVerificationService(client=client)

    result = service.verify_claim(claim, evidence_cards)

    assert "Verify the claim against the evidence cards." in client.prompts[0]
    assert result.verdict == expected_verdict
    assert result.claim.verification_status == expected_verdict
    assert result.confidence == "high"
    if expected_verdict == "supported":
        assert result.evidence_cards[0].stance == "support"
    elif expected_verdict == "contradicted":
        assert result.evidence_cards[0].stance == "contradict"
    else:
        assert result.evidence_cards[0].stance == "needs_verification"


def test_claim_verification_returns_needs_verification_without_evidence() -> None:
    claim = Claim(
        id="claim-002",
        meeting_id="meeting-claim-001",
        text="We already reproduced the larger model result.",
        speaker="Alice",
    )
    client = StubChatJsonClient({})
    service = ClaimVerificationService(client=client)

    result = service.verify_claim(claim, [])

    assert client.prompts == []
    assert result.verdict == "needs_verification"
    assert result.evidence_cards == []
    assert result.gaps
