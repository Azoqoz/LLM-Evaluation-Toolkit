"""Batch dashboard summaries."""

from __future__ import annotations

import math

import pandas as pd

COMPACT_RESULT_COLUMNS = (
    "Status",
    "Quality",
    "Error Type",
    "Question",
    "Answer",
    "Expected Answer",
    "Context",
)
LOWEST_RESULT_COLUMNS = (
    "Status",
    "Quality",
    "Error Type",
    "Question",
    "Answer",
)
ROW_DETAIL_FIELDS = (
    "Status",
    "Quality score",
    "Error type",
    "Question",
    "Answer",
    "Expected answer",
    "Context",
    "Relevance",
    "Correctness",
    "Groundedness",
    "Completeness",
    "Improvement feedback",
)


def _display_text(value: object) -> str:
    """Return a readable display string for an optional scalar value."""

    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return "N/A"
    text = str(value).strip()
    return text if text else "N/A"


def _display_score(value: object) -> str:
    """Format a score to one decimal place, preserving unavailable values."""

    try:
        score = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return "N/A" if math.isnan(score) else f"{score:.1f}"


def filter_dashboard_results(
    results: pd.DataFrame,
    status: str = "All",
    error_type: str = "All",
) -> pd.DataFrame:
    """Apply the dashboard's deterministic single-select filters."""

    filtered = results.copy()
    if status != "All" and "status" in filtered:
        filtered = filtered[filtered["status"].eq(status)]
    if error_type != "All" and "error_type" in filtered:
        filtered = filtered[filtered["error_type"].eq(error_type)]
    return filtered


def prepare_compact_results(results: pd.DataFrame) -> pd.DataFrame:
    """Return the fixed, readable primary table without mutating results."""

    index = results.index
    values = {
        "Status": results.get("status", pd.Series(index=index, dtype=object)).map(
            lambda value: _display_text(value).upper()
        ),
        "Quality": results.get(
            "quality_score", pd.Series(index=index, dtype=float)
        ).map(_display_score),
        "Error Type": results.get(
            "error_type", pd.Series(index=index, dtype=object)
        ).map(_display_text),
        "Question": results.get(
            "question", pd.Series(index=index, dtype=object)
        ).map(_display_text),
        "Answer": results.get("answer", pd.Series(index=index, dtype=object)).map(
            _display_text
        ),
        "Expected Answer": results.get(
            "expected_answer", pd.Series(index=index, dtype=object)
        ).map(_display_text),
        "Context": results.get(
            "context", pd.Series(index=index, dtype=object)
        ).map(_display_text),
    }
    return pd.DataFrame(values, index=index).reset_index(drop=True)


def prepare_lowest_scoring_results(
    results: pd.DataFrame, limit: int = 5
) -> pd.DataFrame:
    """Prefer failed rows, then fill remaining slots with the lowest passes."""

    if results.empty or limit <= 0:
        return pd.DataFrame(columns=LOWEST_RESULT_COLUMNS)
    working = results.copy()
    quality_values = working.get(
        "quality_score", pd.Series(index=working.index, dtype=float)
    )
    working["_quality_numeric"] = pd.to_numeric(
        quality_values, errors="coerce"
    )
    status = working.get("status", pd.Series(index=working.index, dtype=object))
    failed = working[status.eq("Fail")].sort_values(
        "_quality_numeric", na_position="last"
    )
    passed = working[~status.eq("Fail")].sort_values(
        "_quality_numeric", na_position="last"
    )
    selected = pd.concat([failed.head(limit), passed.head(max(0, limit - len(failed)))])
    compact = prepare_compact_results(selected)
    return compact.loc[:, list(LOWEST_RESULT_COLUMNS)]


def prepare_row_details(row: pd.Series) -> dict[str, str]:
    """Return complete display-ready details for one evaluated row."""

    details = {
        "Status": _display_text(row.get("status")).upper(),
        "Quality score": _display_score(row.get("quality_score")),
        "Error type": _display_text(row.get("error_type")),
        "Question": _display_text(row.get("question")),
        "Answer": _display_text(row.get("answer")),
        "Expected answer": _display_text(row.get("expected_answer")),
        "Context": _display_text(row.get("context")),
        "Relevance": _display_score(row.get("relevance_score")),
        "Correctness": _display_score(row.get("correctness_score")),
        "Groundedness": _display_score(row.get("groundedness_score")),
        "Completeness": _display_score(row.get("completeness_score")),
        "Improvement feedback": _display_text(row.get("improvement_feedback")),
    }
    return {field: details[field] for field in ROW_DETAIL_FIELDS}


def summarize_results(results: pd.DataFrame) -> dict[str, float | int | None]:
    """Calculate high-level batch metrics with unavailable values preserved."""

    total = len(results)
    statuses = results.get("status", pd.Series(index=results.index, dtype=object))
    passed = int(statuses.eq("Pass").sum()) if total else 0
    summary: dict[str, float | int | None] = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0.0,
        "fail_rate": round((total - passed) / total * 100, 1) if total else 0.0,
    }
    for metric in (
        "quality_score",
        "relevance_score",
        "correctness_score",
        "groundedness_score",
        "completeness_score",
    ):
        metric_values = results.get(metric, pd.Series(index=results.index, dtype=float))
        values = pd.to_numeric(metric_values, errors="coerce")
        summary[f"average_{metric}"] = (
            round(float(values.mean()), 1) if values.notna().any() else None
        )
    return summary
