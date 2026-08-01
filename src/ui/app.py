"""Main Streamlit interface."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config.settings import DEFAULT_PASS_THRESHOLD, ERROR_TYPES, get_app_mode
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch
from src.reporting.export import to_csv_bytes
from src.reporting.summary import (
    filter_dashboard_results,
    prepare_compact_results,
    prepare_lowest_scoring_results,
    prepare_row_details,
    summarize_results,
)
from src.ui.components import metric_display, render_intro, render_result
from src.ui.styles import APP_CSS


SAMPLE_CSV_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "sample_evaluations.csv"
)

_SINGLE_FIELD_KEYS = (
    "single_question",
    "single_answer",
    "single_expected_answer",
    "single_context",
)


@st.cache_resource(show_spinner="Loading the local embedding model…")
def get_evaluator(pass_threshold: int) -> OfflineHybridEvaluator:
    """Create and cache the model-backed evaluator per threshold."""

    return OfflineHybridEvaluator(pass_threshold=pass_threshold)


def _advanced_settings() -> int:
    with st.sidebar.expander("Advanced Settings", expanded=False):
        threshold = st.slider(
            "Pass threshold",
            min_value=0,
            max_value=100,
            value=DEFAULT_PASS_THRESHOLD,
            help="Minimum normalized quality score required to pass.",
        )
        st.caption("Scores use only available metrics and normalize their weights.")
    return threshold


def _clear_single_fields() -> None:
    """Clear only the Single Evaluation inputs and displayed result."""

    for key in _SINGLE_FIELD_KEYS:
        st.session_state[key] = ""
    st.session_state.pop("single_result", None)


def _render_single(threshold: int) -> None:
    render_intro("Single Evaluation")
    st.markdown(
        "Question and answer are required. Without an expected answer, correctness "
        "is N/A; without context, the groundedness estimate is N/A."
    )
    with st.form("single_evaluation"):
        question = st.text_area(
            "Question *",
            key="single_question",
            placeholder="What question was the system asked?",
            height=100,
        )
        answer = st.text_area(
            "Answer *",
            key="single_answer",
            placeholder="Paste the response to evaluate.",
            height=170,
        )
        left, right = st.columns(2)
        expected = left.text_area(
            "Expected answer",
            key="single_expected_answer",
            placeholder="Optional reference answer",
            height=130,
        )
        context = right.text_area(
            "Context",
            key="single_context",
            placeholder="Optional source context",
            height=130,
        )
        with st.container(
            key="single_action_group",
            horizontal=True,
            horizontal_alignment="center",
            gap="medium",
        ):
            submitted = st.form_submit_button(
                "Run Evaluation",
                key="single_run_evaluation",
                type="primary",
                width=190,
            )
            st.form_submit_button(
                "Clear fields",
                key="single_clear_fields",
                type="secondary",
                width=132,
                on_click=_clear_single_fields,
            )
    if submitted:
        st.session_state.pop("single_result", None)
        if not question.strip() or not answer.strip():
            st.error("Enter both a question and an answer.")
            return
        try:
            result = get_evaluator(threshold).evaluate(
                question, answer, expected, context
            )
        except Exception as exc:
            st.error(
                "The local embedding model could not be loaded. On first use, "
                "connect to the internet so the model can download, then retry."
            )
            st.caption(str(exc))
            return
        st.session_state["single_result"] = result

    result = st.session_state.get("single_result")
    if result is not None:
        render_result(result)


def _validation_metrics(validation: object) -> None:
    columns = st.columns(5)
    columns[0].metric("Total rows", validation.total_rows)
    columns[1].metric("Valid rows", validation.valid_rows)
    columns[2].metric("Invalid rows", validation.invalid_rows)
    columns[3].metric("Empty required", validation.empty_required_values)
    columns[4].metric("Duplicates", validation.duplicate_rows)


def _status_table_style(frame: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Style PASS and FAIL cells as high-contrast status labels."""

    def status_style(value: object) -> str:
        if value == "PASS":
            return (
                "background-color: #153b35; color: #92e0d1; "
                "font-weight: 750; text-align: center;"
            )
        if value == "FAIL":
            return (
                "background-color: #452529; color: #efb1b7; "
                "font-weight: 750; text-align: center;"
            )
        return "color: #dce2e0; font-weight: 700; text-align: center;"

    return frame.style.map(status_style, subset=["Status"])


