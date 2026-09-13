"""HTTP contracts and equivalence with the untouched Python pipeline."""

import json
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import EXPORT_COLUMNS
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe
from src.pipeline.batch import evaluate_batch
from src.reporting.export import prepare_export, to_csv_bytes
from src.reporting.summary import summarize_results


ANSWER = "alpha beta gamma delta epsilon"
PAYLOAD = {"question": "query", "answer": ANSWER}
CSV = b"id, Question ,answer,expected_answer,context,extra,quality_score\n001, q ,alpha beta gamma delta epsilon,,,x,-1\n002,q,alpha beta gamma delta epsilon,,,y,-2\n003,other,30 days,14 days,14 days,z,-3\n004,empty,,,,w,-4\n"


def upload(client, content=CSV, threshold=None):
    data = {} if threshold is None else {"pass_threshold": threshold}
    return client.post("/evaluate/batch", files={"file": ("input.csv", content, "text/csv")}, data=data)


def test_health_is_liveness_without_evaluator_construction(client, factory):
    assert client.get("/health").json() == {"status": "ok", "evaluator_version": "1.3.0"}
    factory.assert_not_called()


def test_default_app_probes_never_load_model():
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/capabilities").status_code == 200


def test_capabilities_expose_real_defaults(client, factory):
    response = client.get("/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_mode"] == "Offline Hybrid"
    assert body["evaluator_version"] == "1.3.0"
    assert body["configuration"] == {
        "default_pass_threshold": 70,
        "pass_threshold": {"minimum": 0, "maximum": 100, "inclusive": True},
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "metric_weights": {"correctness_score": .35, "relevance_score": .25, "groundedness_score": .25, "completeness_score": .15},
    }
    assert body["required_csv_columns"] == ["question", "answer"]
    assert body["optional_csv_columns"] == ["expected_answer", "context", "id"]
    assert body["result_columns"] == list(EXPORT_COLUMNS)
    assert body["offline_first"] and body["model_download_on_cache_miss"]
    assert body["single_evaluation"] and body["batch_csv_evaluation"]
    factory.assert_not_called()


@pytest.mark.parametrize("payload", [
    PAYLOAD,
    {"question": " query ", "answer": " " + ANSWER + " ", "expected_answer": " \t", "context": None},
    {"question": "duration?", "answer": "two weeks", "expected_answer": "14 days", "context": "14 days"},
    {"question": "duration?", "answer": "30 days", "expected_answer": "14 days", "context": "14 days"},
    {"question": ANSWER, "answer": ANSWER},
    {"question": "query", "answer": "N/A"},
    {"question": "query", "answer": "I cannot answer that request."},
    {"question": "query", "answer": "this response has unusual punctuation!!!!"},
    {"question": "query", "answer": ""},
    {"question": None, "answer": None},
    {"question": "", "answer": ANSWER},
    {"question": "query", "answer": "", "expected_answer": "reference", "context": "source"},
])
def test_single_output_matches_existing_evaluator_exactly(client, scorer, payload):
    expected = OfflineHybridEvaluator(scorer).evaluate(**payload).to_dict()
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    assert response.json() == expected
    assert list(response.json()) == list(EXPORT_COLUMNS)


@pytest.mark.parametrize("threshold,status", [(0, "Pass"), (80, "Pass"), (80.0, "Pass"), (80.01, "Fail"), (100, "Fail"), (100.0, "Fail")])
def test_threshold_boundary_and_exact_feedback(client, scorer, threshold, status):
    response = client.post("/evaluate", json={**PAYLOAD, "pass_threshold": threshold})
    expected = OfflineHybridEvaluator(scorer, threshold).evaluate(**PAYLOAD).to_dict()
    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["status"] == status


def test_thresholds_do_not_leak_between_requests(client):
    assert client.post("/evaluate", json={**PAYLOAD, "pass_threshold": 100}).json()["status"] == "Fail"
    assert client.post("/evaluate", json=PAYLOAD).json()["status"] == "Pass"


