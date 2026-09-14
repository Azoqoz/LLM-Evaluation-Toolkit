"""Cache selection and build verification without weights or network."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.evaluators import semantic
from src.application import prefetch_model
from src.config.settings import DEFAULT_MODEL_NAME

LOADER = semantic._load_model


@pytest.mark.parametrize("broken", [False, True])
def test_prefetched_artifact_is_local_only_even_when_broken(tmp_path, monkeypatch, broken):
    constructor = Mock(side_effect=OSError("broken artifact") if broken else None)
    monkeypatch.setattr(semantic, "MODEL_CACHE_PATH", tmp_path)
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    LOADER.cache_clear()
    try:
        if broken:
            with pytest.raises(OSError):
                LOADER(DEFAULT_MODEL_NAME)
        else:
            assert LOADER(DEFAULT_MODEL_NAME) is constructor.return_value
        constructor.assert_called_once_with(str(tmp_path), local_files_only=True)
    finally:
        LOADER.cache_clear()


def test_prefetch_saves_exact_model_and_verifies_local_forward_pass(tmp_path, monkeypatch):
    downloaded, local = Mock(), Mock()
    constructor = Mock(side_effect=[downloaded, local])
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    monkeypatch.setattr(prefetch_model, "MODEL_CACHE_PATH", tmp_path / "model")
    prefetch_model.prefetch()
    assert constructor.call_args_list[0].args == (DEFAULT_MODEL_NAME,)
    downloaded.save.assert_called_once_with(str(tmp_path / "model"))
    assert constructor.call_args_list[1].kwargs == {"local_files_only": True}
    local.encode.assert_called_once_with(["Evaluator warmup."], normalize_embeddings=True)
