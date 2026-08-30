"""Пути и сетевые настройки приложения."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR_NAME = "desktop-pet-gameshub"
ENV_DB_PATH = "GAMESHUB_DB_PATH"


def default_data_dir() -> Path:
    """Возвращает каталог пользовательских данных."""

    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / f".{APP_DIR_NAME}"


def default_db_path() -> Path:
    """Возвращает путь из `GAMESHUB_DB_PATH` или стандартный путь."""

    override = os.environ.get(ENV_DB_PATH)
    if override:
        return Path(override)
    return default_data_dir() / "games.db"


@dataclass(frozen=True)
class NetworkConfig:
    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_factor: float = 0.5
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


@dataclass(frozen=True)
class AppConfig:
    db_path: Path = field(default_factory=default_db_path)
    network: NetworkConfig = field(default_factory=NetworkConfig)
