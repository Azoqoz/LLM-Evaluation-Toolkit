"""HTTP request and response schemas; evaluator outputs keep their own model."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr

from src.config.settings import DEFAULT_PASS_THRESHOLD


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required keys, but blank/null values retain the core evaluator behavior.
    question: StrictStr | None
    answer: StrictStr | None
    expected_answer: StrictStr | None = None
    context: StrictStr | None = None
    pass_threshold: Annotated[
        StrictInt | StrictFloat, Field(ge=0, le=100, allow_inf_nan=False)
    ] = DEFAULT_PASS_THRESHOLD


class HealthResponse(BaseModel):
    status: str
    evaluator_version: str


class ReadinessResponse(BaseModel):
    status: Literal["warming", "ready", "error"]
    message: str | None = None


class ThresholdRange(BaseModel):
    minimum: int
    maximum: int
    inclusive: bool


class ConfigurationResponse(BaseModel):
    default_pass_threshold: int
    pass_threshold: ThresholdRange
    model_name: str
    metric_weights: dict[str, float]


class CapabilitiesResponse(BaseModel):
    app_name: str
    evaluation_mode: str
    evaluator_version: str
    single_evaluation: bool
    batch_csv_evaluation: bool
    offline_first: bool
    model_download_on_cache_miss: bool
    configuration: ConfigurationResponse
    required_csv_columns: list[str]
    optional_csv_columns: list[str]
    result_columns: list[str]
    error_types: list[str]
    nullable_metrics: list[str]
    app_mode: Literal["demo", "local"]
    csv_upload_allowed: bool
    threshold_editable: bool
    demo_pass_threshold: int
    benchmark: "BenchmarkInfo"


class BenchmarkInfo(BaseModel):
    id: str
    title: str
    row_count: int


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatchValidation(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    empty_required_values: int
    duplicate_rows: int
    missing_required_columns: list[str]
    can_evaluate: bool


class BatchResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    validation: BatchValidation
    invalid_rows: list[dict[str, Any]]
    summary: dict[str, int | float | None]
    evaluated_csv: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    error: ErrorDetail
