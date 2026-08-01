"""Batch and export tests."""

from io import BytesIO

import pandas as pd

from src.config.settings import EXPORT_COLUMNS
from src.pipeline.batch import evaluate_batch
from src.reporting.export import prepare_export, to_csv_bytes


def test_export_contains_original_and_required_columns(evaluator) -> None:
    source = pd.DataFrame(
        {
            "id": ["case-1"],
            "question": ["What is caching?"],
            "answer": ["Caching stores reusable data for faster access."],
        }
    )
    results = evaluate_batch(source, evaluator)
    exported = prepare_export(results)
    assert exported.loc[0, "id"] == "case-1"
    assert set(EXPORT_COLUMNS).issubset(exported.columns)


def test_export_preserves_threshold_failure_classification(evaluator) -> None:
    evaluator.pass_threshold = 100
    source = pd.DataFrame(
        {
            "id": ["threshold-failure"],
            "question": ["Python lists store ordered values"],
            "answer": [
                "Python lists store ordered values in a mutable collection."
            ],
        }
    )

    results = evaluate_batch(source, evaluator)
    exported = pd.read_csv(BytesIO(to_csv_bytes(results)))

    assert exported.loc[0, "status"] == "Fail"
    assert exported.loc[0, "error_type"] != "No Error"
    assert "weakest available metric" in exported.loc[0, "improvement_feedback"]
    assert "configured pass threshold (100)" in exported.loc[
        0, "improvement_feedback"
    ]