@pytest.mark.parametrize("payload", [
    {}, {"question": "query"}, {"answer": ANSWER},
    {**PAYLOAD, "question": 123}, {**PAYLOAD, "answer": False},
    {**PAYLOAD, "expected_answer": []}, {**PAYLOAD, "context": {}},
    {**PAYLOAD, "pass_threshold": -1}, {**PAYLOAD, "pass_threshold": 101},
    {**PAYLOAD, "pass_threshold": "80"}, {**PAYLOAD, "pass_threshold": True},
    {**PAYLOAD, "pass_threshold": None}, {**PAYLOAD, "unexpected": "value"},
    [], "not an object",
])
def test_malformed_single_requests_are_structured(client, factory, payload):
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["details"]["issues"]
    factory.assert_not_called()


@pytest.mark.parametrize("body", [b'{"question":', b'{"question":"q","answer":"a","pass_threshold":NaN}', b'{"question":"q","answer":"a","pass_threshold":Infinity}', b"\xff"])
def test_malformed_json_and_nonfinite_numbers(client, factory, body):
    response = client.post("/evaluate", content=body, headers={"content-type": "application/json"})
    assert response.status_code in (400, 422)
    assert "error" in response.json()
    factory.assert_not_called()


def test_validation_error_does_not_echo_inputs_or_unknown_keys(client):
    private_path = "C:/private/model/secret.bin"
    response = client.post("/evaluate", json={**PAYLOAD, private_path: private_path, "context": {"path": private_path}})
    assert response.status_code == 422
    assert private_path not in response.text
    assert "Traceback" not in response.text


def test_batch_matches_existing_rows_csv_order_validation_and_summary(client, scorer):
    validation = validate_dataframe(read_csv_bytes(CSV))
    original = evaluate_batch(validation.valid_data, OfflineHybridEvaluator(scorer))
    export = prepare_export(original)
    response = upload(client)
    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == list(export.columns)
    expected_rows = export.astype(object).where(pd.notna(export), None).to_dict("records")
    assert body["rows"] == expected_rows
    assert list(body["rows"][0]) == body["columns"]
    assert body["evaluated_csv"].encode("utf-8") == to_csv_bytes(original)
    assert body["summary"] == summarize_results(original)
    assert body["validation"] == {
        "total_rows": 4, "valid_rows": 2, "invalid_rows": 2,
        "empty_required_values": 1, "duplicate_rows": 1,
        "missing_required_columns": [], "can_evaluate": True,
    }
    assert [row["_validation_error"] for row in body["invalid_rows"]] == ["Duplicate row", "Empty required value(s): answer"]
    assert body["rows"][0]["id"] == 1  # Preserve pandas numeric inference.
    assert body["rows"][0]["question"] == " q "
    assert body["rows"][0]["correctness_score"] is None


@pytest.mark.parametrize("threshold", ["0", "80", "80.0", "80.01", "100", "100.0", "8e1"])
def test_batch_threshold_preserves_numeric_representation(client, scorer, threshold):
    response = upload(client, threshold=threshold)
    assert response.status_code == 200
    validation = validate_dataframe(read_csv_bytes(CSV))
    expected = evaluate_batch(validation.valid_data, OfflineHybridEvaluator(scorer, json.loads(threshold)))
    assert response.json()["evaluated_csv"].encode("utf-8") == to_csv_bytes(expected)


@pytest.mark.parametrize("threshold", ["-1", "101", "NaN", "Infinity", "true", "null", '"80"', "[]", "wrong"])
def test_invalid_batch_threshold(client, factory, threshold):
    response = upload(client, threshold=threshold)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    factory.assert_not_called()


