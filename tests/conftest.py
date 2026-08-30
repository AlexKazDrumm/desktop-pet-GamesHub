from __future__ import annotations

import sqlite3

import pytest

from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.db.schema import ensure_schema


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Соединение с БД в памяти со свежеприменённой схемой."""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    ensure_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def repo(conn: sqlite3.Connection) -> GameRepository:
    return GameRepository(conn)
