from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from rimg import __version__
from rimg.config import load_config
from rimg.logging import configure_logging

logger = logging.getLogger(__name__)

WEB_COMMANDS = {"run", "serve", "web"}


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    config = load_config()
    parser = argparse.ArgumentParser(description="Rimg batch image processing tools.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=sorted(WEB_COMMANDS),
        help="Command to run. Defaults to launching the web interface.",
    )
    parser.add_argument("--host", default=config.host, help="Host address for Streamlit.")
    parser.add_argument("--port", type=int, default=config.port, help="Port for Streamlit.")
    parser.add_argument("--version", action="version", version=f"rimg {__version__}")
    args = parser.parse_args(argv)

    if args.command is None or args.command in WEB_COMMANDS:
        return run_web(args.host, args.port)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def run_web(host: str, port: int) -> int:
    web_app = Path(__file__).with_name("web.py")

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(web_app),
        "--server.address",
        host,
        "--server.port",
        str(port),
    ]
    logger.info("Starting Rimg web interface on %s:%s", host, port)
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        logger.info("Rimg web interface stopped")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
