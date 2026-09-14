"""ONNX mode selection and isolated startup without heavyweight imports."""

import os
import subprocess
import sys
from unittest.mock import Mock

from src.application.service import EvaluationService
from src.evaluators.embedding_backend import create_semantic_scorer
from src.evaluators.semantic import SentenceTransformerScorer


def test_local_keeps_lazy_sentence_transformer(monkeypatch):
    from src.evaluators import semantic
    loader = Mock()
    monkeypatch.setattr(semantic, "_load_model", loader)
    scorer = create_semantic_scorer("local")
    assert isinstance(scorer, SentenceTransformerScorer)
    assert scorer._model is None
    loader.assert_not_called()


def test_demo_selects_onnx_and_initializes_only_once(monkeypatch):
    from src.evaluators import onnx_embeddings
    model = Mock()
    factory = Mock(return_value=model)
    monkeypatch.setattr(onnx_embeddings, "OnnxEmbeddingModel", factory)
    service = EvaluationService(app_mode="demo")
    assert service.readiness() == {"status": "warming"}
    service.initialize()
    service.initialize()
    assert service.readiness() == {"status": "ready"}
    factory.assert_called_once_with()
    model.encode.assert_called_once_with(["Evaluator warmup."], normalize_embeddings=True)


def test_real_api_startup_and_benchmark_never_import_heavy_packages(onnx_model):
    script = """
import importlib.abc, sys
class NoHeavy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'sentence_transformers', 'transformers'}:
            raise AssertionError('Forbidden production import: ' + fullname)
sys.meta_path.insert(0, NoHeavy())
from threading import Event
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.application.service import EvaluationService
from src.evaluators.embedding_backend import create_semantic_scorer
from src.evaluators.hybrid import OfflineHybridEvaluator
entered, release = Event(), Event()
def factory(threshold):
    entered.set()
    assert release.wait(10)
    return OfflineHybridEvaluator(create_semantic_scorer('demo'), threshold)
service = EvaluationService(factory, app_mode='demo')
with TestClient(create_app(service)) as client:
    assert entered.wait(5)
    assert client.get('/health').status_code == 200
    assert client.get('/ready').json() == {'status':'warming'}
    assert client.post('/evaluate', json={'question':'q','answer':'a'}).status_code == 503
    release.set()
    assert service._initialization_finished.wait(30)
    assert client.get('/ready').json() == {'status':'ready'}
    assert client.post('/evaluate', json={'question':'q','answer':'a'}).status_code == 200
    response = client.post('/evaluate/benchmark')
    assert response.status_code == 200
    assert len(response.json()['rows']) == 100
assert not {'torch','sentence_transformers','transformers'}.intersection(sys.modules)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60,
        env={**os.environ, "APP_MODE": "demo", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    )
    assert completed.returncode == 0, completed.stderr
