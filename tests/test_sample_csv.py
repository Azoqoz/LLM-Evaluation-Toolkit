"""Official downloadable sample regression tests."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch
from src.ui.app import SAMPLE_CSV_PATH


EXPECTED_COLUMNS = ["id", "question", "answer", "expected_answer", "context"]


class HighSimilarityScorer:
    """Keep sample outcome tests deterministic and independent of model loading."""

    def similarity(self, left: str, right: str) -> float:
        return 90.0


def test_official_sample_schema_validation_and_outcomes() -> None:
    expected_path = Path("data/sample_evaluations.csv").resolve()
    assert SAMPLE_CSV_PATH == expected_path

    sample = read_csv_bytes(SAMPLE_CSV_PATH.read_bytes())
    assert sample.columns.tolist() == EXPECTED_COLUMNS
    assert len(sample) == 6

    validation = validate_dataframe(sample)
    assert validation.total_rows == 6
    assert validation.valid_rows == 6
    assert validation.invalid_rows == 0
    assert validation.duplicate_rows == 0

    results = evaluate_batch(
        validation.valid_data,
        OfflineHybridEvaluator(HighSimilarityScorer()),
    )
    assert results["status"].value_counts().to_dict() == {"Pass": 3, "Fail": 3}
    outcomes = results.set_index("id")[["status", "error_type"]].to_dict("index")
    assert outcomes["demo-001"] == {"status": "Pass", "error_type": "No Error"}
    assert outcomes["demo-002"] == {
        "status": "Fail",
        "error_type": "Contradictory Answer",
    }
    assert outcomes["demo-003"] == {"status": "Pass", "error_type": "No Error"}
    assert outcomes["demo-004"] == {
        "status": "Fail",
        "error_type": "Incomplete Answer",
    }
    assert outcomes["demo-005"] == {
        "status": "Fail",
        "error_type": "Unwanted Refusal",
    }
    assert outcomes["demo-006"] == {"status": "Pass", "error_type": "No Error"}


def test_official_sample_dashboard_renders() -> None:
    app = AppTest.from_string(
        """
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch
from src.ui.app import SAMPLE_CSV_PATH, _render_dashboard

class HighSimilarityScorer:
    def similarity(self, left, right):
        return 90.0

sample = read_csv_bytes(SAMPLE_CSV_PATH.read_bytes())
validation = validate_dataframe(sample)
results = evaluate_batch(
    validation.valid_data,
    OfflineHybridEvaluator(HighSimilarityScorer()),
)
_render_dashboard(results)
"""
    ).run()

    assert not app.exception
