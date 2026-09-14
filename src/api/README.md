# Evaluation backend

Install `requirements.txt` in the project environment and run from the repository
root:

```console
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

The existing `app.py` still starts Streamlit and is unchanged. The new API uses
`src.application.service.EvaluationService`, which imports neither FastAPI nor
Streamlit and can also be called from Python. Its operations are `health()`,
`capabilities()`, `configuration()`, `evaluate(...)`, and `evaluate_csv(...)`.
An optional evaluator factory allows dependency injection. Startup initializes one evaluator and warms its model in a background thread. Operations reuse it under a lock, restoring the threshold after each operation. Direct Python callers must explicitly call initialize() and confirm readiness() before evaluating. Evaluation uses the unchanged scoring pipeline.

OpenAPI is available at `/openapi.json`; interactive docs are at `/docs`.

## HTTP contract

| Endpoint | Request | Success response |
| --- | --- | --- |
| `GET /health` | None | `status: "ok"`, `evaluator_version` (liveness only) |
| `GET /ready` | None | Uncached `warming`, `ready`, or safe `error` status |
| `GET /capabilities` | None | Supported operations, evaluator mode/version, configuration/defaults, CSV fields, result fields, nullable metrics, error types, cache/download behavior |
| `POST /evaluate` | JSON object | Original evaluation result fields, without an envelope |
| `POST /evaluate/batch` | Multipart `file`, optional `pass_threshold` form field | `columns`, `rows`, `validation`, `invalid_rows`, `summary`, `evaluated_csv` |
| `POST /evaluate/benchmark` | No body or `{}` | Same batch response, from the fixed 100-row repository benchmark |

The API now resolves `APP_MODE` from the environment at service startup (default
`local`); this does not change Streamlit's mode resolver. Capabilities includes
`app_mode`, `csv_upload_allowed`, `threshold_editable`, `demo_pass_threshold`, and
`benchmark` metadata. Public Demo allows free-form single evaluations at threshold
70, rejects CSV uploads before multipart parsing, and allows the fixed benchmark.
Local Mode retains the existing single and CSV behavior. Benchmark overrides are
rejected. See `frontend/README.md` for the complete EVALROOM setup.

Single request example:

```json
{
  "question": "How long is the return period?",
  "answer": "two weeks",
  "expected_answer": "14 days",
  "context": null,
  "pass_threshold": 70
}
```

`question` and `answer` keys are required, but blank strings and null retain the
core evaluator's behavior. Optional `expected_answer` and `context` default to
null. No text length limits are added. Text values must be strings or null;
other types and unknown JSON fields return 422. This is transport validation;
the original Python evaluator remains unchanged, including its permissive
handling of other falsy values. The existing Streamlit form still disallows
blank question/answer values.

Threshold defaults to the integer 70. It must be a finite number from 0 through
100, inclusive; booleans and numeric strings in JSON are rejected. Floating-point
thresholds remain supported. Multipart thresholds use JSON number syntax, such
as `80`, `80.0`, or `80.01`; their numeric representation is retained because
existing failure feedback includes it. A score at the threshold passes only
when the original error classification is `No Error`.

## Batch results and compatibility

CSV bytes go through the existing `read_csv_bytes`, `validate_dataframe`, and
`evaluate_batch` functions. Only validated rows are evaluated, as in Streamlit.
No file extension or MIME sniffing changes the CSV interpretation; uploaded
filenames are never used as filesystem paths.

`columns` and each evaluated row follow the existing `prepare_export` column
order: original non-result columns, then the original result columns. The
`evaluated_csv` string is the UTF-8 output of the original `to_csv_bytes`, allowing
a client to download results without re-evaluating or recreating CSV formatting.
The service's `BatchEvaluationResult.results` retains the native DataFrame.

`validation` contains `total_rows`, `valid_rows`, `invalid_rows`,
`empty_required_values`, `duplicate_rows`, `missing_required_columns`, and
`can_evaluate`. `invalid_rows` contains excluded input rows and the original
`_validation_error` messages. `summary` comes directly from `summarize_results`:
counts, pass/fail percentages, and averages of available metrics. These metadata
fields do not alter evaluated row values.

Existing CSV quirks are retained: normalized headers, inferred numeric IDs,
literal placeholder strings, duplicate comparison ignoring IDs/extra columns,
and empty-cell rather than empty-row counts. Collisions that the original
validator cannot handle return a structured error; they are not repaired.
All-invalid or header-only CSVs return 422, matching the application's refusal
to evaluate when no valid rows remain.

Unavailable metrics serialize as JSON null. Pandas missing values and nonfinite
numbers in CSV rows become JSON null because JSON cannot represent them; the
parallel `evaluated_csv` preserves the existing exporter output. Finite numbers
are not rounded by this transport conversion.

## Errors

All errors use this envelope without raw exception text, submitted JSON input,
stack traces, or internal filesystem paths:

```json
{
  "error": {
    "code": "missing_csv_columns",
    "message": "The CSV is missing required columns.",
    "details": {
      "total_rows": 1,
      "valid_rows": 0,
      "invalid_rows": 1,
      "empty_required_values": 0,
      "duplicate_rows": 0,
      "missing_required_columns": ["answer"],
      "can_evaluate": false
    }
  }
}
```

| HTTP status | Error codes |
| --- | --- |
| 422 | `invalid_request`, `invalid_csv`, `invalid_csv_schema`, `missing_csv_columns`, `no_valid_rows` |
| 403 | `demo_restricted` (CSV upload or threshold changes in Public Demo) |
| 503 | `evaluator_warming`, `evaluator_unavailable`, `evaluation_failed` |
| 500 | `internal_error` (unexpected application/serialization failure) |
| Other HTTP failures, such as 400/404/405 | `http_error` |

Request-validation details identify known fields and validation error types.
CSV validation failures include counts when available. Evaluator failures abort
the batch, with no partial results returned.

## Current limits

Health checks remain liveness probes. Use `/ready` to distinguish warm-up, readiness, and initialization failure. See [production startup](STARTUP.md) for build prefetch, Render commands, and retry behavior.

Requests use worker threads; rows within a batch remain sequential. CSV parsing
and results are held in memory, and returning JSON plus CSV increases payload
size. No application upload/row limits, jobs, streaming, persistence, cancellation,
authentication, CORS policy, or external LLM providers are added. Framework and
deployment transport limits can still apply. Real-model performance and concurrent
inference capacity are not established by the deterministic tests.

## Verification

```console
python -m pytest tests/backend -q
python -m pytest tests/parity -q
python -m pytest -q
```

Backend tests inject a deterministic scorer and freeze the clock while running
the real evaluator, rules, scoring, CSV validation, batch loop and exporter.
Unexpected real-model loading is blocked. They compare full outputs and CSV
bytes, including threshold representation and nullable metrics.

The transport follows FastAPI's documented [file upload](https://fastapi.tiangolo.com/tutorial/request-files/),
[exception handler](https://fastapi.tiangolo.com/tutorial/handling-errors/), and
[testing](https://fastapi.tiangolo.com/tutorial/testing/) interfaces.
