"""Transport-safe serialization without changing evaluator or CSV values."""

from __future__ import annotations

import math

import pandas as pd

from src.pipeline.models import EvaluationResult


def serialize_result(result: EvaluationResult) -> dict[str, object]:
    """Keep the evaluator's field order, nullable metrics, and metadata."""

    return result.to_dict()


def serialize_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Represent pandas missing/nonfinite scalars as JSON null.

    CSV is serialized separately by the existing exporter, without this JSON
    transport conversion. Do not round numbers or stringify original columns.
    """

    records = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return [
        {
            key: None if isinstance(value, float) and not math.isfinite(value) else value
            for key, value in record.items()
        }
        for record in records
    ]
