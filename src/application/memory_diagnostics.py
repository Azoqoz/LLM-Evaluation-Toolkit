"""Best-effort process RSS logging; never part of a public API response."""

import logging
import os


def log_rss(stage: str) -> None:
    if os.getenv("APP_MODE", "").strip().lower() != "demo":
        return
    try:
        import psutil

        rss = psutil.Process().memory_info().rss / 1024**2
        logging.getLogger("uvicorn.error").info("Evaluator RSS %s: %.1f MiB", stage, rss)
    except (ImportError, OSError):
        pass  # Diagnostics must never affect evaluation or readiness.
