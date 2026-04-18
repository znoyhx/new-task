from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

DEFAULT_DATA_DIR = Path("data") / "local_db"
DEFAULT_SQLITE_FILENAME = "evidenceflow.sqlite3"
DEFAULT_LANCEDB_DIRNAME = "lancedb"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_PROVIDER = "deepseek"
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_EMBEDDINGS_PROVIDER = "fastembed"
DEFAULT_TRANSCRIPTION_BACKEND = "faster-whisper"


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    app_env: str
    log_level: str
    data_dir: Path
    sqlite_path: Path
    lancedb_path: Path
    llm_provider: str
    llm_model: str
    deepseek_api_key: str | None
    deepseek_base_url: str
    embeddings_provider: str
    transcription_backend: str
    openalex_email: str | None


def _parse_dotenv(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()

        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        values[key] = value

    return values


def _resolve_path(raw_value: str, repo_root: Path) -> Path:
    candidate = Path(raw_value)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _get_value(name: str, env: Mapping[str, str], dotenv_values: Mapping[str, str], default: str | None = None) -> str | None:
    if name in env:
        return env[name]
    if name in dotenv_values:
        return dotenv_values[name]
    return default


def load_settings(
    env: Mapping[str, str] | None = None,
    *,
    repo_root: Path | None = None,
    dotenv_path: Path | None = None
) -> Settings:
    resolved_repo_root = repo_root or Path(__file__).resolve().parent.parent
    resolved_dotenv_path = dotenv_path or resolved_repo_root / ".env"
    env_values = dict(os.environ if env is None else env)
    dotenv_values = _parse_dotenv(resolved_dotenv_path)

    data_dir_value = _get_value("DATA_DIR", env_values, dotenv_values)
    data_dir = (
        _resolve_path(data_dir_value, resolved_repo_root)
        if data_dir_value
        else resolved_repo_root / DEFAULT_DATA_DIR
    )

    sqlite_path_value = _get_value("SQLITE_PATH", env_values, dotenv_values)
    sqlite_path = (
        _resolve_path(sqlite_path_value, resolved_repo_root)
        if sqlite_path_value
        else data_dir / DEFAULT_SQLITE_FILENAME
    )

    lancedb_path_value = _get_value("LANCEDB_PATH", env_values, dotenv_values)
    lancedb_path = (
        _resolve_path(lancedb_path_value, resolved_repo_root)
        if lancedb_path_value
        else data_dir / DEFAULT_LANCEDB_DIRNAME
    )

    return Settings(
        repo_root=resolved_repo_root,
        app_env=_get_value("APP_ENV", env_values, dotenv_values, "development") or "development",
        log_level=_get_value("LOG_LEVEL", env_values, dotenv_values, "INFO") or "INFO",
        data_dir=data_dir,
        sqlite_path=sqlite_path,
        lancedb_path=lancedb_path,
        llm_provider=_get_value("LLM_PROVIDER", env_values, dotenv_values, DEFAULT_LLM_PROVIDER)
        or DEFAULT_LLM_PROVIDER,
        llm_model=_get_value("LLM_MODEL", env_values, dotenv_values, DEFAULT_LLM_MODEL)
        or DEFAULT_LLM_MODEL,
        deepseek_api_key=_get_value("DEEPSEEK_API_KEY", env_values, dotenv_values),
        deepseek_base_url=_get_value(
            "DEEPSEEK_BASE_URL",
            env_values,
            dotenv_values,
            DEFAULT_DEEPSEEK_BASE_URL
        )
        or DEFAULT_DEEPSEEK_BASE_URL,
        embeddings_provider=_get_value(
            "EMBEDDINGS_PROVIDER",
            env_values,
            dotenv_values,
            DEFAULT_EMBEDDINGS_PROVIDER
        )
        or DEFAULT_EMBEDDINGS_PROVIDER,
        transcription_backend=_get_value(
            "TRANSCRIPTION_BACKEND",
            env_values,
            dotenv_values,
            DEFAULT_TRANSCRIPTION_BACKEND
        )
        or DEFAULT_TRANSCRIPTION_BACKEND,
        openalex_email=_get_value("OPENALEX_EMAIL", env_values, dotenv_values)
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()

