"""Safe batch evaluation."""

from __future__ import annotations

import pandas as pd

from src.evaluators.hybrid import OfflineHybridEvaluator


def _optional_text(row: pd.Series, column: str) -> str | None:
    value = row.get(column)
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return str(value)


def evaluate_batch(
    data: pd.DataFrame,
    evaluator: OfflineHybridEvaluator,
) -> pd.DataFrame:
    """Evaluate valid rows while retaining every original column."""

    records: list[dict[str, object]] = []
    for _, row in data.iterrows():
        result = evaluator.evaluate(
            question=str(row["question"]),
            answer=str(row["answer"]),
            expected_answer=_optional_text(row, "expected_answer"),
            context=_optional_text(row, "context"),
        )
        records.append({**row.to_dict(), **result.to_dict()})
    return pd.DataFrame(records)
