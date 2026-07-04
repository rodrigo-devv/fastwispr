from __future__ import annotations

from pathlib import Path
import logging
import os

from .config import default_data_dir


def app_log_path() -> Path:
    return default_data_dir() / "fastwispr.log"


def configure_file_logging(*, force: bool = False) -> Path:
    path = app_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    logging.basicConfig(
        filename=str(path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        encoding="utf-8",
        force=force,
    )
    return path
