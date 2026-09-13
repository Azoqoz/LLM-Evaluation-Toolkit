"""Offline backend tests with the real evaluator and a deterministic scorer."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.application.service import EvaluationService
from src.evaluators import hybrid, semantic
from src.evaluators.hybrid import OfflineHybridEvaluator


@pytest.fixture(autouse=True)
def offline_clock(monkeypatch):
    class FrozenDatetime:
        @classmethod
        def now(cls, tz):
            assert tz is timezone.utc
            return datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    def forbid_model_load(*args, **kwargs):
        raise AssertionError("Backend tests must not load or download real model weights")

    monkeypatch.setattr(hybrid, "datetime", FrozenDatetime)
    monkeypatch.setattr(semantic, "_load_model", forbid_model_load)


@pytest.fixture
def scorer():
    return Mock(similarity=Mock(return_value=80.0))


@pytest.fixture
def factory(scorer):
    return Mock(side_effect=lambda threshold: OfflineHybridEvaluator(scorer, threshold))


@pytest.fixture
def service(factory):
    return EvaluationService(factory, app_mode="local")


@pytest.fixture
def client(service):
    with TestClient(create_app(service), raise_server_exceptions=False) as client:
        yield client
