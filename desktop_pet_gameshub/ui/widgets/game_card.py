"""Карточка игры в галерее.

Виджет ничего не знает о сети и БД: обложку ему поставляет вызывающая
сторона через ``cover_loader`` — это держит карточку простой и легко
переиспользуемой.
"""

from __future__ import annotations

import sqlite3
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

CardClickHandler = Callable[[int], None]
CoverLoader = Callable[[str, "ttk.Label"], None]


class GameCard(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        row: sqlite3.Row,
        *,
        width: int,
        height: int,
        on_select: CardClickHandler,
        on_open: CardClickHandler,
        cover_loader: CoverLoader | None = None,
    ) -> None:
        super().__init__(parent, width=width, height=height, relief="ridge", padding=6)
        self.grid_propagate(False)
        self.game_id = int(row["id"])

        self.image_label = ttk.Label(self, text="(загрузка...)", anchor="center", width=22)
        self.image_label.grid(row=0, column=0, sticky="n", pady=(0, 6))

        title = row["title"] or ""
        year = row["year"]
        title_text = f"{title} ({year})" if year is not None else title
        ttk.Label(self, text=title_text, wraplength=width - 12, justify="center").grid(
            row=1, column=0, sticky="ew"
        )

        meta_lines = [v for v in (row["publishers"], row["developers"]) if v]
        ttk.Label(
            self,
            text="\n".join(meta_lines),
            wraplength=width - 12,
            justify="center",
            foreground="#555",
        ).grid(row=2, column=0, sticky="ew", pady=(4, 0))

        for widget in (self, self.image_label):
            widget.bind("<Button-1>", lambda _e: on_select(self.game_id))
            widget.bind("<Double-1>", lambda _e: on_open(self.game_id))

        cover_url = (row["cover_url"] or "").strip()
        if cover_url and cover_loader is not None:
            cover_loader(cover_url, self.image_label)
        else:
            self.image_label.configure(text="(нет обложки)")

    def mark_selected(self, selected: bool) -> None:
        self.configure(relief="solid" if selected else "ridge")
