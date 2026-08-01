"""Central settings for the evaluator and user interface."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "LLM Evaluation Toolkit"
EVALUATION_MODE = "Offline Hybrid"
EVALUATOR_VERSION = "1.3.0"
DEFAULT_PASS_THRESHOLD = 70
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
APP_MODE_ENV_VAR = "APP_MODE"


def _get_streamlit_app_mode() -> object | None:
    """Read APP_MODE from Streamlit secrets without requiring a secrets file."""

    try:
        import streamlit as st

        return st.secrets[APP_MODE_ENV_VAR]
    except Exception:
        return None


def get_app_mode() -> Literal["local", "demo"]:
    """Return the configured runtime mode, defaulting safely to local."""

    configured = os.getenv(APP_MODE_ENV_VAR)
    if configured is None:
        configured = _get_streamlit_app_mode()
    normalized = str(configured or "").strip().lower()
    return "demo" if normalized == "demo" else "local"

REQUIRED_COLUMNS = ("question", "answer")
OPTIONAL_COLUMNS = ("expected_answer", "context", "id")
INPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

METRIC_WEIGHTS = {
    "correctness_score": 0.35,
    "relevance_score": 0.25,
    "groundedness_score": 0.25,
    "completeness_score": 0.15,
}

EXPORT_COLUMNS = (
    "relevance_score",
    "correctness_score",
    "groundedness_score",
    "completeness_score",
    "quality_score",
    "status",
    "error_type",
    "improvement_feedback",
    "evaluation_mode",
    "evaluated_at",
    "evaluator_version",
)

ERROR_TYPES = (
    "No Error",
    "Empty Answer",
    "Irrelevant Answer",
    "Incorrect Answer",
    "Incomplete Answer",
    "Unsupported Answer",
    "Contradictory Answer",
    "Overly Verbose",
    "Unwanted Refusal",
    "Formatting Issue",
    "Insufficient Data",
)
