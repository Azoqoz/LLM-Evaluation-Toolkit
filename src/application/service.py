"""Application orchestration; no HTTP or Streamlit dependencies.

The original evaluator, validator, batch loop, summary and exporter remain the
source of behavior. A new evaluator is created for each operation so concurrent
requests never mutate a shared pass threshold. The existing embedding loader
continues to cache model weights and load from disk before trying a download.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from src.application.serialization import serialize_result, serialize_rows
from src.config.settings import (
    APP_NAME,
    DEFAULT_MODEL_NAME,
    DEFAULT_PASS_THRESHOLD,
    ERROR_TYPES,
    EVALUATION_MODE,
    EVALUATOR_VERSION,
    EXPORT_COLUMNS,
    METRIC_WEIGHTS,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
)
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import (
    CsvValidationResult,
    read_csv_bytes,
    validate_dataframe,
)
from src.pipeline.batch import evaluate_batch
from src.reporting.export import prepare_export, to_csv_bytes
from src.reporting.summary import summarize_results


class ApplicationError(Exception):
    """A stable, public error; never constructed from raw exception messages."""

    def __init__(
        self, code: str, message: str, details: dict[str, object] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def validate_threshold(value: int | float) -> None:
    """Validate the transport's numeric type without coercing int to float.

    Retaining the numeric type matters: threshold feedback embeds its string
    representation (for example 80 versus 80.0).
    """

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 100
        or not math.isfinite(value)
    ):
        raise ApplicationError(
            "invalid_request",
            "pass_threshold must be a finite number between 0 and 100.",
            {"field": "pass_threshold"},
        )


def validation_metadata(result: CsvValidationResult) -> dict[str, object]:
    return {
        "total_rows": result.total_rows,
        "valid_rows": result.valid_rows,
        "invalid_rows": result.invalid_rows,
        "empty_required_values": result.empty_required_values,
        "duplicate_rows": result.duplicate_rows,
        "missing_required_columns": list(result.missing_required_columns),
        "can_evaluate": result.can_evaluate,
    }


@dataclass(frozen=True)
class BatchEvaluationResult:
    """Original evaluated rows and validation information, before transport."""

    results: pd.DataFrame
    validation: CsvValidationResult

    def to_dict(self) -> dict[str, object]:
        exported = prepare_export(self.results)
        return {
            "columns": list(exported.columns),
            "rows": serialize_rows(exported),
            "validation": validation_metadata(self.validation),
            "invalid_rows": serialize_rows(self.validation.invalid_data),
            "summary": summarize_results(self.results),
            "evaluated_csv": to_csv_bytes(self.results).decode("utf-8"),
        }


class EvaluationService:
    """Reusable synchronous service with an injectable evaluator factory."""

    def __init__(
        self,
        evaluator_factory: Callable[[int | float], OfflineHybridEvaluator] | None = None,
    ) -> None:
        self._evaluator_factory = evaluator_factory or (
            lambda threshold: OfflineHybridEvaluator(pass_threshold=threshold)
        )

    def health(self) -> dict[str, str]:
        """Liveness only; do not load or claim readiness of the model."""

        return {"status": "ok", "evaluator_version": EVALUATOR_VERSION}

    def configuration(self) -> dict[str, object]:
        return {
            "default_pass_threshold": DEFAULT_PASS_THRESHOLD,
            "pass_threshold": {"minimum": 0, "maximum": 100, "inclusive": True},
            "model_name": DEFAULT_MODEL_NAME,
            "metric_weights": dict(METRIC_WEIGHTS),
        }

    def capabilities(self) -> dict[str, object]:
        return {
            "app_name": APP_NAME,
            "evaluation_mode": EVALUATION_MODE,
            "evaluator_version": EVALUATOR_VERSION,
            "single_evaluation": True,
            "batch_csv_evaluation": True,
            "offline_first": True,
            "model_download_on_cache_miss": True,
            "configuration": self.configuration(),
            "required_csv_columns": list(REQUIRED_COLUMNS),
            "optional_csv_columns": list(OPTIONAL_COLUMNS),
            "result_columns": list(EXPORT_COLUMNS),
            "error_types": list(ERROR_TYPES),
            "nullable_metrics": [
                "relevance_score", "correctness_score", "groundedness_score",
                "completeness_score", "quality_score",
            ],
        }

    def evaluate(
        self,
        question: str | None,
        answer: str | None,
        expected_answer: str | None = None,
        context: str | None = None,
        pass_threshold: int | float = DEFAULT_PASS_THRESHOLD,
    ) -> dict[str, object]:
        validate_threshold(pass_threshold)
        for field, value in (
            ("question", question), ("answer", answer),
            ("expected_answer", expected_answer), ("context", context),
        ):
            if value is not None and not isinstance(value, str):
                raise ApplicationError(
                    "invalid_request", "Text fields must be strings or null.",
                    {"field": field},
                )
        try:
            result = self._evaluator_factory(pass_threshold).evaluate(
                question, answer, expected_answer, context
            )
            return serialize_result(result)
        except Exception as exc:
            raise ApplicationError(
                "evaluation_failed", "The local evaluator could not complete the evaluation."
            ) from exc

    def evaluate_csv(
        self, content: bytes, pass_threshold: int | float = DEFAULT_PASS_THRESHOLD
    ) -> BatchEvaluationResult:
        validate_threshold(pass_threshold)
        if not isinstance(content, bytes):
            raise ApplicationError("invalid_csv", "CSV content must be supplied as bytes.")
        try:
            data = read_csv_bytes(content)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as exc:
            raise ApplicationError(
                "invalid_csv", "The upload could not be read as a UTF-8 CSV."
            ) from exc
        try:
            validation = validate_dataframe(data)
        except (AttributeError, ValueError, TypeError) as exc:
            # The original validator cannot handle some normalized header
            # collisions. Report them without repairing/reinterpreting the CSV.
            raise ApplicationError(
                "invalid_csv_schema", "The CSV column structure could not be validated."
            ) from exc
        metadata = validation_metadata(validation)
        if validation.missing_required_columns:
            raise ApplicationError(
                "missing_csv_columns", "The CSV is missing required columns.", metadata
            )
        if not validation.can_evaluate:
            raise ApplicationError(
                "no_valid_rows", "The CSV has no valid rows to evaluate.", metadata
            )
        try:
            results = evaluate_batch(
                validation.valid_data, self._evaluator_factory(pass_threshold)
            )
        except Exception as exc:
            raise ApplicationError(
                "evaluation_failed", "The local evaluator could not complete the evaluation."
            ) from exc
        return BatchEvaluationResult(results, validation)
