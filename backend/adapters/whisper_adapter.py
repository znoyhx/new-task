from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from backend.config import Settings, get_settings


class WhisperAdapter:
    _model_cache: dict[tuple[str, str, str, str], Any] = {}

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def transcribe_file(
        self,
        file_path: str | Path,
        *,
        language_hint: str | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        backend = self.settings.transcription_backend.strip().lower()
        if backend != "faster-whisper":
            raise NotImplementedError(
                f"Unsupported local transcription backend '{self.settings.transcription_backend}'. "
                "This build only supports 'faster-whisper'."
            )

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install it locally before importing audio meetings."
            ) from exc

        model_size = os.getenv("FASTER_WHISPER_MODEL_SIZE", os.getenv("WHISPER_MODEL_SIZE", "tiny"))
        device = os.getenv("FASTER_WHISPER_DEVICE", os.getenv("WHISPER_DEVICE", "cpu"))
        compute_type = os.getenv(
            "FASTER_WHISPER_COMPUTE_TYPE",
            os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        )
        cpu_threads = self._read_int_env("FASTER_WHISPER_CPU_THREADS", default=4)
        download_root = str(self.settings.data_dir / "models" / "faster-whisper")
        model_key = (backend, model_size, device, compute_type)
        model = self._model_cache.get(model_key)
        if model is None:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                cpu_threads=cpu_threads,
            )
            self._model_cache[model_key] = model

        beam_size = self._read_int_env("FASTER_WHISPER_BEAM_SIZE", default=1)
        vad_filter = os.getenv("FASTER_WHISPER_VAD_FILTER", "true").strip().lower() != "false"
        started_at = time.perf_counter()
        try:
            segments, info = model.transcribe(
                str(path),
                language=language_hint or None,
                beam_size=beam_size,
                vad_filter=vad_filter,
                condition_on_previous_text=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Local transcription failed for '{path.name}': {exc}") from exc

        text_parts: list[str] = []
        normalized_segments: list[dict[str, Any]] = []
        for index, segment in enumerate(segments, start=1):
            text = str(getattr(segment, "text", "")).strip()
            if not text:
                continue

            text_parts.append(text)
            normalized_segments.append(
                {
                    "id": index,
                    "text": text,
                    "start": getattr(segment, "start", None),
                    "end": getattr(segment, "end", None),
                    "avg_logprob": getattr(segment, "avg_logprob", None),
                    "no_speech_prob": getattr(segment, "no_speech_prob", None),
                }
            )

        warning_messages: list[str] = []
        if not normalized_segments:
            warning_messages.append("Local transcription returned no non-empty segments.")

        return {
            "backend": backend,
            "text": " ".join(text_parts).strip(),
            "segments": normalized_segments,
            "language": getattr(info, "language", None),
            "duration_seconds": getattr(info, "duration", None),
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
            "warnings": warning_messages,
            "model_size": model_size,
        }

    def _read_int_env(self, name: str, *, default: int) -> int:
        raw_value = os.getenv(name)
        if not raw_value:
            return default
        try:
            return int(raw_value)
        except ValueError:
            return default
