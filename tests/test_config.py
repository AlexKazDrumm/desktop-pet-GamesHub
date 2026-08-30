from __future__ import annotations

from pathlib import Path

from desktop_pet_gameshub.config import ENV_DB_PATH, default_db_path


def test_default_db_path_respects_env_override(monkeypatch) -> None:
    monkeypatch.setenv(ENV_DB_PATH, "/tmp/custom-games.db")
    assert default_db_path() == Path("/tmp/custom-games.db")


def test_default_db_path_uses_local_appdata_on_windows(monkeypatch) -> None:
    monkeypatch.delenv(ENV_DB_PATH, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/test/AppData/Local")
    path = default_db_path()
    assert "desktop-pet-gameshub" in str(path)
    assert path.name == "games.db"
