"""Загрузка обложек по URL.

Возвращает сырые байты изображения — преобразование в объект Tkinter
(``PhotoImage``) выполняется в UI-слое, чтобы этот модуль оставался
тестируемым без Tkinter и без Pillow.
"""

from __future__ import annotations

import requests

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.services import http


def fetch_image_bytes(url: str, network: NetworkConfig, session: requests.Session | None = None) -> bytes:
    """Скачивает изображение по URL. Поднимает NetworkError при сбое."""

    own_session = session or http.build_session(network)
    response = http.get(own_session, url, network)
    return response.content
