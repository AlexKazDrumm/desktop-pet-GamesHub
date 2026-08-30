"""Запуск приложения и команды CLI."""

from __future__ import annotations

import argparse
import json
import sys
from tkinter import messagebox

from desktop_pet_gameshub.config import AppConfig
from desktop_pet_gameshub.services import mgl_client
from desktop_pet_gameshub.services.errors import NetworkError, ParseError


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="desktop-pet-GamesHub — локальный каталог игр (GUI + CLI-утилиты)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    test_mgl = sub.add_parser("test-mgl", help="Проверить разбор карточки игры на mygamelist.club (без записи в БД)")
    test_mgl.add_argument("mgl_id", help="Идентификатор игры на mygamelist.club")

    parser.add_argument("--seed-demo", action="store_true", help="Заполнить пустую БД демонстрационным набором игр")

    return parser


def cli_test_mgl(mgl_id: str, config: AppConfig) -> int:
    try:
        data = mgl_client.fetch_game(mgl_id, config.network)
    except (NetworkError, ParseError) as exc:
        sys.stderr.write(f"[error] {exc}\n")
        return 2

    payload = {
        "title": data.title,
        "year": data.year,
        "cover_url": data.cover_url,
        "developers": data.developers,
        "publishers": data.publishers,
        "genres": data.genres,
        "platforms": data.platforms,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cli_seed_demo(config: AppConfig) -> int:
    from desktop_pet_gameshub.db.connection import get_connection
    from desktop_pet_gameshub.db.seed import seed_demo_data

    conn = get_connection(config.db_path)
    try:
        added = seed_demo_data(conn)
    finally:
        conn.close()
    print(f"Добавлено игр: {added}" if added else "БД уже содержит данные, демо-набор не применён.")
    return 0


def run_gui(config: AppConfig) -> int:
    from desktop_pet_gameshub.ui.main_window import MainWindow

    window = MainWindow(config)
    window.mainloop()
    return 0


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    config = AppConfig()

    if getattr(args, "cmd", None) == "test-mgl":
        return cli_test_mgl(args.mgl_id, config)

    if getattr(args, "seed_demo", False):
        return cli_seed_demo(config)

    try:
        return run_gui(config)
    except Exception as exc:  # noqa: BLE001 - последний рубеж перед падением приложения
        try:
            messagebox.showerror("Fatal", str(exc))
        except Exception:
            sys.stderr.write(f"Fatal: {exc}\n")
        raise
