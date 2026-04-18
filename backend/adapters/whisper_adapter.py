from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.config import Settings, get_settings


class WhisperAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def transcribe_file(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        raise NotImplementedError(
            f"Local transcription backend '{self.settings.transcription_backend}' will be implemented in Task 3."
        )

