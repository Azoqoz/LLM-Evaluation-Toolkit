"""Unmodified evaluator decisions, including exact threshold boundaries."""

from pathlib import Path

import pandas as pd
import pytest

from src.evaluators.hybrid import OfflineHybridEvaluator
from src.evaluators.semantic import SentenceTransformerScorer
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch

CASES = [
    ("How long is the return period?", "two weeks", "14 days", "14 days"),
    ("How long is the return period?", "30 days", "14 days", "14 days"),
    ("What is the refund policy?", "I cannot answer that request.", None, None),
    ("What is the refund policy?", "", None, None),
    ("What is the refund policy?", "What is the refund policy?", None, None),
    ("When are backups made?", "Backups are made daily.", "every 24 hours", "daily backups"),
    ("Explain the return policy.", "The return policy allows returns within fourteen days.", None, None),
]


@pytest.mark.parametrize("case", CASES)
def test_semantic_fixtures_and_threshold_boundaries(onnx_model, reference_model, case):
    local = OfflineHybridEvaluator(SentenceTransformerScorer(model=reference_model))
    demo = OfflineHybridEvaluator(SentenceTransformerScorer(model=onnx_model))
    quality = local.evaluate(*case).quality_score
    thresholds = [0, 70, 100]
    if quality is not None:
        thresholds += [quality, max(0, quality - .01), min(100, quality + .01)]
    for threshold in thresholds:
        local.pass_threshold = demo.pass_threshold = threshold
        assert demo.evaluate(*case).to_dict() == local.evaluate(*case).to_dict()


def test_all_100_benchmark_outputs_are_equivalent(onnx_model, reference_model):
    path = Path(__file__).resolve().parents[2] / "data/demo_benchmark.csv"
    validation = validate_dataframe(read_csv_bytes(path.read_bytes()))
    assert validation.valid_rows == 100
    actual = evaluate_batch(validation.valid_data, OfflineHybridEvaluator(SentenceTransformerScorer(model=onnx_model)))
    expected = evaluate_batch(validation.valid_data, OfflineHybridEvaluator(SentenceTransformerScorer(model=reference_model)))
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    assert actual.status.value_counts().to_dict() == {"Fail": 60, "Pass": 40}
