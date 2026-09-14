"""Real-model checks are offline and opt in to cached build artifacts."""

import os
import importlib
from datetime import datetime, timezone

import pytest

from src.config.model_cache import MODEL_CACHE_PATH, ONNX_CACHE_PATH


def optional_dependency(name):
    if os.getenv("REQUIRE_ONNX_PARITY") == "1":
        return importlib.import_module(name)
    return pytest.importorskip(name)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    from src.evaluators import hybrid

    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 1, 2, tzinfo=timezone.utc)
    monkeypatch.setattr(hybrid, "datetime", Clock)


@pytest.fixture(scope="session")
def onnx_model():
    if not (ONNX_CACHE_PATH / "onnx/model.onnx").exists():
        if os.getenv("REQUIRE_ONNX_PARITY") == "1":
            pytest.fail("Prefetch ONNX artifacts before required parity tests")
        pytest.skip("Run python -m src.application.prefetch_onnx for real-model tests")
    optional_dependency("onnxruntime")
    from src.evaluators.onnx_embeddings import OnnxEmbeddingModel
    return OnnxEmbeddingModel()


@pytest.fixture(scope="session")
def reference_model():
    if not MODEL_CACHE_PATH.exists():
        if os.getenv("REQUIRE_ONNX_PARITY") == "1":
            pytest.fail("Prefetch the local SentenceTransformer reference first")
        pytest.skip("Local SentenceTransformer reference artifact is not cached")
    sentence_transformers = optional_dependency("sentence_transformers")
    return sentence_transformers.SentenceTransformer(str(MODEL_CACHE_PATH), local_files_only=True)