def _render_results_table(frame: pd.DataFrame) -> None:
    """Render a compact status-first dashboard table."""

    column_widths = {
        "Status": st.column_config.TextColumn("Status", width=82),
        "Quality": st.column_config.TextColumn("Quality", width=82),
        "Error Type": st.column_config.TextColumn("Error Type", width=145),
        "Question": st.column_config.TextColumn("Question", width=190),
        "Answer": st.column_config.TextColumn("Answer", width=235),
        "Expected Answer": st.column_config.TextColumn(
            "Expected Answer", width=190
        ),
        "Context": st.column_config.TextColumn("Context", width=190),
    }
    st.dataframe(
        _status_table_style(frame),
        column_config={
            column: column_widths[column]
            for column in frame.columns
            if column in column_widths
        },
        use_container_width=True,
        hide_index=True,
        height=min(420, 38 * (len(frame) + 1) + 4),
    )


def _render_row_details(filtered: pd.DataFrame) -> None:
    """Render a selector and complete details for one visible result."""

    if filtered.empty:
        return
    rows = filtered.reset_index(drop=True)

    def row_label(position: int) -> str:
        row = rows.iloc[position]
        question = str(row.get("question") or "N/A").strip() or "N/A"
        if len(question) > 68:
            question = question[:65].rstrip() + "…"
        return f"Row {position + 1} · {str(row.get('status', 'N/A')).upper()} · {question}"

    selected_position = st.selectbox(
        "Inspect evaluated row",
        options=list(range(len(rows))),
        format_func=row_label,
        key="dashboard_row_detail",
    )
    details = prepare_row_details(rows.iloc[selected_position])
    with st.expander("Full row details", expanded=False):
        status_class = "pass" if details["Status"] == "PASS" else "fail"
        st.markdown(
            f'<span class="result-status-badge {status_class}">'
            f'{details["Status"]}</span>',
            unsafe_allow_html=True,
        )
        overview = st.columns(3)
        overview[0].metric("Quality score", details["Quality score"])
        overview[1].markdown("**Error type**")
        overview[1].write(details["Error type"])
        overview[2].markdown("**Status**")
        overview[2].write(details["Status"])
        for label in ("Question", "Answer", "Expected answer", "Context"):
            st.markdown(f"**{label}**")
            st.write(details[label])
        score_columns = st.columns(4)
        for column, label in zip(
            score_columns,
            ("Relevance", "Correctness", "Groundedness", "Completeness"),
        ):
            column.metric(label, details[label])
        st.markdown("**Improvement feedback**")
        st.info(details["Improvement feedback"])


def _render_dashboard(results: pd.DataFrame) -> None:
    summary = summarize_results(results)
    st.header("Evaluation dashboard")
    st.subheader("Results summary")
    top = st.columns(5)
    top[0].metric("Total evaluated", summary["total"])
    with top[1].container(key="batch_summary_passed"):
        st.metric("Passed", summary["passed"])
    with top[2].container(key="batch_summary_failed"):
        st.metric("Failed", summary["failed"])
    top[3].metric("Pass rate", f'{summary["pass_rate"]:.1f}%')
    top[4].metric(
        "Average quality", metric_display(summary["average_quality_score"])
    )

    st.subheader("Average metric scores")
    metric_columns = st.columns(4)
    for column, (label, key) in zip(
        metric_columns,
        (
            ("Relevance", "average_relevance_score"),
            ("Correctness", "average_correctness_score"),
            ("Groundedness", "average_groundedness_score"),
            ("Completeness", "average_completeness_score"),
        ),
    ):
        column.metric(label, metric_display(summary[key]))

    if results.empty:
        st.info("No evaluated rows are available to chart.")
        return

    error_counts = results["error_type"].value_counts().rename_axis("error_type")
    st.subheader("Error types")
    st.bar_chart(error_counts, horizontal=True, use_container_width=True)

    st.subheader("Lowest-scoring examples")
    st.caption("The weakest responses are shown first, prioritizing failed rows.")
    _render_results_table(prepare_lowest_scoring_results(results))

    st.subheader("Results")
    filter_left, filter_right = st.columns(2)
    selected_status = filter_left.selectbox(
        "Status", ["All", "Pass", "Fail"], index=0, key="dashboard_status_filter"
    )
    available_error_values = set(results["error_type"].dropna().astype(str))
    present_errors = [item for item in ERROR_TYPES if item in available_error_values]
    present_errors.extend(sorted(available_error_values.difference(present_errors)))
    selected_error = filter_right.selectbox(
        "Error Type",
        ["All", *present_errors],
        index=0,
        key="dashboard_error_filter",
    )
    filtered = filter_dashboard_results(results, selected_status, selected_error)
    st.caption(
        f"Showing {len(filtered)} of {len(results)} evaluated responses"
    )
    _render_results_table(prepare_compact_results(filtered))
    _render_row_details(filtered)


