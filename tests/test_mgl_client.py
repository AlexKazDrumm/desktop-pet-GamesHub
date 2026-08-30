from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from desktop_pet_gameshub.config import NetworkConfig
from desktop_pet_gameshub.services import mgl_client
from desktop_pet_gameshub.services.errors import NetworkError

SAMPLE_HTML = """
<html><body><main><h1>Mocked Game</h1></main></body></html>
"""


def test_fetch_game_parses_response_without_real_network() -> None:
    fake_response = Mock(text=SAMPLE_HTML)
    with patch.object(mgl_client.http, "get", return_value=fake_response) as mocked_get:
        data = mgl_client.fetch_game("abc123", NetworkConfig(), session=Mock())

    assert data.title == "Mocked Game"
    called_url = mocked_get.call_args[0][1]
    assert called_url.endswith("abc123")


def test_fetch_game_propagates_network_error() -> None:
    with patch.object(mgl_client.http, "get", side_effect=NetworkError("boom")):
        with pytest.raises(NetworkError):
            mgl_client.fetch_game("abc123", NetworkConfig(), session=Mock())
