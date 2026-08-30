"""Подключение к SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from desktop_pet_gameshub.db.schema import ensure_schema


def get_connection(db_path: Path, *, initialize: bool = True) -> sqlite3.Connection:
    """Открывает базу и при необходимости применяет миграции."""

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")

    if initialize:
        ensure_schema(conn)

    return conn
