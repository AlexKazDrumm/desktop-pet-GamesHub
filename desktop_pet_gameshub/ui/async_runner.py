"""Фоновые задачи с возвратом результата в поток Tkinter."""

from __future__ import annotations

import queue
import tkinter as tk
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any


class BackgroundRunner:
    def __init__(self, widget: tk.Misc, max_workers: int = 4) -> None:
        self._widget = widget
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: queue.Queue[tuple] = queue.Queue()
        self._epoch = 0

    def new_epoch(self) -> int:
        self._epoch += 1
        return self._epoch

    @property
    def current_epoch(self) -> int:
        return self._epoch

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        epoch: int | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
        **kwargs: Any,
    ) -> Future:
        def job() -> tuple:
            try:
                return (epoch, True, fn(*args, **kwargs))
            except BaseException as exc:  # noqa: BLE001 - доставляем любую ошибку в UI
                return (epoch, False, exc)

        future = self._executor.submit(job)

        def on_done(done_future: Future) -> None:
            self._results.put((done_future.result(), on_success, on_error))
            try:
                self._widget.after(0, self._drain)
            except tk.TclError:
                pass  # окно уже закрыто

        future.add_done_callback(on_done)
        return future

    def _drain(self) -> None:
        while True:
            try:
                (task_epoch, ok, payload), on_success, on_error = self._results.get_nowait()
            except queue.Empty:
                return
            if task_epoch is not None and task_epoch != self._epoch:
                continue
            if ok:
                if on_success is not None:
                    on_success(payload)
            elif on_error is not None:
                on_error(payload)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
