"""Модальный выбор нескольких значений из справочника (платформы, разработчики, издатели)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def pick_multiple(
    parent: tk.Misc,
    title: str,
    items: list[tuple[int, str]],
    selected_ids: list[int],
) -> list[int]:
    """Показывает модальный список с множественным выбором и возвращает выбранные id."""

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("420x520")
    dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE)
    listbox.pack(fill=tk.BOTH, expand=True)
    for i, (item_id, name) in enumerate(items):
        listbox.insert(tk.END, f"{name} (id:{item_id})")
        if item_id in selected_ids:
            listbox.selection_set(i)

    result: list[int] = list(selected_ids)

    def confirm() -> None:
        nonlocal result
        result = [items[i][0] for i in listbox.curselection()]
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(buttons, text="OK", command=confirm).pack(side=tk.RIGHT)
    ttk.Button(buttons, text="Отмена", command=cancel).pack(side=tk.RIGHT, padx=5)

    dialog.wait_window()
    return result
