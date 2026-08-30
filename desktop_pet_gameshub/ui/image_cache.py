"""Загрузка и кеширование обложек."""

from __future__ import annotations

from io import BytesIO
from tkinter import PhotoImage

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:  # Pillow не обязателен: без него обложки просто не показываются
    PIL_AVAILABLE = False

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.services import images as image_service
from desktop_pet_gameshub.services.errors import NetworkError
from desktop_pet_gameshub.ui.async_runner import BackgroundRunner


class ImageCache:
    def __init__(self, network: NetworkConfig, max_w: int = 160, max_h: int = 200) -> None:
        self._network = network
        self._max_w = max_w
        self._max_h = max_h
        self._cache: dict[str, PhotoImage] = {}

    def get_cached(self, url: str) -> PhotoImage | None:
        return self._cache.get(url)

    def request(
        self,
        runner: BackgroundRunner,
        url: str,
        epoch: int,
        on_loaded: callable,
        on_failed: callable,
    ) -> None:
        if not PIL_AVAILABLE:
            on_failed(RuntimeError("Pillow не установлен"))
            return

        cached = self._cache.get(url)
        if cached is not None:
            on_loaded(cached)
            return

        def job() -> Image.Image:
            data = image_service.fetch_image_bytes(url, self._network)
            img = Image.open(BytesIO(data))
            img.load()
            img.thumbnail((self._max_w, self._max_h))
            return img

        def success(pil_image: Image.Image) -> None:
            photo = ImageTk.PhotoImage(pil_image)
            self._cache[url] = photo
            on_loaded(photo)

        def failure(exc: BaseException) -> None:
            if isinstance(exc, NetworkError):
                on_failed(exc)
            else:
                on_failed(exc)

        runner.submit(job, epoch=epoch, on_success=success, on_error=failure)
