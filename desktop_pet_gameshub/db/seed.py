"""Начальный набор игр для пустой базы."""

from __future__ import annotations

import json
import sqlite3
from importlib import resources
from typing import Any

from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.models.game import Game


def load_seed_payload() -> list[dict[str, Any]]:
    data_file = resources.files("desktop_pet_gameshub.data") / "seed_games.json"
    with data_file.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_demo_data(conn: sqlite3.Connection, *, skip_if_not_empty: bool = True) -> int:
    """Добавляет начальный набор и возвращает число новых записей."""

    repo = GameRepository(conn)

    if skip_if_not_empty:
        existing = conn.execute("SELECT COUNT(*) AS cnt FROM games").fetchone()["cnt"]
        if existing:
            return 0

    payload = load_seed_payload()
    for item in payload:
        game = Game(
            title=item["title"],
            year=item.get("year"),
            cover_url=item.get("cover_url"),
            status_id=repo.upsert_name("statuses", item["status"]) if item.get("status") else None,
            developers=item.get("developers", []),
            publishers=item.get("publishers", []),
            genres=item.get("genres", []),
            platforms=item.get("platforms", []),
        )
        repo.save_game(game)

    return len(payload)
