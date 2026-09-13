"""CSV parsing, validation, batch execution and wire-format parity."""

from io import BytesIO
from unittest.mock import Mock

import pandas as pd
import pytest

from src.config.settings import EXPORT_COLUMNS, INPUT_COLUMNS
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch
from src.reporting.export import prepare_export, to_csv_bytes


OUTPUT = ["relevance_score", "correctness_score", "groundedness_score", "completeness_score", "quality_score", "status", "error_type", "improvement_feedback", "evaluation_mode", "evaluated_at", "evaluator_version"]


def test_schema_constants():
    assert INPUT_COLUMNS == ("question", "answer", "expected_answer", "context", "id")
    assert list(EXPORT_COLUMNS) == OUTPUT


def test_csv_normalizes_headers_preserves_values_and_infers_numbers():
    source = read_csv_bytes(b' Question ,ANSWER,id,Extra\n Q ,N/A,001,x\nQ2,NA,002,y\nQ3,None,003,z\nQ4,,004,w\n')
    original = source.copy(deep=True)
    result = validate_dataframe(source)
    assert list(result.valid_data) == ["question", "answer", "id", "extra"]
    assert result.valid_data.answer.tolist() == ["N/A", "NA", "None"]
    assert result.valid_data.question.tolist() == [" Q ", "Q2", "Q3"]
    assert result.valid_data.id.tolist() == [1, 2, 3]
    assert (result.total_rows, result.valid_rows, result.invalid_rows, result.empty_required_values) == (4, 3, 1, 1)
    assert result.invalid_data._validation_error.tolist() == ["Empty required value(s): answer"]
    pd.testing.assert_frame_equal(source, original)


def test_duplicates_ignore_id_extra_case_whitespace_and_count_empty_cells():
    source = pd.DataFrame({"question": [" Q ", "q", "", None], "answer": [" A ", "a", "", None], "id": [1, 2, 3, 4], "extra": list("abcd")}, index=[10, 20, 30, 40])
    result = validate_dataframe(source)
    assert (result.valid_rows, result.invalid_rows, result.duplicate_rows, result.empty_required_values) == (1, 3, 2, 4)
    assert result.valid_data.index.tolist() == [10]
    assert result.invalid_data._validation_error.tolist() == ["Duplicate row", "Empty required value(s): question, answer", "Empty required value(s): question, answer; Duplicate row"]


@pytest.mark.parametrize("column", ["expected_answer", "context"])
def test_optional_references_participate_in_duplicate_key(column):
    result = validate_dataframe(pd.DataFrame({"question": ["q"] * 3, "answer": ["a"] * 3, column: ["x", "y", " X "]}))
    assert (result.valid_rows, result.duplicate_rows) == (2, 1)


def test_missing_columns_and_header_only_csv():
    result = validate_dataframe(pd.DataFrame({"extra": [1]}))
    assert result.missing_required_columns == ["question", "answer"]
    assert not result.can_evaluate
    assert result.invalid_data._validation_error.tolist() == ["Missing required column(s): question, answer"]
    empty = validate_dataframe(read_csv_bytes(b"question,answer\n"))
    assert (empty.total_rows, empty.valid_rows, empty.invalid_rows) == (0, 0, 0)
    assert not empty.can_evaluate


@pytest.mark.parametrize("content,error", [(b"", pd.errors.EmptyDataError), (b'question,answer\nq,"unterminated', pd.errors.ParserError), (b"question,answer\nq,\xff", UnicodeDecodeError)])
def test_parse_errors_propagate(content, error):
    with pytest.raises(error):
        read_csv_bytes(content)


def test_normalized_header_collision_currently_raises():
    with pytest.raises(AttributeError):
        validate_dataframe(pd.DataFrame([["q", "q", "a"]], columns=["Question", " question ", "answer"]))


def test_batch_matches_single_preserves_originals_and_export(scorer):
    source = pd.DataFrame({"id": ["001", "002"], "question": [" q ", "other"], "answer": ["alpha beta gamma delta epsilon"] * 2, "context": [None, "source"], "extra": ["é,quoted", "line\nbreak"], "quality_score": [-1, -1]}, index=[8, 9])
    original = source.copy(deep=True)
    evaluator = OfflineHybridEvaluator(scorer)
    result = evaluate_batch(source, evaluator)
    assert result.index.tolist() == [0, 1]
    assert result.question.tolist() == [" q ", "other"]
    for i, row in source.reset_index(drop=True).iterrows():
        single = evaluator.evaluate(row.question, row.answer, context=row.context).to_dict()
        for name, value in single.items():
            assert (pd.isna(result.loc[i, name]) if value is None else result.loc[i, name] == value)
    exported = prepare_export(result)
    assert list(exported) == ["id", "question", "answer", "context", "extra"] + OUTPUT
    payload = to_csv_bytes(result)
    assert isinstance(payload, bytes) and not payload.startswith(b"\xef\xbb\xbf")
    decoded = pd.read_csv(BytesIO(payload), keep_default_na=False, dtype=str)
    assert decoded.extra.tolist() == ["é,quoted", "line\nbreak"]
    assert decoded.correctness_score.tolist() == ["", ""]
    assert decoded.evaluated_at.tolist() == ["2026-01-02T03:04:05+00:00"] * 2
    pd.testing.assert_frame_equal(source, original)


def test_batch_does_not_validate_or_skip_rows(scorer):
    source = pd.DataFrame({"question": [None, None], "answer": [float("nan"), float("nan")], "expected_answer": [None, " "], "context": [pd.NA, ""]})
    result = evaluate_batch(source, OfflineHybridEvaluator(scorer))
    assert len(result) == 2
    assert scorer.calls == [("None", "nan")] * 2


def test_empty_batch_loses_input_schema_but_export_adds_outputs(scorer):
    result = evaluate_batch(pd.DataFrame(columns=["question", "answer"]), OfflineHybridEvaluator(scorer))
    assert list(result) == []
    assert list(prepare_export(result)) == OUTPUT
    assert to_csv_bytes(result).decode().strip() == ",".join(OUTPUT)


def test_batch_failure_aborts_without_partial_result():
    evaluator = Mock()
    evaluator.evaluate.side_effect = RuntimeError("row failed")
    with pytest.raises(RuntimeError, match="row failed"):
        evaluate_batch(pd.DataFrame({"question": ["q", "q2"], "answer": ["a", "a2"]}), evaluator)
    assert evaluator.evaluate.call_count == 1


def test_batch_missing_required_column_raises(scorer):
    with pytest.raises(KeyError, match="answer"):
        evaluate_batch(pd.DataFrame({"question": ["q"]}), OfflineHybridEvaluator(scorer))
