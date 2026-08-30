from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.services import http
from desktop_pet_gameshub.services.errors import NetworkError


def test_get_wraps_timeout_into_network_error() -> None:
    session = Mock()
    session.get.side_effect = requests.exceptions.Timeout("timed out")

    with pytest.raises(NetworkError):
        http.get(session, "https://example.invalid/page", NetworkConfig())


def test_get_passes_configured_timeout() -> None:
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    session.get.return_value = response
    network = NetworkConfig(timeout_seconds=3.5)

    result = http.get(session, "https://example.invalid/page", network)

    assert result is response
    session.get.assert_called_once_with("https://example.invalid/page", timeout=3.5)


def test_get_raises_on_http_error_status() -> None:
    session = Mock()
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    session.get.return_value = response

    with pytest.raises(NetworkError):
        http.get(session, "https://example.invalid/missing", NetworkConfig())
