"""Runtime mode configuration and rendering tests."""

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.config.settings import get_app_mode


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("local", "local"),
        ("demo", "demo"),
        ("LOCAL", "local"),
        ("Demo", "demo"),
        ("", "local"),
        ("invalid-value", "local"),
    ],
)
def test_app_mode_normalization(
    monkeypatch: pytest.MonkeyPatch, configured: str, expected: str
) -> None:
    monkeypatch.setenv("APP_MODE", configured)
    assert get_app_mode() == expected


def test_app_mode_defaults_to_local_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.setattr(st, "secrets", {})
    assert get_app_mode() == "local"


def test_environment_app_mode_takes_priority_over_streamlit_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_MODE", "local")
    monkeypatch.setattr(st, "secrets", {"APP_MODE": "demo"})
    assert get_app_mode() == "local"


def test_streamlit_secret_is_used_when_environment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.setattr(st, "secrets", {"APP_MODE": "Demo"})
    assert get_app_mode() == "demo"


def test_missing_streamlit_secret_defaults_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.setattr(st, "secrets", {})
    assert get_app_mode() == "local"


def test_invalid_streamlit_secret_defaults_to_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_MODE", raising=False)
    monkeypatch.setattr(st, "secrets", {"APP_MODE": "invalid-value"})
    assert get_app_mode() == "local"


@pytest.mark.parametrize(
    ("app_mode", "sidebar_badge", "content_badge", "description", "mode_detail"),
    [
        (
            "local",
            "FULL LOCAL MODE",
            "Full Local Mode · Offline evaluation",
            "Complete offline evaluation on your machine.",
            "Best for full-size datasets and private evaluation",
        ),
        (
            "demo",
            "DEMO MODE",
            "Demo Mode · Hosted evaluation",
            "Hosted version for quick testing.",
            "Run locally for private data and larger workloads",
        ),
    ],
)
def test_both_app_modes_render(
    monkeypatch: pytest.MonkeyPatch,
    app_mode: str,
    sidebar_badge: str,
    content_badge: str,
    description: str,
    mode_detail: str,
) -> None:
    monkeypatch.setenv("APP_MODE", app_mode)
    app = AppTest.from_file("app.py").run()

    assert not app.exception
    markup = " ".join(element.value for element in app.markdown)
    assert "LLM Evaluation Toolkit" in markup
    assert sidebar_badge in markup
    assert content_badge in markup
    assert description in markup
    assert mode_detail in markup
    assert set(app.radio[0].options) == {
        "Single Evaluation",
        "Batch Evaluation",
    }

    app.radio[0].set_value("Batch Evaluation").run()
    assert not app.exception
    batch_markup = " ".join(element.value for element in app.markdown)
    assert content_badge in batch_markup
