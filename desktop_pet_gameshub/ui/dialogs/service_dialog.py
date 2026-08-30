"""Управление сервисами и аккаунтами (например: Steam, GOG, Epic Games Store)."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from desktop_pet_gameshub.db.repository import GameRepository


class ServiceManagerDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, repo: GameRepository, on_changed: callable) -> None:
        super().__init__(master)
        self.title("Сервисы и аккаунты")
        self.repo = repo
        self.on_changed = on_changed
        self.geometry("700x440")
        self.transient(master)
        self.grab_set()

        self.services: list[sqlite3.Row] = []
        self.accounts: list[sqlite3.Row] = []
        self.selected_service_id: int | None = None

        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(frame)
        right = ttk.Frame(frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        ttk.Label(left, text="Сервисы").pack(anchor="w")
        self.lst_services = tk.Listbox(left, exportselection=False)
        self.lst_services.pack(fill=tk.BOTH, expand=True)
        btns_srv = ttk.Frame(left)
        btns_srv.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btns_srv, text="Добавить сервис", command=self.add_service).pack(side=tk.LEFT)
        ttk.Button(btns_srv, text="Удалить сервис", command=self.delete_service).pack(side=tk.LEFT, padx=5)

        ttk.Label(right, text="Аккаунты (для выбранного сервиса)").pack(anchor="w")
        self.lst_accounts = tk.Listbox(right, exportselection=False)
        self.lst_accounts.pack(fill=tk.BOTH, expand=True)
        btns_acc = ttk.Frame(right)
        btns_acc.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btns_acc, text="Добавить аккаунт", command=self.add_account).pack(side=tk.LEFT)
        ttk.Button(btns_acc, text="Удалить аккаунт", command=self.delete_account).pack(side=tk.LEFT, padx=5)

        self.lst_services.bind("<<ListboxSelect>>", self.on_select_service)

        self.reload_data()

    def reload_data(self) -> None:
        self.services = self.repo.get_all("services")
        self.lst_services.delete(0, tk.END)
        for s in self.services:
            self.lst_services.insert(tk.END, f"{s['name']} (id:{s['id']})")
        self.lst_accounts.delete(0, tk.END)
        self.selected_service_id = None
        self.on_changed()

    def on_select_service(self, _event: tk.Event | None = None) -> None:
        idx = self.lst_services.curselection()
        if not idx:
            self.selected_service_id = None
            self.lst_accounts.delete(0, tk.END)
            return
        service = self.services[idx[0]]
        self.selected_service_id = service["id"]
        self.accounts = self.repo.accounts_for_service(service["id"])
        self.lst_accounts.delete(0, tk.END)
        for a in self.accounts:
            self.lst_accounts.insert(tk.END, f"{a['name']} (id:{a['id']})")

    def add_service(self) -> None:
        name = simpledialog.askstring("Новый сервис", "Название сервиса:", parent=self)
        if not name:
            return
        try:
            self.repo.upsert_name("services", name)
            self.reload_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такой сервис уже существует.", parent=self)

    def delete_service(self) -> None:
        idx = self.lst_services.curselection()
        if not idx:
            return
        service = self.services[idx[0]]
        if not messagebox.askyesno(
            "Подтвердите", f"Удалить сервис «{service['name']}» и все его аккаунты?", parent=self
        ):
            return
        self.repo.delete_row("services", service["id"])
        self.reload_data()

    def add_account(self) -> None:
        if not self.selected_service_id:
            messagebox.showinfo("Внимание", "Сначала выберите сервис.", parent=self)
            return
        name = simpledialog.askstring("Новый аккаунт", "Название/логин аккаунта:", parent=self)
        if not name:
            return
        try:
            self.repo.add_account(self.selected_service_id, name)
            self.on_select_service()
            self.on_changed()
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Такой аккаунт уже существует у этого сервиса.", parent=self)

    def delete_account(self) -> None:
        idx = self.lst_accounts.curselection()
        if not idx:
            return
        account = self.accounts[idx[0]]
        if not messagebox.askyesno("Подтвердите", f"Удалить аккаунт «{account['name']}»?", parent=self):
            return
        self.repo.delete_row("accounts", account["id"])
        self.on_select_service()
        self.on_changed()
