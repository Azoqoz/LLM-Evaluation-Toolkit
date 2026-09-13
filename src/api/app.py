"""Thin ASGI entry point: uvicorn src.api.app:app --host 127.0.0.1."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import Body, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from src.api.schemas import (
    BatchResponse,
    BenchmarkRequest,
    CapabilitiesResponse,
    ErrorResponse,
    EvaluationRequest,
    HealthResponse,
)
from src.application.service import ApplicationError, EvaluationService, validate_threshold
from src.config.settings import APP_NAME, DEFAULT_PASS_THRESHOLD, EVALUATOR_VERSION
from src.pipeline.models import EvaluationResult


def error_response(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def parse_form_threshold(value: str) -> int | float:
    # Multipart fields are strings. JSON numeric parsing preserves 80 vs 80.0
    # in the existing feedback text, unlike unconditional float conversion.
    try:
        threshold = json.loads(value)
    except (ValueError, TypeError) as exc:
        raise ApplicationError(
            "invalid_request", "pass_threshold must be a number between 0 and 100.",
            {"field": "pass_threshold"},
        ) from exc
    validate_threshold(threshold)
    return threshold


def create_app(service: EvaluationService | None = None) -> FastAPI:
    app = FastAPI(title=APP_NAME, version=EVALUATOR_VERSION, debug=False)
    app.state.evaluation_service = service if service is not None else EvaluationService()

    @app.middleware("http")
    async def reject_demo_upload_before_parsing(request: Request, call_next):
        # Reject before multipart parsing can spool a visitor's file to disk.
        if request.method == "POST" and request.url.path.rstrip("/") == "/evaluate/batch":
            try:
                request.app.state.evaluation_service.require_csv_upload()
            except ApplicationError as exc:
                return error_response(403, exc.code, exc.message, exc.details)
        return await call_next(request)

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError):
        status = {"evaluation_failed": 503, "demo_restricted": 403}.get(exc.code, 422)
        return error_response(status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, exc: RequestValidationError):
        # Do not echo input, exception context, or arbitrary user-provided keys.
        fields = {"question", "answer", "expected_answer", "context", "pass_threshold", "file"}
        issues = [
            {"field": next((part for part in error["loc"] if part in fields), "request"),
             "type": error["type"]}
            for error in exc.errors()
        ]
        return error_response(422, "invalid_request", "The request is invalid.", {"issues": issues})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        # Multipart parser messages can contain supplied header data.
        return error_response(exc.status_code, "http_error", "The HTTP request could not be processed.")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return error_response(500, "internal_error", "The request could not be completed.")

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request):
        return request.app.state.evaluation_service.health()

    @app.get("/capabilities", response_model=CapabilitiesResponse)
    def capabilities(request: Request) -> dict[str, object]:
        return request.app.state.evaluation_service.capabilities()

    errors = {403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}

    @app.post("/evaluate/benchmark", response_model=BatchResponse, responses=errors)
    def benchmark(request: Request, payload: BenchmarkRequest = Body(default=BenchmarkRequest())):
        return request.app.state.evaluation_service.evaluate_benchmark().to_dict()

    @app.post("/evaluate", response_model=EvaluationResult, responses=errors)
    def evaluate(payload: EvaluationRequest, request: Request):
        return request.app.state.evaluation_service.evaluate(**payload.model_dump())

    @app.post("/evaluate/batch", response_model=BatchResponse, responses=errors)
    def evaluate_csv(
        request: Request,
        file: Annotated[UploadFile, File(description="CSV with question and answer columns")],
        pass_threshold: Annotated[str, Form(description="Number from 0 to 100, inclusive")] = str(DEFAULT_PASS_THRESHOLD),
    ):
        # Sync routes run evaluation in FastAPI's worker pool. Uploaded content
        # stays request-scoped; no user-supplied filename is opened or persisted.
        threshold = parse_form_threshold(pass_threshold)
        result = request.app.state.evaluation_service.evaluate_csv(file.file.read(), threshold)
        return result.to_dict()

    return app


app = create_app()
