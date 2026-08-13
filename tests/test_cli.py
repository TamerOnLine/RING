from __future__ import annotations

from pathlib import Path

from rimg import cli


def test_main_defaults_to_web_command(monkeypatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_run_web(host: str, port: int) -> int:
        calls.append((host, port))
        return 0

    monkeypatch.setattr(cli, "run_web", fake_run_web)

    assert cli.main([]) == 0
    assert calls == [("127.0.0.1", 8501)]


def test_main_accepts_web_command_and_options(monkeypatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_run_web(host: str, port: int) -> int:
        calls.append((host, port))
        return 0

    monkeypatch.setattr(cli, "run_web", fake_run_web)

    assert cli.main(["web", "--host", "0.0.0.0", "--port", "8600"]) == 0
    assert calls == [("0.0.0.0", 8600)]


def test_run_web_launches_streamlit(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_call(command: list[str]) -> int:
        calls.append(command)
        return 0

    monkeypatch.setattr(cli.subprocess, "call", fake_call)

    assert cli.run_web("127.0.0.1", 8600) == 0
    command = calls[0]
    assert command[:3] == [cli.sys.executable, "-m", "streamlit"]
    assert command[3] == "run"
    assert Path(command[4]).name == "web.py"
    assert command[-4:] == ["--server.address", "127.0.0.1", "--server.port", "8600"]
