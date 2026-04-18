from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from backend.config import Settings, get_settings


class OpenAlexAdapterError(RuntimeError):
    """Raised when OpenAlex search fails."""


class OpenAlexAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search_works(
        self,
        query: str,
        *,
        per_page: int = 5,
        timeout: float = 20.0
    ) -> list[dict[str, Any]]:
        params = {
            "search": query,
            "per-page": str(per_page)
        }
        if self.settings.openalex_email:
            params["mailto"] = self.settings.openalex_email

        endpoint = f"https://api.openalex.org/works?{parse.urlencode(params)}"

        try:
            with request.urlopen(endpoint, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OpenAlexAdapterError(
                f"OpenAlex request failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise OpenAlexAdapterError(f"OpenAlex request could not be completed: {exc.reason}") from exc

        results = payload.get("results", [])
        normalized: list[dict[str, Any]] = []
        for item in results:
            location = item.get("primary_location") or {}
            normalized.append(
                {
                    "id": item.get("id"),
                    "title": item.get("display_name"),
                    "source_url": location.get("landing_page_url") or location.get("pdf_url"),
                    "publication_year": item.get("publication_year"),
                    "authors": [
                        authorship.get("author", {}).get("display_name")
                        for authorship in item.get("authorships", [])
                        if authorship.get("author", {}).get("display_name")
                    ],
                    "raw": item
                }
            )

        return normalized

