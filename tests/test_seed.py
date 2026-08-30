from __future__ import annotations

import sqlite3

from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.db.seed import load_seed_payload, seed_demo_data


def test_seed_payload_has_no_personal_accounts() -> None:
    payload = load_seed_payload()
    assert len(payload) >= 10
    for item in payload:
        assert "account" not in item
        assert "service" not in item
        assert item["title"]


def test_seed_demo_data_populates_empty_db(conn: sqlite3.Connection) -> None:
    added = seed_demo_data(conn)
    payload = load_seed_payload()
    assert added == len(payload)

    total = conn.execute("SELECT COUNT(*) AS cnt FROM games").fetchone()["cnt"]
    assert total == len(payload)


def test_seed_demo_data_skips_when_not_empty(conn: sqlite3.Connection, repo: GameRepository) -> None:
    from desktop_pet_gameshub.models.game import Game

    repo.save_game(Game(title="Already here"))
    added = seed_demo_data(conn)
    assert added == 0
    total = conn.execute("SELECT COUNT(*) AS cnt FROM games").fetchone()["cnt"]
    assert total == 1
