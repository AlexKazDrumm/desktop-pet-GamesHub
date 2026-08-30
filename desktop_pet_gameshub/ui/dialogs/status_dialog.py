"""Управление статусами прохождения (например: пройдено, в процессе, в планах)."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from desktop_pet_gameshub.db.repository import GameRepository


class StatusManagerDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, repo: GameRepository, on_changed: callable) -> None:
        super().__init__(master)
        self.title("Статусы")
        self.repo = repo
        self.on_changed = on_changed
        self.geometry("400x320")
        self.transient(master)
        self.grab_set()

        self.statuses: list[sqlite3.Row] = []

        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Статусы").pack(anchor="w")
        self.listbox = tk.Listbox(frame)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text="Добавить статус", command=self.add_status).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Удалить статус", command=self.delete_status).pack(side=tk.LEFT, padx=5)

        self.reload()

    def reload(self) -> None:
        self.statuses = self.repo.get_all("statuses")
        self.listbox.delete(0, tk.END)
        for s in self.statuses:
            self.listbox.insert(tk.END, f"{s['name']} (id:{s['id']})")
        self.on_changed()

    def add_status(self) -> None:
        name = simpledialog.askstring("Новый статус", "Название статуса:", parent=self)
        if not name:
            return
        try:
            self.repo.upsert_name("statuses", name)
            self.reload()
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такой статус уже существует.", parent=self)

    def delete_status(self) -> None:
        idx = self.listbox.curselection()
        if not idx:
            return
        status = self.statuses[idx[0]]
        if not messagebox.askyesno("Подтвердите", f"Удалить статус «{status['name']}»?", parent=self):
            return
        self.repo.delete_row("statuses", status["id"])
        self.reload()
