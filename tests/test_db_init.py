from __future__ import annotations

import sqlite3

import pytest

from desktop_pet_gameshub.db.connection import get_connection
from desktop_pet_gameshub.db.schema import CURRENT_SCHEMA_VERSION, ensure_schema


def test_ensure_schema_creates_all_tables(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        "services", "accounts", "statuses", "developers", "publishers", "genres",
        "platforms", "games", "game_developers", "game_publishers", "game_genres",
        "game_platforms", "schema_meta",
    }
    assert expected.issubset(tables)


def test_ensure_schema_sets_current_version(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()
    assert row["version"] == CURRENT_SCHEMA_VERSION


def test_ensure_schema_is_idempotent(conn: sqlite3.Connection) -> None:
    # Повторный вызов не должен ни падать, ни менять версию схемы.
    version_before = ensure_schema(conn)
    version_after = ensure_schema(conn)
    assert version_before == version_after == CURRENT_SCHEMA_VERSION


def test_new_database_starts_empty(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS cnt FROM games").fetchone()["cnt"]
    assert count == 0


def test_get_connection_creates_file_from_scratch(tmp_path) -> None:
    db_path = tmp_path / "nested" / "games.db"
    assert not db_path.exists()

    connection = get_connection(db_path)
    try:
        version = connection.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()["version"]
        assert version == CURRENT_SCHEMA_VERSION
    finally:
        connection.close()

    assert db_path.exists()


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            # service_id = 999 не существует в services — вставка должна быть отклонена.
            conn.execute("INSERT INTO games(title, service_id) VALUES ('X', 999)")
