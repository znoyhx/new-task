from __future__ import annotations

from typing import Literal

ResponseLanguage = Literal["zh", "en"]


def resolve_response_language(output_language: str | None) -> ResponseLanguage:
    return "zh" if str(output_language or "").strip().lower() == "zh" else "en"


def is_chinese(output_language: str | None) -> bool:
    return resolve_response_language(output_language) == "zh"


def localize_text(output_language: str | None, *, zh: str, en: str) -> str:
    return zh if is_chinese(output_language) else en


def build_json_output_language_instruction(output_language: str | None) -> str:
    if is_chinese(output_language):
        return (
            "Write every free-text field value in Simplified Chinese. "
            "Keep JSON keys, enum values, ids, and URLs unchanged."
        )
    return (
        "Write every free-text field value in English. "
        "Keep JSON keys, enum values, ids, and URLs unchanged."
    )
