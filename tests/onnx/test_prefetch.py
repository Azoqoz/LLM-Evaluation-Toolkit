"""Build artifact selection is pinned and never requests quantized models."""

from unittest.mock import Mock

from src.application import prefetch_onnx
from src.config.model_cache import ONNX_ARTIFACTS, ONNX_REVISION
from src.config.settings import DEFAULT_MODEL_NAME


def test_prefetch_downloads_only_matching_official_artifacts(tmp_path, monkeypatch):
    import huggingface_hub
    from src.evaluators import onnx_embeddings

    def download(model, filename, **kwargs):
        assert model == DEFAULT_MODEL_NAME
        assert kwargs == {"revision": ONNX_REVISION, "local_dir": str(tmp_path)}
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test artifact")
    downloader = Mock(side_effect=download)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", downloader)
    model = Mock()
    model.encode.return_value.shape = (1, 384)
    monkeypatch.setattr(onnx_embeddings, "OnnxEmbeddingModel", Mock(return_value=model))
    monkeypatch.setattr(prefetch_onnx, "ONNX_CACHE_PATH", tmp_path)
    prefetch_onnx.prefetch()
    assert downloader.call_count == len(ONNX_ARTIFACTS)
    assert [name for name in ONNX_ARTIFACTS if name.endswith(".onnx")] == ["onnx/model.onnx"]
    assert (tmp_path / "manifest.json").exists()
