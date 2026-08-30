"""Добавление и редактирование игры, включая автозаполнение с mygamelist.club."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from desktop_pet_gameshub.config import AppConfig
from desktop_pet_gameshub.db.connection import get_connection
from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.models.game import Game
from desktop_pet_gameshub.services import mgl_client
from desktop_pet_gameshub.services.errors import NetworkError
from desktop_pet_gameshub.ui.async_runner import BackgroundRunner
from desktop_pet_gameshub.ui.image_cache import ImageCache


class GameDialog(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        config: AppConfig,
        repo: GameRepository,
        runner: BackgroundRunner,
        image_cache: ImageCache,
        on_saved: callable,
        game_id: int | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Добавить / редактировать игру")
        self.config_ = config
        self.repo = repo
        self.runner = runner
        self.image_cache = image_cache
        self.on_saved = on_saved
        self.game_id = game_id
        self.geometry("760x620")
        self.transient(master)
        self.grab_set()

        self.var_title = tk.StringVar()
        self.var_year = tk.StringVar()
        self.var_cover = tk.StringVar()
        self.var_mgl_id = tk.StringVar()
        self.var_service = tk.StringVar()
        self.var_account = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_developers = tk.StringVar()
        self.var_publishers = tk.StringVar()
        self.var_genres = tk.StringVar()
        self.var_platforms = tk.StringVar()

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top, text="MGL ID:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.var_mgl_id, width=40).pack(side=tk.LEFT, padx=6)
        self.btn_autofill = ttk.Button(top, text="Определить", command=self.autofill_from_mgl)
        self.btn_autofill.pack(side=tk.LEFT)
        self.lbl_autofill_status = ttk.Label(top, text="", foreground="#555")
        self.lbl_autofill_status.pack(side=tk.LEFT, padx=8)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self._labeled_entry(left, "Название", self.var_title)
        self._labeled_entry(left, "Год", self.var_year)
        self._labeled_entry(left, "Обложка (URL)", self.var_cover)
        self._labeled_entry(left, "Разработчики (через запятую)", self.var_developers)
        self._labeled_entry(left, "Издатели (через запятую)", self.var_publishers)

        self._labeled_entry(right, "Жанры (через запятую)", self.var_genres)
        self._labeled_entry(right, "Платформы (через запятую)", self.var_platforms)

        sel = ttk.Frame(right)
        sel.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(sel, text="Сервис").grid(row=0, column=0, sticky="w")
        ttk.Label(sel, text="Аккаунт").grid(row=1, column=0, sticky="w")
        ttk.Label(sel, text="Статус").grid(row=2, column=0, sticky="w")

        self.cmb_service = ttk.Combobox(sel, textvariable=self.var_service, state="readonly", width=30)
        self.cmb_account = ttk.Combobox(sel, textvariable=self.var_account, state="readonly", width=30)
        self.cmb_status = ttk.Combobox(sel, textvariable=self.var_status, state="readonly", width=30)
        self.cmb_service.grid(row=0, column=1, sticky="we", padx=(8, 0), pady=2)
        self.cmb_account.grid(row=1, column=1, sticky="we", padx=(8, 0), pady=2)
        self.cmb_status.grid(row=2, column=1, sticky="we", padx=(8, 0), pady=2)
        sel.grid_columnconfigure(1, weight=1)
        self.cmb_service.bind("<<ComboboxSelected>>", self.reload_accounts_for_service)

        prev = ttk.Frame(right)
        prev.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(prev, text="Превью обложки:").pack(anchor="w")
        self.cover_preview = ttk.Label(prev, text="(нет обложки)")
        self.cover_preview.pack(fill=tk.X)
        self.var_cover.trace_add("write", lambda *_: self.load_cover_preview())

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.btn_save = ttk.Button(bottom, text="Сохранить", command=self.save)
        self.btn_save.pack(side=tk.RIGHT)
        ttk.Button(bottom, text="Отмена", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.lbl_save_status = ttk.Label(bottom, text="", foreground="#555")
        self.lbl_save_status.pack(side=tk.LEFT)

        self.reload_ref_data()
        if self.game_id:
            self.load_game(self.game_id)

    def _labeled_entry(self, parent: tk.Misc, label: str, var: tk.StringVar) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=3)
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Entry(frame, textvariable=var).pack(fill=tk.X)

    def reload_ref_data(self) -> None:
        self.cmb_service["values"] = [s["name"] for s in self.repo.get_all("services")]
        self.cmb_status["values"] = [s["name"] for s in self.repo.get_all("statuses")]
        self.reload_accounts_for_service()

    def reload_accounts_for_service(self, _event: tk.Event | None = None) -> None:
        self.cmb_account.set("")
        service_id = self.repo.id_by_name("services", self.var_service.get().strip())
        if not service_id:
            self.cmb_account["values"] = []
            return
        accounts = self.repo.accounts_for_service(service_id)
        self.cmb_account["values"] = [a["name"] for a in accounts]

    def load_cover_preview(self) -> None:
        url = self.var_cover.get().strip()
        if not url:
            self.cover_preview.configure(image="", text="(нет обложки)")
            return
        cached = self.image_cache.get_cached(url)
        if cached is not None:
            self.cover_preview.configure(image=cached, text="")
            self.cover_preview.image = cached
            return
        self.cover_preview.configure(image="", text="(загрузка обложки...)")
        epoch = self.runner.current_epoch

        def loaded(photo):
            if url != self.var_cover.get().strip():
                return
            self.cover_preview.configure(image=photo, text="")
            self.cover_preview.image = photo

        def failed(_exc):
            if url != self.var_cover.get().strip():
                return
            self.cover_preview.configure(image="", text="(не удалось загрузить)")

        self.image_cache.request(self.runner, url, epoch, loaded, failed)

    def autofill_from_mgl(self) -> None:
        mgl_id = self.var_mgl_id.get().strip()
        if not mgl_id:
            messagebox.showinfo("MGL", "Введите MGL ID.", parent=self)
            return

        self.btn_autofill.state(["disabled"])
        self.lbl_autofill_status.configure(text="Загрузка данных с mygamelist.club…")

        def apply_result(data) -> None:
            self.btn_autofill.state(["!disabled"])
            self.lbl_autofill_status.configure(text="Готово")
            if data.title:
                self.var_title.set(data.title)
            if data.year:
                self.var_year.set(str(data.year))
            if data.cover_url:
                self.var_cover.set(data.cover_url)
            if data.developers:
                self.var_developers.set(", ".join(data.developers))
            if data.publishers:
                self.var_publishers.set(", ".join(data.publishers))
            if data.genres:
                self.var_genres.set(", ".join(data.genres))
            if data.platforms:
                self.var_platforms.set(", ".join(data.platforms))

        def apply_error(exc: BaseException) -> None:
            self.btn_autofill.state(["!disabled"])
            if isinstance(exc, NetworkError):
                self.lbl_autofill_status.configure(text=f"Ошибка сети: {exc}")
            else:
                self.lbl_autofill_status.configure(text=f"Не удалось разобрать страницу: {exc}")

        self.runner.submit(
            mgl_client.fetch_game,
            mgl_id,
            self.config_.network,
            on_success=apply_result,
            on_error=apply_error,
        )

    def load_game(self, game_id: int) -> None:
        row = self.repo.get_game(game_id)
        if not row:
            return
        self.var_title.set(row["title"] or "")
        self.var_year.set("" if row["year"] is None else str(row["year"]))
        self.var_cover.set(row["cover_url"] or "")
        self.var_mgl_id.set(row["mgl_id"] or "")

        service_name = self.repo.name_by_id("services", row["service_id"])
        if service_name:
            self.var_service.set(service_name)
            self.reload_accounts_for_service()
        account_name = self.repo.name_by_id("accounts", row["account_id"])
        if account_name:
            self.var_account.set(account_name)
        status_name = self.repo.name_by_id("statuses", row["status_id"])
        if status_name:
            self.var_status.set(status_name)

        self.var_developers.set(", ".join(self.repo.names_for_game("developers", game_id)))
        self.var_publishers.set(", ".join(self.repo.names_for_game("publishers", game_id)))
        self.var_genres.set(", ".join(self.repo.names_for_game("genres", game_id)))
        self.var_platforms.set(", ".join(self.repo.names_for_game("platforms", game_id)))
        self.load_cover_preview()

    def _split_csv(self, value: str) -> list[str]:
        return [x.strip() for x in value.split(",") if x.strip()]

    def save(self) -> None:
        title = self.var_title.get().strip()
        if not title:
            messagebox.showerror("Ошибка", "Название обязательно.", parent=self)
            return

        year_text = self.var_year.get().strip()
        if year_text and not year_text.isdigit():
            messagebox.showerror("Ошибка", "Год должен быть числом.", parent=self)
            return

        service_id = self.repo.id_by_name("services", self.var_service.get())
        account_id = None
        if service_id and self.var_account.get():
            account_id = self.repo.account_id_by_service_and_name(service_id, self.var_account.get())

        game = Game(
            id=self.game_id,
            title=title,
            year=int(year_text) if year_text else None,
            cover_url=self.var_cover.get().strip() or None,
            mgl_id=self.var_mgl_id.get().strip() or None,
            service_id=service_id,
            account_id=account_id,
            status_id=self.repo.id_by_name("statuses", self.var_status.get()),
            developers=self._split_csv(self.var_developers.get()),
            publishers=self._split_csv(self.var_publishers.get()),
            genres=self._split_csv(self.var_genres.get()),
            platforms=self._split_csv(self.var_platforms.get()),
        )

        self.btn_save.state(["disabled"])
        self.lbl_save_status.configure(text="Сохранение…")

        def write_job() -> None:
            # Отдельное соединение: запись выполняется в фоновом потоке.
            conn = get_connection(self.config_.db_path)
            try:
                GameRepository(conn).save_game(game)
            finally:
                conn.close()

        def on_success(_result) -> None:
            self.on_saved()
            self.destroy()

        def on_error(exc: BaseException) -> None:
            self.btn_save.state(["!disabled"])
            self.lbl_save_status.configure(text=f"Не удалось сохранить: {exc}")

        self.runner.submit(write_job, on_success=on_success, on_error=on_error)
