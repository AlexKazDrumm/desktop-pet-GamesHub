"""Загрузка карточки игры с mygamelist.club."""

from __future__ import annotations

import requests

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.models.game import MGLGameData
from desktop_pet_gameshub.services import http
from desktop_pet_gameshub.services.mgl_parser import MGL_BASE_URL, parse_html


def fetch_game(mgl_id: str, network: NetworkConfig, session: requests.Session | None = None) -> MGLGameData:
    own_session = session or http.build_session(network)
    url = MGL_BASE_URL + mgl_id.strip()
    response = http.get(own_session, url, network)
    return parse_html(response.text)
