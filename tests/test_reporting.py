"""Dashboard reporting preparation tests."""

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.reporting.summary import (
    COMPACT_RESULT_COLUMNS,
    LOWEST_RESULT_COLUMNS,
    ROW_DETAIL_FIELDS,
    filter_dashboard_results,
    prepare_compact_results,
    prepare_lowest_scoring_results,
    prepare_row_details,
    summarize_results,
)


@pytest.fixture
def dashboard_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "question": ["Passing question", "Weak answer", "Unsupported claim"],
            "answer": ["Good answer", "Off-topic answer", "Uncited answer"],
            "expected_answer": ["Good answer", None, "Supported answer"],
            "context": [None, "Relevant context", "Different context"],
            "quality_score": [88.24, 42.16, 51.04],
            "relevance_score": [90.0, 25.0, 72.0],
            "correctness_score": [91.0, None, 62.0],
            "groundedness_score": [None, 60.0, 35.0],
            "completeness_score": [82.0, 55.0, 65.0],
            "status": ["Pass", "Fail", "Fail"],
            "error_type": ["No Error", "Irrelevant Answer", "Unsupported Answer"],
            "improvement_feedback": ["Passed.", "Address the question.", "Use context."],
        }
    )


def test_results_summary_counts(dashboard_results: pd.DataFrame) -> None:
    summary = summarize_results(dashboard_results)
    assert summary["total"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 2
    assert summary["pass_rate"] == 33.3
    assert summary["average_quality_score"] == 60.5


def test_compact_results_have_status_first_and_readable_values(
    dashboard_results: pd.DataFrame,
) -> None:
    compact = prepare_compact_results(dashboard_results)
    assert tuple(compact.columns) == COMPACT_RESULT_COLUMNS
    assert compact["Status"].tolist() == ["PASS", "FAIL", "FAIL"]
    assert compact["Quality"].tolist() == ["88.2", "42.2", "51.0"]
    assert compact.loc[0, "Expected Answer"] == "Good answer"
    assert compact.loc[0, "Context"] == "N/A"
    assert compact.loc[1, "Expected Answer"] == "N/A"


def test_lowest_scoring_results_prioritize_failures_and_column_order(
    dashboard_results: pd.DataFrame,
) -> None:
    lowest = prepare_lowest_scoring_results(dashboard_results, limit=2)
    assert tuple(lowest.columns) == LOWEST_RESULT_COLUMNS
    assert lowest["Status"].tolist() == ["FAIL", "FAIL"]
    assert lowest["Quality"].tolist() == ["42.2", "51.0"]
    assert "Passing question" not in lowest["Question"].tolist()


def test_filter_dashboard_results_by_pass(dashboard_results: pd.DataFrame) -> None:
    filtered = filter_dashboard_results(dashboard_results, status="Pass")
    assert filtered["status"].tolist() == ["Pass"]
    assert filtered["error_type"].tolist() == ["No Error"]


def test_filter_dashboard_results_by_fail(dashboard_results: pd.DataFrame) -> None:
    filtered = filter_dashboard_results(dashboard_results, status="Fail")
    assert filtered["status"].tolist() == ["Fail", "Fail"]
    assert "No Error" not in filtered["error_type"].tolist()


def test_filter_dashboard_results_by_error_type(
    dashboard_results: pd.DataFrame,
) -> None:
    filtered = filter_dashboard_results(
        dashboard_results, error_type="Unsupported Answer"
    )
    assert filtered["question"].tolist() == ["Unsupported claim"]


def test_row_details_include_all_fields_and_na_values(
    dashboard_results: pd.DataFrame,
) -> None:
    details = prepare_row_details(dashboard_results.iloc[0])
    assert tuple(details) == ROW_DETAIL_FIELDS
    assert details["Status"] == "PASS"
    assert details["Quality score"] == "88.2"
    assert details["Correctness"] == "91.0"
    assert details["Groundedness"] == "N/A"
    assert details["Context"] == "N/A"
    assert details["Improvement feedback"] == "Passed."


def test_dashboard_renders_with_missing_quality_scores() -> None:
    app = AppTest.from_string(
        """
import pandas as pd
from src.ui.app import _render_dashboard

_render_dashboard(pd.DataFrame({
    "question": ["Q1", "Q2"],
    "answer": ["A1", "A2"],
    "quality_score": [75.0, None],
    "relevance_score": [80.0, None],
    "correctness_score": [None, None],
    "groundedness_score": [None, None],
    "completeness_score": [70.0, None],
    "status": ["Pass", "Fail"],
    "error_type": ["No Error", "Incomplete Answer"],
}))
"""
    ).run()

    assert not app.exception


def test_dashboard_filter_controls_update_visible_result_count() -> None:
    app = AppTest.from_string(
        """
import pandas as pd
from src.ui.app import _render_dashboard

_render_dashboard(pd.DataFrame({
    "question": ["Pass question", "Fail one", "Fail two"],
    "answer": ["Pass answer", "Wrong", "Unsupported"],
    "expected_answer": ["Pass answer", "Right", "Supported"],
    "context": [None, None, "Supported context"],
    "quality_score": [90.0, 40.0, 50.0],
    "relevance_score": [90.0, 30.0, 70.0],
    "correctness_score": [90.0, 35.0, 60.0],
    "groundedness_score": [None, None, 30.0],
    "completeness_score": [90.0, 55.0, 65.0],
    "status": ["Pass", "Fail", "Fail"],
    "error_type": ["No Error", "Incorrect Answer", "Unsupported Answer"],
    "improvement_feedback": ["Passed", "Correct it", "Ground it"],
}))
"""
    ).run()

    assert not app.exception
    status_filter = next(item for item in app.selectbox if item.label == "Status")
    status_filter.set_value("Pass").run()
    assert any(
        "Showing 1 of 3 evaluated responses" in item.value for item in app.caption
    )

    status_filter = next(item for item in app.selectbox if item.label == "Status")
    status_filter.set_value("Fail").run()
    assert any(
        "Showing 2 of 3 evaluated responses" in item.value for item in app.caption
    )

    error_filter = next(item for item in app.selectbox if item.label == "Error Type")
    error_filter.set_value("Unsupported Answer").run()
    assert any(
        "Showing 1 of 3 evaluated responses" in item.value for item in app.caption
    )


def test_empty_dashboard_renders_without_exception() -> None:
    app = AppTest.from_string(
        """
import pandas as pd
from src.ui.app import _render_dashboard

_render_dashboard(pd.DataFrame())
"""
    ).run()

    assert not app.exception
