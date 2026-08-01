"""CSV validation tests."""

import pandas as pd

from src.evaluators.rules import evaluate_rules
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe


def test_valid_schema_and_duplicate_detection() -> None:
    data = pd.DataFrame(
        {
            "question": ["Q1", "Q1", "Q2"],
            "answer": ["A1", "A1", ""],
            "id": [1, 2, 3],
        }
    )
    result = validate_dataframe(data)
    assert result.total_rows == 3
    assert result.valid_rows == 1
    assert result.invalid_rows == 2
    assert result.duplicate_rows == 1
    assert result.empty_required_values == 1


def test_missing_required_columns() -> None:
    result = validate_dataframe(pd.DataFrame({"question": ["Q"]}))
    assert result.missing_required_columns == ["answer"]
    assert result.valid_rows == 0
    assert not result.can_evaluate


def test_csv_preserves_literal_placeholders_but_rejects_empty_answers(
    evaluator,
) -> None:
    data = read_csv_bytes(
        b"question,answer\nQ1,N/A\nQ2,NA\nQ3,None\nQ4,\n"
    )

    assert data["answer"].tolist() == ["N/A", "NA", "None", ""]
    validation = validate_dataframe(data)
    assert validation.valid_rows == 3
    assert validation.invalid_rows == 1
    assert validation.empty_required_values == 1
    assert validation.valid_data["answer"].tolist() == ["N/A", "NA", "None"]
    assert all(
        evaluate_rules("Question", answer).placeholder
        for answer in validation.valid_data["answer"]
    )
    assert all(
        evaluator.evaluate("Question", answer).error_type == "Insufficient Data"
        for answer in validation.valid_data["answer"]
    )
