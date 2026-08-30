-- Справочный дамп схемы (версия 1). Источник истины — desktop_pet_gameshub/db/schema.py,
-- этот файл только для чтения человеком и не используется приложением напрямую.

CREATE TRIGGER trg_games_updated
AFTER UPDATE ON games
FOR EACH ROW BEGIN
  UPDATE games SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  UNIQUE(service_id, name),
  FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE developers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE game_developers (
  game_id INTEGER NOT NULL,
  developer_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, developer_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(developer_id) REFERENCES developers(id) ON DELETE CASCADE
);

CREATE TABLE game_genres (
  game_id INTEGER NOT NULL,
  genre_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, genre_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

CREATE TABLE game_platforms (
  game_id INTEGER NOT NULL,
  platform_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, platform_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(platform_id) REFERENCES platforms(id) ON DELETE CASCADE
);

CREATE TABLE game_publishers (
  game_id INTEGER NOT NULL,
  publisher_id INTEGER NOT NULL,
  PRIMARY KEY (game_id, publisher_id),
  FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
  FOREIGN KEY(publisher_id) REFERENCES publishers(id) ON DELETE CASCADE
);

CREATE TABLE games (
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

CREATE TABLE genres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE platforms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE publishers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE schema_meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  version INTEGER NOT NULL
);

CREATE TABLE services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE statuses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_games_account ON games(account_id);

CREATE INDEX idx_games_service ON games(service_id);

CREATE INDEX idx_games_status ON games(status_id);

CREATE INDEX idx_games_year ON games(year);

CREATE INDEX idx_gd_dev ON game_developers(developer_id);

CREATE INDEX idx_gd_game ON game_developers(game_id);

CREATE INDEX idx_gg_game ON game_genres(game_id);

CREATE INDEX idx_gg_gen ON game_genres(genre_id);

CREATE INDEX idx_gp_game ON game_publishers(game_id);

CREATE INDEX idx_gp_pub ON game_publishers(publisher_id);

CREATE INDEX idx_gpl_game ON game_platforms(game_id);

CREATE INDEX idx_gpl_plat ON game_platforms(platform_id);
