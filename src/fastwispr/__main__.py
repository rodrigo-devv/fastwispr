from __future__ import annotations

import logging

from fastwispr.cli import main
from fastwispr.logging_setup import configure_file_logging


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        configure_file_logging()
        logging.getLogger("fastwispr.__main__").exception("FastWispr crashed")
        raise
