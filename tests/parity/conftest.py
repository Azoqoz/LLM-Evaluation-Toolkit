"""Keep parity tests offline; freeze only nondeterministic boundaries."""

from datetime import datetime, timezone

import pytest

from src.evaluators import hybrid, semantic


@pytest.fixture(autouse=True)
def offline_clock(monkeypatch):
    class FrozenDatetime:
        @classmethod
        def now(cls, tz):
            assert tz is timezone.utc
            return datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    def forbid_model_load(*args, **kwargs):
        raise AssertionError("Parity tests must not load/download real model weights")

    monkeypatch.setattr(hybrid, "datetime", FrozenDatetime)
    monkeypatch.setattr(semantic, "_load_model", forbid_model_load)


class RecordingScorer:
    def __init__(self, score=80):
        self.score = score
        self.calls = []

    def similarity(self, left, right):
        self.calls.append((left, right))
        return self.score


@pytest.fixture
def scorer():
    return RecordingScorer()