@pytest.mark.parametrize("csv,code", [
    (b"question\nq\n", "missing_csv_columns"),
    (b"extra\nx\n", "missing_csv_columns"),
    (b"question,answer\n", "no_valid_rows"),
    (b"question,answer\nq,\n", "no_valid_rows"),
    (b"", "invalid_csv"),
    (b'question,answer\nq,"unterminated', "invalid_csv"),
    (b"question,answer\nq,\xff", "invalid_csv"),
    (b"Question, question ,answer\nq,q,a\n", "invalid_csv_schema"),
])
def test_invalid_batch_inputs(client, factory, csv, code):
    response = upload(client, csv)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert "Traceback" not in response.text
    factory.assert_not_called()


def test_missing_csv_columns_details(client):
    response = upload(client, b"question\nq\n")
    details = response.json()["error"]["details"]
    assert details["missing_required_columns"] == ["answer"]
    assert details["total_rows"] == details["invalid_rows"] == 1
    assert details["valid_rows"] == 0


def test_literal_placeholders_are_evaluated(client):
    response = upload(client, b"question,answer\nq1,N/A\nq2,NA\nq3,None\nq4,\n")
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [row["answer"] for row in rows] == ["N/A", "NA", "None"]
    assert [row["error_type"] for row in rows] == ["Insufficient Data"] * 3
    assert response.json()["validation"]["invalid_rows"] == 1


def test_json_nonfinite_values_are_null_but_csv_unchanged(client, scorer):
    csv = b"question,answer,extra\nq,alpha beta gamma delta epsilon,inf\n"
    response = upload(client, csv)
    assert response.status_code == 200
    assert response.json()["rows"][0]["extra"] is None
    expected = evaluate_batch(validate_dataframe(read_csv_bytes(csv)).valid_data, OfflineHybridEvaluator(scorer))
    assert response.json()["evaluated_csv"].encode() == to_csv_bytes(expected)


def test_csv_unicode_commas_newlines_and_duplicate_header_mangling(client):
    csv = 'question,answer,extra,extra\nq,alpha beta gamma delta epsilon,"é,quoted","line\nbreak"\n'.encode()
    response = upload(client, csv)
    assert response.status_code == 200
    body = response.json()
    assert body["columns"][:4] == ["question", "answer", "extra", "extra.1"]
    assert body["rows"][0]["extra"] == "é,quoted"
    decoded = pd.read_csv(BytesIO(body["evaluated_csv"].encode()))
    assert decoded.loc[0, "extra.1"] == "line\nbreak"


def test_missing_upload_and_malformed_multipart(client, factory):
    assert client.post("/evaluate/batch").status_code == 422
    response = client.post("/evaluate/batch", content=b"broken", headers={"content-type": "multipart/form-data"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "http_error"
    factory.assert_not_called()


@pytest.mark.parametrize("batch", [False, True])
def test_evaluator_failure_is_safe_and_has_no_partial_results(client, scorer, batch):
    scorer.similarity.side_effect = RuntimeError("Traceback at C:/private/model.bin: secret")
    response = upload(client) if batch else client.post("/evaluate", json=PAYLOAD)
    assert response.status_code == 503
    assert response.json() == {"error": {
        "code": "evaluation_failed", "message": "The local evaluator could not complete the evaluation.", "details": {},
    }}


def test_unexpected_failure_is_safe(client, service, monkeypatch):
    def fail():
        raise RuntimeError("C:/private/config secret")
    monkeypatch.setattr(service, "capabilities", fail)
    response = client.get("/capabilities")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "The request could not be completed.", "details": {}}}


def test_openapi_documents_nullable_result_and_batch_upload(client):
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {"/health", "/capabilities", "/evaluate", "/evaluate/batch"}
    result = schema["components"]["schemas"]["EvaluationResult"]
    assert {"type": "null"} in result["properties"]["correctness_score"]["anyOf"]
    request = schema["components"]["schemas"]["EvaluationRequest"]
    assert request["required"] == ["question", "answer"]
    assert "multipart/form-data" in schema["paths"]["/evaluate/batch"]["post"]["requestBody"]["content"]
