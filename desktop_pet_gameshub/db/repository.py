"""Запросы к базе каталога игр."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from desktop_pet_gameshub.models.game import Game, GameFilter

_LINK_TABLES = {
    "developers": ("game_developers", "developer_id"),
    "publishers": ("game_publishers", "publisher_id"),
    "genres": ("game_genres", "genre_id"),
    "platforms": ("game_platforms", "platform_id"),
}


class GameRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _upsert_name_nocommit(self, table: str, name: str) -> int:
        name = name.strip()
        cur = self._conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = self._conn.execute(f"INSERT INTO {table}(name) VALUES (?)", (name,))
        return cur.lastrowid

    def upsert_name(self, table: str, name: str) -> int:
        with self._conn:
            return self._upsert_name_nocommit(table, name)

    def get_all(self, table: str) -> list[sqlite3.Row]:
        return list(self._conn.execute(f"SELECT * FROM {table} ORDER BY name"))

    def id_by_name(self, table: str, name: str | None) -> int | None:
        if not name:
            return None
        cur = self._conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
        row = cur.fetchone()
        return row["id"] if row else None

    def name_by_id(self, table: str, row_id: int | None) -> str | None:
        if not row_id:
            return None
        row = self._conn.execute(f"SELECT name FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return row["name"] if row else None

    def account_id_by_service_and_name(self, service_id: int, name: str) -> int | None:
        row = self._conn.execute(
            "SELECT id FROM accounts WHERE service_id = ? AND name = ?", (service_id, name)
        ).fetchone()
        return row["id"] if row else None

    def names_for_game(self, table: str, game_id: int) -> list[str]:
        link_table, fk = _LINK_TABLES[table]
        sql = (
            f"SELECT t.name FROM {link_table} lt "
            f"JOIN {table} t ON t.id = lt.{fk} "
            f"WHERE lt.game_id = ? ORDER BY t.name"
        )
        return [row["name"] for row in self._conn.execute(sql, (game_id,))]

    def accounts_for_service(self, service_id: int) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                "SELECT * FROM accounts WHERE service_id = ? ORDER BY name", (service_id,)
            )
        )

    def add_account(self, service_id: int, name: str) -> int:
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO accounts(service_id, name) VALUES (?,?)", (service_id, name.strip())
            )
            return cur.lastrowid

    def delete_row(self, table: str, row_id: int) -> None:
        with self._conn:
            self._conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))

    def link_many(self, game_id: int, table: str, names: Iterable[str]) -> None:
        link_table, fk = _LINK_TABLES[table]
        self._conn.execute(f"DELETE FROM {link_table} WHERE game_id = ?", (game_id,))
        for raw_name in names:
            name = raw_name.strip()
            if not name:
                continue
            obj_id = self._upsert_name_nocommit(table, name)
            self._conn.execute(
                f"INSERT OR IGNORE INTO {link_table}(game_id, {fk}) VALUES (?,?)",
                (game_id, obj_id),
            )

    def get_game(self, game_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM games WHERE id = ?", (game_id,)
        ).fetchone()

    def save_game(self, game: Game) -> int:
        """Создаёт или обновляет игру вместе со связями. Возвращает id."""

        with self._conn:
            if game.id:
                self._conn.execute(
                    """
                    UPDATE games
                    SET title=?, year=?, cover_url=?, service_id=?,
                        account_id=?, status_id=?, mgl_id=?
                    WHERE id = ?
                    """,
                    (
                        game.title,
                        game.year,
                        game.cover_url,
                        game.service_id,
                        game.account_id,
                        game.status_id,
                        game.mgl_id,
                        game.id,
                    ),
                )
                game_id = game.id
            else:
                cur = self._conn.execute(
                    """
                    INSERT INTO games(title, year, cover_url, service_id, account_id, status_id, mgl_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        game.title,
                        game.year,
                        game.cover_url,
                        game.service_id,
                        game.account_id,
                        game.status_id,
                        game.mgl_id,
                    ),
                )
                game_id = cur.lastrowid

            self.link_many(game_id, "developers", game.developers)
            self.link_many(game_id, "publishers", game.publishers)
            self.link_many(game_id, "genres", game.genres)
            self.link_many(game_id, "platforms", game.platforms)

        return game_id

    def delete_game(self, game_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM games WHERE id = ?", (game_id,))

    def fetch_game_list(
        self, game_filter: GameFilter | None = None
    ) -> tuple[list[sqlite3.Row], int]:
        """Возвращает отфильтрованный и отсортированный список игр + общее число."""

        f = game_filter or GameFilter()
        where: list[str] = []
        params: list[object] = []

        if f.year is not None:
            where.append("g.year = ?")
            params.append(f.year)
        if f.status_id:
            where.append("g.status_id = ?")
            params.append(f.status_id)
        if f.service_id:
            where.append("g.service_id = ?")
            params.append(f.service_id)
        if f.account_id:
            where.append("g.account_id = ?")
            params.append(f.account_id)

        for ids, column, link_table in (
            (f.platform_ids, "platform_id", "game_platforms"),
            (f.developer_ids, "developer_id", "game_developers"),
            (f.publisher_ids, "publisher_id", "game_publishers"),
        ):
            if ids:
                placeholders = ",".join("?" * len(ids))
                where.append(
                    f"g.id IN (SELECT game_id FROM {link_table} WHERE {column} IN ({placeholders}))"
                )
                params.extend(ids)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        order_sql = "g.title COLLATE NOCASE ASC"
        if f.sort_by == "year":
            order_sql = "COALESCE(g.year, 9999) ASC, g.title COLLATE NOCASE ASC"

        total_count = self._conn.execute(
            f"SELECT COUNT(*) AS cnt FROM games g {where_sql}", params
        ).fetchone()["cnt"]

        sql = f"""
        WITH devs AS (
          SELECT gd.game_id, GROUP_CONCAT(d.name, ', ') AS developers
          FROM game_developers gd JOIN developers d ON d.id = gd.developer_id
          GROUP BY gd.game_id
        ),
        pubs AS (
          SELECT gp.game_id, GROUP_CONCAT(p.name, ', ') AS publishers
          FROM game_publishers gp JOIN publishers p ON p.id = gp.publisher_id
          GROUP BY gp.game_id
        )
        SELECT g.*, devs.developers, pubs.publishers
        FROM games g
        LEFT JOIN devs ON devs.game_id = g.id
        LEFT JOIN pubs ON pubs.game_id = g.id
        {where_sql}
        ORDER BY {order_sql};
        """
        rows = list(self._conn.execute(sql, params))
        return rows, total_count
