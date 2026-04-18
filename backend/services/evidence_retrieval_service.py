from __future__ import annotations

from typing import Any, Protocol

from backend.adapters.openalex_adapter import OpenAlexAdapter
from backend.schemas.claim import Claim
from backend.schemas.evidence_card import EvidenceCard, EvidenceRetrievalResult


class SearchWorksClient(Protocol):
    def search_works(
        self,
        query: str,
        *,
        per_page: int = 5,
        timeout: float = 20.0,
    ) -> list[dict[str, Any]]:
        ...


class EvidenceRetrievalError(RuntimeError):
    """Raised when evidence retrieval cannot complete."""


class EvidenceRetrievalService:
    def __init__(self, search_client: SearchWorksClient | None = None) -> None:
        self.search_client = search_client or OpenAlexAdapter()

    def retrieve_evidence(
        self,
        claim: Claim,
        *,
        max_results: int = 5,
    ) -> EvidenceRetrievalResult:
        claim_text = claim.text.strip()
        if not claim_text:
            raise EvidenceRetrievalError("Claim text is required for evidence retrieval.")

        query = self._build_query(claim)
        works = self.search_client.search_works(query, per_page=max_results, timeout=20.0)
        evidence_cards = [
            self._map_work_to_evidence_card(work, claim=claim, index=index)
            for index, work in enumerate(works, start=1)
        ]

        return EvidenceRetrievalResult(
            claim_id=claim.id,
            query=query,
            evidence_cards=evidence_cards,
        )

    def _build_query(self, claim: Claim) -> str:
        return " ".join(claim.text.split())

    def _map_work_to_evidence_card(
        self,
        work: dict[str, Any],
        *,
        claim: Claim,
        index: int,
    ) -> EvidenceCard:
        raw = work.get("raw") if isinstance(work.get("raw"), dict) else {}
        title = self._clean_text(work.get("title"), default="Untitled result")
        source_url = self._clean_text(work.get("source_url"), default="unknown")
        publication_year = work.get("publication_year")
        authors = self._coerce_authors(work.get("authors"))
        snippet = self._extract_snippet(raw, title=title, publication_year=publication_year, authors=authors)
        evidence_id = self._clean_text(
            work.get("id"),
            default=f"{claim.id or claim.meeting_id or 'claim'}-evidence-{index:02d}",
        )

        return EvidenceCard(
            id=evidence_id,
            claim_id=claim.id,
            source_title=title,
            source_url=source_url,
            source_type="paper",
            stance="needs_verification",
            snippet=snippet,
            score=raw.get("relevance_score") or 0.0,
            reason="Retrieved from OpenAlex for claim review.",
            authors=authors,
            publication_year=publication_year,
        )

    def _extract_snippet(
        self,
        raw: dict[str, Any],
        *,
        title: str,
        publication_year: object,
        authors: list[str],
    ) -> str:
        abstract_inverted_index = raw.get("abstract_inverted_index")
        if isinstance(abstract_inverted_index, dict) and abstract_inverted_index:
            reconstructed = self._reconstruct_abstract(abstract_inverted_index)
            if reconstructed:
                return reconstructed[:320]

        author_text = ", ".join(authors[:3]) if authors else "unknown authors"
        year_text = str(publication_year).strip() if publication_year else "unknown year"
        return f"{title} ({year_text}) by {author_text}"

    def _reconstruct_abstract(self, abstract_inverted_index: dict[str, Any]) -> str:
        positioned_tokens: list[tuple[int, str]] = []
        for token, positions in abstract_inverted_index.items():
            if not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int):
                    positioned_tokens.append((position, token))

        if not positioned_tokens:
            return ""

        positioned_tokens.sort(key=lambda item: item[0])
        return " ".join(token for _, token in positioned_tokens)

    def _coerce_authors(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            authors: list[str] = []
            for entry in value:
                text = str(entry).strip()
                if text:
                    authors.append(text)
            return authors
        text = str(value).strip()
        return [text] if text else []

    def _clean_text(self, value: object, *, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default
