"""Startup, readiness and exclusion of request-triggered initialization."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.application.service import ApplicationError, EvaluationService
from src.evaluators.hybrid import OfflineHybridEvaluator
from src.evaluators.semantic import SentenceTransformerScorer


def test_health_and_ready_during_background_warmup_then_evaluation(scorer):
    entered, release = Event(), Event()
    def make(threshold):
        entered.set()
        assert release.wait(5)
        return OfflineHybridEvaluator(scorer, threshold)
    factory = Mock(side_effect=make)
    service = EvaluationService(factory, app_mode="local")
    app = create_app(service)
    with TestClient(app) as client:
        try:
            assert entered.wait(2)
            assert client.get("/health").json() == {"status": "ok", "evaluator_version": "1.3.0"}
            assert client.get("/ready").json() == {"status": "warming"}
            for path in ["/evaluate", "/evaluate/benchmark", "/evaluate/batch"]:
                response = client.post(path, json={"question": "q", "answer": "a"})
                assert response.status_code == 503
                assert response.json()["error"]["code"] == "evaluator_warming"
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: service.initialize(), range(8)))
            factory.assert_called_once_with(70)
            scorer.similarity.assert_not_called()
        finally:
            release.set()
        assert service._initialization_finished.wait(2)
        assert client.get("/ready").json() == {"status": "ready"}
        assert client.get("/ready").headers["cache-control"] == "no-store"
        for threshold in [100, 0, 80.0, 80.01]:
            payload = {"question": "query", "answer": "alpha beta gamma delta epsilon"}
            response = client.post("/evaluate", json={**payload, "pass_threshold": threshold})
            assert response.status_code == 200
            assert response.json() == OfflineHybridEvaluator(scorer, threshold).evaluate(**payload).to_dict()
        factory.assert_called_once_with(70)


def test_requests_without_lifespan_cannot_initialize(factory):
    service = EvaluationService(factory)
    with pytest.raises(ApplicationError, match="Preparing"):
        service.evaluate(None, "")
    with pytest.raises(ApplicationError, match="Preparing"):
        service.evaluate_csv(b"question,answer\nq,a\n")
    # TestClient without context intentionally skips lifespan.
    client = TestClient(create_app(service))
    try:
        assert client.post("/evaluate", json={"question": "q", "answer": "a"}).status_code == 503
        assert client.get("/ready").json() == {"status": "warming"}
    finally:
        client.close()
    factory.assert_not_called()


def test_initialization_failure_is_terminal_and_safe():
    factory = Mock(side_effect=RuntimeError("Traceback C:/private/model.bin secret"))
    service = EvaluationService(factory)
    with TestClient(create_app(service)) as client:
        assert service._initialization_finished.wait(2)
        assert client.get("/health").status_code == 200
        assert client.get("/ready").json() == {
            "status": "error", "message": "Evaluator initialization failed.",
        }
        for _ in range(3):
            service.initialize()
            response = client.post("/evaluate", json={"question": "q", "answer": "a"})
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "evaluator_unavailable"
            assert "private" not in response.text and "Traceback" not in response.text
        factory.assert_called_once_with(70)


def test_real_scorer_forward_pass_finishes_before_ready(monkeypatch):
    from src.evaluators import semantic
    entered, release = Event(), Event()
    def encode(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return [[1.0, 0.0], [1.0, 0.0]]
    model = Mock(encode=Mock(side_effect=encode))
    loader = Mock(return_value=model)
    monkeypatch.setattr(semantic, "_load_model", loader)
    service = EvaluationService()
    with TestClient(create_app(service)) as client:
        try:
            assert entered.wait(2)
            assert client.get("/ready").json() == {"status": "warming"}
        finally:
            release.set()
        assert service._initialization_finished.wait(2)
        assert client.get("/ready").json() == {"status": "ready"}
        loader.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        model.encode.assert_called_once_with(["Evaluator warmup."], normalize_embeddings=True)
        response = client.post("/evaluate", json={"question": "q", "answer": "alpha beta gamma delta epsilon"})
        assert response.status_code == 200
        assert loader.call_count == 1


def test_forward_pass_failure_never_reports_ready():
    model = Mock(encode=Mock(side_effect=RuntimeError("private path")))
    factory = Mock(return_value=OfflineHybridEvaluator(SentenceTransformerScorer(model=model)))
    service = EvaluationService(factory)
    service.initialize()
    assert service.readiness()["status"] == "error"
    with pytest.raises(ApplicationError):
        service.evaluate("q", "a")
    model.encode.assert_called_once()
