"""Dark-theme configuration and fallback-style tests."""

import tomllib
from pathlib import Path

from src.ui.styles import APP_CSS


def test_all_streamlit_theme_presets_use_the_same_dark_palette() -> None:
    config_path = Path(__file__).parents[1] / ".streamlit" / "config.toml"
    with config_path.open("rb") as config_file:
        theme = tomllib.load(config_file)["theme"]

    assert theme["base"] == "dark"
    expected = {
        "primaryColor": "#1F9D8B",
        "backgroundColor": "#090D12",
        "secondaryBackgroundColor": "#151A23",
        "textColor": "#F2F5F4",
    }
    for preset in (theme, theme["light"], theme["dark"]):
        assert {key: preset[key] for key in expected} == expected

    expected_sidebar = {
        "backgroundColor": "#0E131A",
        "secondaryBackgroundColor": "#171C25",
        "textColor": "#F2F5F4",
    }
    for sidebar in (
        theme["sidebar"],
        theme["light"]["sidebar"],
        theme["dark"]["sidebar"],
    ):
        assert {
            key: sidebar[key] for key in expected_sidebar
        } == expected_sidebar


def test_dark_widget_fallbacks_cover_theme_sensitive_surfaces() -> None:
    for selector in (
        '[data-baseweb="textarea"]',
        '[data-baseweb="input"]',
        '[data-testid="stFileUploaderDropzone"]',
        '[data-testid="stDataFrame"]',
        '[data-testid="stVegaLiteChart"]',
    ):
        assert selector in APP_CSS
    assert "color-scheme: dark" in APP_CSS


def test_neutral_surfaces_keep_teal_as_an_accent_only() -> None:
    assert "background-color: #252631" in APP_CSS
    assert "background: #10151d" in APP_CSS
    assert "background: rgba(14, 19, 26, .98)" in APP_CSS
    assert "background: #1f9d8b" in APP_CSS
