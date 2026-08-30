"""Главное окно: галерея карточек, фильтры, поиск и точки входа в диалоги."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from desktop_pet_gameshub.config import AppConfig
from desktop_pet_gameshub.db.connection import get_connection
from desktop_pet_gameshub.db.repository import GameRepository
from desktop_pet_gameshub.models.game import GameFilter
from desktop_pet_gameshub.ui.async_runner import BackgroundRunner
from desktop_pet_gameshub.ui.clipboard import install_clipboard_support
from desktop_pet_gameshub.ui.dialogs.game_dialog import GameDialog
from desktop_pet_gameshub.ui.dialogs.multi_select import pick_multiple
from desktop_pet_gameshub.ui.dialogs.service_dialog import ServiceManagerDialog
from desktop_pet_gameshub.ui.dialogs.status_dialog import StatusManagerDialog
from desktop_pet_gameshub.ui.image_cache import ImageCache
from desktop_pet_gameshub.ui.widgets.game_card import GameCard

CARD_W = 180
CARD_H = 290
CARD_PAD_X = 12
CARD_PAD_Y = 12
COVER_MAX_W = 160
COVER_MAX_H = 200


class MainWindow(tk.Tk):
    """Корневое окно приложения. Владеет соединением БД для чтения в UI-потоке."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.title("Каталог игр — локальная база")
        self.geometry("1024x720")
        self.minsize(980, 640)

        self.config_ = config
        self.conn: sqlite3.Connection = get_connection(config.db_path)
        self.repo = GameRepository(self.conn)
        self.runner = BackgroundRunner(self)
        self.image_cache = ImageCache(config.network, max_w=COVER_MAX_W, max_h=COVER_MAX_H)

        install_clipboard_support(self)

        self.sort_by = tk.StringVar(value="title")
        self.filter_year = tk.StringVar()
        self.filter_status = tk.StringVar()
        self.filter_service = tk.StringVar()
        self.filter_account = tk.StringVar()
        self.selected_platform_ids: list[int] = []
        self.selected_developer_ids: list[int] = []
        self.selected_publisher_ids: list[int] = []

        self._selected_game_id: int | None = None
        self._cards_by_game: dict[int, GameCard] = {}

        self._build_top_bar()
        self._build_menu()
        self._build_gallery()

        self.lbl_count = ttk.Label(self, text="0 результат(ов)")
        self.lbl_count.pack(anchor="w", padx=12, pady=(0, 8))
        self.lbl_status = ttk.Label(self, text="", foreground="#555")
        self.lbl_status.pack(anchor="w", padx=12, pady=(0, 8))

        self.reload_ref_filters()
        self.reload_list()

        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- построение статичной части UI -----

    def _build_top_bar(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(top, text="Добавить игру", command=self.add_game).pack(side=tk.LEFT)
        ttk.Button(top, text="Редактировать", command=self.edit_selected).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(top, text="Сортировка:").pack(side=tk.LEFT)
        cmb_sort = ttk.Combobox(top, state="readonly", width=12, textvariable=self.sort_by, values=["title", "year"])
        cmb_sort.pack(side=tk.LEFT, padx=(4, 10))
        cmb_sort.bind("<<ComboboxSelected>>", lambda e: self.reload_list())

        ttk.Label(top, text="Год:").pack(side=tk.LEFT)
        ent_year = ttk.Entry(top, textvariable=self.filter_year, width=6)
        ent_year.pack(side=tk.LEFT, padx=(2, 8))
        ent_year.bind("<Return>", lambda e: self.reload_list())

        ttk.Label(top, text="Статус:").pack(side=tk.LEFT)
        self.cmb_status = ttk.Combobox(top, state="readonly", width=14, textvariable=self.filter_status)
        self.cmb_status.pack(side=tk.LEFT, padx=(2, 8))
        self.cmb_status.bind("<<ComboboxSelected>>", lambda e: self.reload_list())

        ttk.Label(top, text="Сервис:").pack(side=tk.LEFT)
        self.cmb_service = ttk.Combobox(top, state="readonly", width=14, textvariable=self.filter_service)
        self.cmb_service.pack(side=tk.LEFT, padx=(2, 8))
        self.cmb_service.bind("<<ComboboxSelected>>", self.on_filter_service)

        ttk.Label(top, text="Аккаунт:").pack(side=tk.LEFT)
        self.cmb_account = ttk.Combobox(top, state="readonly", width=16, textvariable=self.filter_account)
        self.cmb_account.pack(side=tk.LEFT, padx=(2, 8))
        self.cmb_account.bind("<<ComboboxSelected>>", lambda e: self.reload_list())

        ttk.Button(top, text="Платформы…", command=self.pick_platforms).pack(side=tk.LEFT, padx=(2, 4))
        ttk.Button(top, text="Разработчики…", command=self.pick_developers).pack(side=tk.LEFT, padx=(2, 4))
        ttk.Button(top, text="Издатели…", command=self.pick_publishers).pack(side=tk.LEFT, padx=(2, 10))
        ttk.Button(top, text="Сброс фильтров", command=self.reset_filters).pack(side=tk.LEFT)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        ref_menu = tk.Menu(menubar, tearoff=0)
        ref_menu.add_command(label="Управление сервисами и аккаунтами…", command=self.open_services)
        ref_menu.add_command(label="Управление статусами…", command=self.open_statuses)
        menubar.add_cascade(label="Справочники", menu=ref_menu)

    def _build_gallery(self) -> None:
        self.gallery_root = ttk.Frame(self)
        self.gallery_root.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(self.gallery_root, highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.gallery_root, orient="vertical", command=self.canvas.yview)
        scroll_x = ttk.Scrollbar(self.gallery_root, orient="horizontal", command=self.canvas.xview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.gallery_root.rowconfigure(0, weight=1)
        self.gallery_root.columnconfigure(0, weight=1)

    # ----- справочники и фильтры -----

    def reload_ref_filters(self) -> None:
        self.cmb_status["values"] = [""] + [s["name"] for s in self.repo.get_all("statuses")]
        self.cmb_service["values"] = [""] + [s["name"] for s in self.repo.get_all("services")]
        self.cmb_account["values"] = [""]

    def on_filter_service(self, _event: tk.Event | None = None) -> None:
        name = self.filter_service.get().strip()
        self.filter_account.set("")
        if not name:
            self.cmb_account["values"] = [""]
            self.reload_list()
            return
        service_id = self.repo.id_by_name("services", name)
        accounts = self.repo.accounts_for_service(service_id) if service_id else []
        self.cmb_account["values"] = [""] + [a["name"] for a in accounts]
        self.reload_list()

    def reset_filters(self) -> None:
        self.filter_year.set("")
        self.filter_status.set("")
        self.filter_service.set("")
        self.filter_account.set("")
        self.selected_platform_ids = []
        self.selected_developer_ids = []
        self.selected_publisher_ids = []
        self.reload_list()

    def pick_platforms(self) -> None:
        self.selected_platform_ids = self._pick_generic("Выбор платформ", "platforms", self.selected_platform_ids)
        self.reload_list()

    def pick_developers(self) -> None:
        self.selected_developer_ids = self._pick_generic("Выбор разработчиков", "developers", self.selected_developer_ids)
        self.reload_list()

    def pick_publishers(self) -> None:
        self.selected_publisher_ids = self._pick_generic("Выбор издателей", "publishers", self.selected_publisher_ids)
        self.reload_list()

    def _pick_generic(self, title: str, table: str, selected_ids: list[int]) -> list[int]:
        items = [(row["id"], row["name"]) for row in self.repo.get_all(table)]
        return pick_multiple(self, title, items, selected_ids)

    # ----- CRUD -----

    def add_game(self) -> None:
        GameDialog(self, self.config_, self.repo, self.runner, self.image_cache, on_saved=self.reload_list)

    def edit_selected(self) -> None:
        if not self._selected_game_id:
            messagebox.showinfo("Редактирование", "Сначала выберите игру, кликнув по карточке.")
            return
        GameDialog(
            self,
            self.config_,
            self.repo,
            self.runner,
            self.image_cache,
            on_saved=self.reload_list,
            game_id=self._selected_game_id,
        )

    def delete_selected(self) -> None:
        if not self._selected_game_id:
            messagebox.showinfo("Удаление", "Сначала выберите игру, кликнув по карточке.")
            return
        if not messagebox.askyesno("Подтвердите", "Удалить выбранную игру?", parent=self):
            return
        self.repo.delete_game(self._selected_game_id)
        self._selected_game_id = None
        self.reload_list()

    def open_services(self) -> None:
        ServiceManagerDialog(self, self.repo, on_changed=self._on_reference_data_changed)

    def open_statuses(self) -> None:
        StatusManagerDialog(self, self.repo, on_changed=self._on_reference_data_changed)

    def _on_reference_data_changed(self) -> None:
        self.reload_ref_filters()
        self.reload_list()

    # ----- список/галерея -----

    def reload_list(self) -> None:
        epoch = self.runner.new_epoch()

        game_filter = self._current_filter()
        if game_filter is None:
            return  # ошибка ввода уже показана пользователю

        self.lbl_status.configure(text="Загрузка списка игр…")

        def db_job():
            local_conn = get_connection(self.config_.db_path)
            try:
                return GameRepository(local_conn).fetch_game_list(game_filter)
            finally:
                local_conn.close()

        def on_success(result) -> None:
            rows, total_count = result
            self.lbl_status.configure(text="")
            for card in list(self._cards_by_game.values()):
                card.destroy()
            self._cards_by_game.clear()
            self._selected_game_id = None
            self.lbl_count.configure(text=f"{total_count} результат(ов)")
            self._render_rows_batched(rows, epoch)

        def on_error(exc: BaseException) -> None:
            self.lbl_status.configure(text=f"Не удалось загрузить список: {exc}")

        self.runner.submit(db_job, epoch=epoch, on_success=on_success, on_error=on_error)

    def _current_filter(self) -> GameFilter | None:
        year_text = self.filter_year.get().strip()
        year = None
        if year_text:
            if not year_text.isdigit():
                messagebox.showerror("Ошибка", "Фильтр по году — число.", parent=self)
                return None
            year = int(year_text)

        status_id = self.repo.id_by_name("statuses", self.filter_status.get().strip() or None)
        service_id = self.repo.id_by_name("services", self.filter_service.get().strip() or None)
        account_id = None
        if service_id and self.filter_account.get().strip():
            account_id = self.repo.account_id_by_service_and_name(service_id, self.filter_account.get().strip())

        return GameFilter(
            year=year,
            status_id=status_id,
            service_id=service_id,
            account_id=account_id,
            platform_ids=tuple(self.selected_platform_ids),
            developer_ids=tuple(self.selected_developer_ids),
            publisher_ids=tuple(self.selected_publisher_ids),
            sort_by=self.sort_by.get(),
        )

    def _render_rows_batched(
        self, rows: list[sqlite3.Row], epoch: int, batch_size: int = 48, start: int = 0
    ) -> None:
        if epoch != self.runner.current_epoch:
            return

        inner_w = max(self.inner.winfo_width(), self.winfo_width() - 60)
        cols = max(1, inner_w // (CARD_W + CARD_PAD_X))

        end = min(len(rows), start + batch_size)
        created = len(self._cards_by_game)
        r, c = divmod(created, cols)

        for i in range(start, end):
            row = rows[i]
            card = GameCard(
                self.inner,
                row,
                width=CARD_W,
                height=CARD_H,
                on_select=self._set_selected_game,
                on_open=self._open_game,
                cover_loader=lambda url, label, e=epoch: self._request_cover(url, label, e),
            )
            card.grid(row=r, column=c, padx=CARD_PAD_X // 2, pady=CARD_PAD_Y // 2, sticky="nw")
            self._cards_by_game[row["id"]] = card
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        if end < len(rows) and epoch == self.runner.current_epoch:
            self.after(0, lambda: self._render_rows_batched(rows, epoch, batch_size, end))

    def _request_cover(self, url: str, label: ttk.Label, epoch: int) -> None:
        def loaded(photo) -> None:
            if epoch != self.runner.current_epoch:
                return
            label.configure(image=photo, text="")
            label.image = photo

        def failed(_exc) -> None:
            if epoch != self.runner.current_epoch:
                return
            label.configure(text="(нет обложки)")

        self.image_cache.request(self.runner, url, epoch, loaded, failed)

    def _set_selected_game(self, game_id: int) -> None:
        if self._selected_game_id is not None:
            old = self._cards_by_game.get(self._selected_game_id)
            if old is not None:
                old.mark_selected(False)
        self._selected_game_id = game_id
        card = self._cards_by_game.get(game_id)
        if card is not None:
            card.mark_selected(True)

    def _open_game(self, game_id: int) -> None:
        self._set_selected_game(game_id)
        GameDialog(
            self, self.config_, self.repo, self.runner, self.image_cache, on_saved=self.reload_list, game_id=game_id
        )

    def _on_close(self) -> None:
        self.runner.shutdown()
        self.conn.close()
        self.destroy()
