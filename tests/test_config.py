import pytest

from rimg.config import DEFAULT_HOST, DEFAULT_PORT, load_config


def test_load_config_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RIMG_HOST", "0.0.0.0")
    monkeypatch.setenv("RIMG_PORT", "8600")

    config = load_config()

    assert config.host == "0.0.0.0"
    assert config.port == 8600


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RIMG_HOST", raising=False)
    monkeypatch.delenv("RIMG_PORT", raising=False)

    config = load_config()

    assert config.host == DEFAULT_HOST
    assert config.port == DEFAULT_PORT
