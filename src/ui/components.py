"""Reusable Streamlit components."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.config.settings import get_app_mode
from src.pipeline.models import EvaluationResult


def metric_display(value: float | None) -> str:
    """Format available scores and preserve N/A."""

    return "N/A" if value is None else f"{value:.1f}"


def render_result(result: EvaluationResult) -> None:
    """Render a single evaluation result."""

    status_icon = "✓" if result.status == "Pass" else "×"
    st.subheader(f"{status_icon} {result.status}")
    st.caption(f"Primary finding: {result.error_type}")
    columns = st.columns(5)
    metrics: list[tuple[str, Any]] = [
        ("Quality", result.quality_score),
        ("Relevance", result.relevance_score),
        ("Correctness", result.correctness_score),
        ("Groundedness", result.groundedness_score),
        ("Completeness", result.completeness_score),
    ]
    for column, (label, value) in zip(columns, metrics):
        column.metric(label, metric_display(value))
    st.info(result.improvement_feedback)


def render_intro(page: str) -> None:
    """Render the page-specific hero."""

    st.markdown('<div class="eyebrow">Offline evaluation workspace</div>', unsafe_allow_html=True)
    st.title(page)
    if page == "Single Evaluation":
        copy = (
            "Score one model response for relevance, correctness, groundedness, "
            "completeness, and overall quality."
        )
    else:
        copy = (
            "Validate and evaluate a CSV dataset, inspect quality patterns, "
            "and export enriched results."
        )
    st.markdown(f'<p class="hero-copy">{copy}</p>', unsafe_allow_html=True)
    app_mode = get_app_mode()
    badge_text = (
        "Demo Mode · Hosted evaluation"
        if app_mode == "demo"
        else "Full Local Mode · Offline evaluation"
    )
    st.markdown(
        f'<span class="runtime-badge {app_mode}">{badge_text}</span>',
        unsafe_allow_html=True,
    )
