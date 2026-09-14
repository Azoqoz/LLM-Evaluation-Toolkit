"""Mode policy and fixed benchmark through the real pipeline (only embeddings mocked)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.application.service import ApplicationError, EvaluationService
from src.config.settings import EXPORT_COLUMNS
from src.ingestion.csv_validator import read_csv_bytes, validate_dataframe


@pytest.mark.parametrize("mode,expected", [(None, "local"), ("local", "local"), ("demo", "demo"), (" DEMO ", "demo"), ("other", "local")])
def test_environment_mode(monkeypatch, mode, expected):
    monkeypatch.delenv("APP_MODE", raising=False)
    if mode is not None:
        monkeypatch.setenv("APP_MODE", mode)
    assert EvaluationService().capabilities()["app_mode"] == expected


@pytest.mark.parametrize("mode", ["demo", "local"])
def test_mode_capabilities(factory, mode):
    with TestClient(create_app(ready_service(factory, app_mode=mode))) as client:
        body = client.get("/capabilities").json()
    assert body["app_mode"] == mode
    assert body["csv_upload_allowed"] is (mode == "local")
    assert body["threshold_editable"] is (mode == "local")
    assert body["demo_pass_threshold"] == 70
    assert body["benchmark"] == {"id": "evalroom-100-v1", "title": "Demo Benchmark", "row_count": 100}


def test_demo_single_is_real_and_threshold_is_fixed(factory, scorer):
    service = ready_service(factory, app_mode="demo")
    with TestClient(create_app(service)) as client:
        result = client.post("/evaluate", json={"question": "query", "answer": "alpha beta gamma delta epsilon"})
        assert result.status_code == 200
        assert result.json()["quality_score"] == 80
        assert scorer.similarity.called
        denied = client.post("/evaluate", json={"question": "q", "answer": "a", "pass_threshold": 0})
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "demo_restricted"


def test_demo_upload_rejected_before_multipart_parsing(factory, monkeypatch):
    from starlette.requests import Request
    async def forbid_form(*args, **kwargs):
        raise AssertionError("A demo upload must never be parsed")
    monkeypatch.setattr(Request, "_get_form", forbid_form)
    service = ready_service(factory, app_mode="demo")
    with TestClient(create_app(service)) as client:
        for path in ["/evaluate/batch", "/evaluate/batch/"]:
            response = client.post(path, files={"file": ("replacement.csv", b"question,answer\nq,a\n")})
            assert response.status_code == 403
    factory.assert_not_called()
    with pytest.raises(ApplicationError, match="Local Mode"):
        service.evaluate_csv(b"question,answer\nq,a\n")


def test_fixed_benchmark_is_valid_diverse_and_exactly_100_rows():
    path = Path(__file__).resolve().parents[2] / "data" / "demo_benchmark.csv"
    validation = validate_dataframe(read_csv_bytes(path.read_bytes()))
    assert (validation.total_rows, validation.valid_rows, validation.invalid_rows) == (100, 100, 0)
    assert validation.valid_data.id.nunique() == 100
    assert validation.valid_data.topic.nunique() == 20
    assert set(validation.valid_data.difficulty) == {"easy", "medium", "hard"}
    assert validation.valid_data.response_style.value_counts().to_dict() == dict.fromkeys(["reference", "paraphrase", "conflict", "incomplete", "off_topic"], 20)


def test_demo_benchmark_evaluates_every_row_and_keeps_schema(factory, scorer):
    service = ready_service(factory, app_mode="demo")
    with TestClient(create_app(service)) as client:
        response = client.post("/evaluate/benchmark")
        assert response.status_code == 200
        body = response.json()
        assert len(body["rows"]) == body["summary"]["total"] == 100
        assert body["validation"]["valid_rows"] == 100
        assert body["columns"][-len(EXPORT_COLUMNS):] == list(EXPORT_COLUMNS)
        assert {row["status"] for row in body["rows"]} == {"Pass", "Fail"}
        assert len({row["error_type"] for row in body["rows"]}) >= 4
        assert len(read_csv_bytes(body["evaluated_csv"].encode())) == 100
        assert scorer.similarity.call_count == 300
        for body_override in [{"file": "replacement.csv"}, {"pass_threshold": 0}, {"path": "C:/private/file.csv"}]:
            assert client.post("/evaluate/benchmark", json=body_override).status_code == 422


def test_local_upload_remains_available(factory):
    with TestClient(create_app(ready_service(factory, app_mode="local"))) as client:
        response = client.post("/evaluate/batch", files={"file": ("cases.csv", b"question,answer\nq,alpha beta gamma delta epsilon\n")}, data={"pass_threshold": "80.01"})
        assert response.status_code == 200
        assert response.json()["rows"][0]["status"] == "Fail"


def ready_service(factory, app_mode):
    service = EvaluationService(factory, app_mode=app_mode)
    service.initialize()
    assert service.readiness() == {"status": "ready"}
    factory.reset_mock()
    return service