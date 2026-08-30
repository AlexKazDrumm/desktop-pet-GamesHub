"""HTTP-клиент для внешних источников."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.services.errors import NetworkError


def build_session(network: NetworkConfig) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=network.max_retries,
        backoff_factor=network.backoff_factor,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": network.user_agent})
    return session


def get(session: requests.Session, url: str, network: NetworkConfig) -> requests.Response:
    try:
        response = session.get(url, timeout=network.timeout_seconds)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        raise NetworkError(f"Не удалось получить {url}: {exc}") from exc
