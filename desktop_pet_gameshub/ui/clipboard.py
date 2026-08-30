"""Поддержка копирования/вставки через контекстное меню и стандартные сочетания клавиш.

В некоторых сборках Tkinter под Windows системная вставка кириллицы в поля
ввода работает нестабильно — это явно связывает горячие клавиши и
контекстное меню с событиями ``<<Cut>>/<<Copy>>/<<Paste>>``.
"""

from __future__ import annotations

import tkinter as tk


def install_clipboard_support(root: tk.Tk) -> None:
    popup = tk.Menu(root, tearoff=0)
    popup.add_command(label="Вырезать", command=lambda: _generate(root.focus_get(), "<<Cut>>"))
    popup.add_command(label="Копировать", command=lambda: _generate(root.focus_get(), "<<Copy>>"))
    popup.add_command(label="Вставить", command=lambda: _generate(root.focus_get(), "<<Paste>>"))
    popup.add_separator()
    popup.add_command(label="Выделить всё", command=lambda: _generate(root.focus_get(), "<<SelectAll>>"))

    def show_popup(event: tk.Event) -> None:
        try:
            event.widget.focus_set()
            popup.tk_popup(event.x_root, event.y_root, 0)
        finally:
            popup.grab_release()

    for seq in ("<Control-v>", "<Control-V>", "<Control-KeyPress-v>", "<Shift-Insert>"):
        root.bind_all(seq, lambda e: _generate(root.focus_get(), "<<Paste>>"), add="+")
    for seq in ("<Control-c>", "<Control-C>", "<Control-KeyPress-c>"):
        root.bind_all(seq, lambda e: _generate(root.focus_get(), "<<Copy>>"), add="+")
    for seq in ("<Control-x>", "<Control-X>", "<Control-KeyPress-x>"):
        root.bind_all(seq, lambda e: _generate(root.focus_get(), "<<Cut>>"), add="+")
    for seq in ("<Control-a>", "<Control-A>", "<Control-KeyPress-a>"):
        root.bind_all(seq, lambda e: _generate(root.focus_get(), "<<SelectAll>>"), add="+")

    for cls in ("Entry", "Text", "TEntry", "TCombobox"):
        root.bind_class(cls, "<Button-3>", show_popup)
        root.bind_class(cls, "<ButtonRelease-3>", lambda e: "break")


def _generate(widget: tk.Misc | None, sequence: str) -> str:
    if widget is not None:
        widget.event_generate(sequence)
    return "break"
