from __future__ import annotations

import logging

DEFAULT_LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
