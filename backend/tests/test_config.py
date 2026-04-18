from __future__ import annotations

from pathlib import Path

from backend.config import load_settings


def test_load_settings_reads_deepseek_key_from_dotenv() -> None:
    repo_root = Path("workspace-root")
    dotenv_path = Path(__file__).parent / "fixtures" / "deepseek.env"

    settings = load_settings(env={}, repo_root=repo_root, dotenv_path=dotenv_path)

    assert settings.deepseek_api_key == "test-deepseek-key"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.llm_provider == "deepseek"
    assert settings.llm_model == "deepseek-chat"


def test_load_settings_uses_local_storage_defaults() -> None:
    repo_root = Path("workspace-root")

    settings = load_settings(env={}, repo_root=repo_root, dotenv_path=Path("missing.env"))

    assert settings.data_dir == repo_root / "data" / "local_db"
    assert settings.sqlite_path == repo_root / "data" / "local_db" / "evidenceflow.sqlite3"
    assert settings.lancedb_path == repo_root / "data" / "local_db" / "lancedb"
    assert settings.embeddings_provider == "fastembed"
    assert settings.transcription_backend == "faster-whisper"