def _render_batch(threshold: int) -> None:
    render_intro("Batch Evaluation")
    st.markdown(
        "Upload a CSV with `question` and `answer`. Optional columns: "
        "`expected_answer`, `context`, and `id`. Invalid rows are isolated safely."
    )
    st.download_button(
        "Download sample CSV",
        data=SAMPLE_CSV_PATH.read_bytes(),
        file_name="llm_evaluation_demo_sample.csv",
        mime="text/csv",
    )
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded is None:
        return
    upload_bytes = uploaded.getvalue()
    signature = hashlib.sha256(upload_bytes).hexdigest()
    if st.session_state.get("_uploaded_signature") != signature:
        st.session_state["_uploaded_signature"] = signature
        st.session_state.pop("batch_results", None)
    try:
        data = read_csv_bytes(upload_bytes)
    except Exception as exc:
        st.error(f"Could not read this CSV: {exc}")
        return

    validation = validate_dataframe(data)
    _validation_metrics(validation)
    if validation.missing_required_columns:
        st.error(
            "Missing required columns: "
            + ", ".join(validation.missing_required_columns)
        )
    if not validation.invalid_data.empty:
        with st.expander("Review invalid rows", expanded=False):
            st.dataframe(
                validation.invalid_data, use_container_width=True, hide_index=True
            )
    if not validation.can_evaluate:
        st.warning("No valid rows are available to evaluate.")
        return

    if st.button(
        f"Evaluate {validation.valid_rows} valid rows",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Running local semantic and rule-based checks…"):
                st.session_state["batch_results"] = evaluate_batch(
                    validation.valid_data, get_evaluator(threshold)
                )
        except Exception as exc:
            st.error(
                "The local embedding model could not be loaded. On first use, "
                "connect to the internet so it can download, then retry."
            )
            st.caption(str(exc))
            return

    results = st.session_state.get("batch_results")
    if isinstance(results, pd.DataFrame) and not results.empty:
        _render_dashboard(results)
        st.download_button(
            "Export evaluated CSV",
            data=to_csv_bytes(results),
            file_name="llm_evaluation_results.csv",
            mime="text/csv",
            type="primary",
        )


def _render_sidebar_mode(app_mode: str) -> None:
    """Render compact environment details in the sidebar."""

    st.markdown(
        '<div class="sidebar-section-label">Application mode</div>',
        unsafe_allow_html=True,
    )
    if app_mode == "demo":
        st.markdown(
            '<span class="mode-badge demo">DEMO MODE</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="sidebar-mode-copy">Hosted version for quick testing.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <ul class="sidebar-mode-points">
                <li>No API key required</li>
                <li>Single and CSV batch evaluation</li>
                <li>Uses hosted resources</li>
                <li>May have speed, memory, or file-size limits</li>
                <li>Run locally for private data and larger workloads</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<span class="mode-badge local">FULL LOCAL MODE</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sidebar-mode-copy">Complete offline evaluation on your machine.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <ul class="sidebar-mode-points">
            <li>No API key required</li>
            <li>Local sentence-transformer model</li>
            <li>Single and CSV batch evaluation</li>
            <li>Data remains on your machine</li>
            <li>Best for full-size datasets and private evaluation</li>
        </ul>
        """,
        unsafe_allow_html=True,
    )


def render_app() -> None:
    """Configure and render the complete application."""

    st.set_page_config(
        page_title="LLM Evaluation Toolkit",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    app_mode = get_app_mode()
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-title"><span>◈</span> LLM Evaluation Toolkit</div>
                <div class="sidebar-brand-subtitle">Quality evaluation for LLM and RAG outputs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        _render_sidebar_mode(app_mode)
        st.divider()
        page = st.radio(
            "Navigation",
            ("Single Evaluation", "Batch Evaluation"),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption(
            "Evaluates outputs—not model weights. Semantic scores are estimates."
        )
    threshold = _advanced_settings()
    if page == "Single Evaluation":
        _render_single(threshold)
    else:
        _render_batch(threshold)
