"""Схема SQLite и миграции."""

from __future__ import annotations

import sqlite3

CURRENT_SCHEMA_VERSION = 1

_SCHEMA_META = """
CREATE TABLE IF NOT EXISTS schema_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  version INTEGER NOT NULL
);
"""

# Миграция 1: базовая структура каталога игр.
_MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  UNIQUE(service_id, name),
  FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS statuses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS developers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS publishers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS genres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS platforms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  year INTEGER,
  cover_url TEXT,
  service_id INTEGER,
  account_id INTEGER,
  status_id INTEGER,
  mgl_id TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE SET NULL,
  FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL,
  FOREIGN KEY(status_id) REFERENCES statuses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS game_developers (
  game_id INTEGER NOT NULL,
  developer_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, developer_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(developer_id) REFERENCES developers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_publishers (
  game_id INTEGER NOT NULL,
  publisher_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, publisher_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(publisher_id) REFERENCES publishers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_genres (
  game_id INTEGER NOT NULL,
  genre_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, genre_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_platforms (
  game_id INTEGER NOT NULL,
  platform_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, platform_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(platform_id) REFERENCES platforms(id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS trg_games_updated
AFTER UPDATE ON games
FOR EACH ROW BEGIN
  UPDATE games SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_games_year ON games(year);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status_id);
CREATE INDEX IF NOT EXISTS idx_games_service ON games(service_id);
CREATE INDEX IF NOT EXISTS idx_games_account ON games(account_id);
CREATE INDEX IF NOT EXISTS idx_gd_game ON game_developers(game_id);
CREATE INDEX IF NOT EXISTS idx_gd_dev ON game_developers(developer_id);
CREATE INDEX IF NOT EXISTS idx_gp_game ON game_publishers(game_id);
CREATE INDEX IF NOT EXISTS idx_gp_pub ON game_publishers(publisher_id);
CREATE INDEX IF NOT EXISTS idx_gg_game ON game_genres(game_id);
CREATE INDEX IF NOT EXISTS idx_gg_gen ON game_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_gpl_game ON game_platforms(game_id);
CREATE INDEX IF NOT EXISTS idx_gpl_plat ON game_platforms(platform_id);
"""

MIGRATIONS: dict[int, str] = {
    1: _MIGRATION_1,
}


def _get_current_version(conn: sqlite3.Connection) -> int:
    conn.executescript(_SCHEMA_META)
    row = conn.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()
    return row["version"] if row else 0


def ensure_schema(conn: sqlite3.Connection) -> int:
    """Применяет недостающие миграции и возвращает версию схемы."""

    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA foreign_keys = ON;")

    current = _get_current_version(conn)
    with conn:
        for version in sorted(MIGRATIONS):
            if version <= current:
                continue
            conn.executescript(MIGRATIONS[version])
            conn.execute(
                "INSERT INTO schema_meta(id, version) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET version = excluded.version",
                (version,),
            )
        current = _get_current_version(conn)
    return current
