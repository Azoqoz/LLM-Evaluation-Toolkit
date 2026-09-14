"""Render build: download the official unquantized ONNX artifact, no Torch."""

import hashlib
import json

from src.config.model_cache import ONNX_ARTIFACTS, ONNX_CACHE_PATH, ONNX_REVISION
from src.config.settings import DEFAULT_MODEL_NAME


def prefetch() -> None:
    from huggingface_hub import hf_hub_download
    from src.evaluators.onnx_embeddings import OnnxEmbeddingModel

    for filename in ONNX_ARTIFACTS:
        hf_hub_download(DEFAULT_MODEL_NAME, filename, revision=ONNX_REVISION,
                        local_dir=str(ONNX_CACHE_PATH))
    # Parse/load and run the actual model locally; failure fails the build.
    model = OnnxEmbeddingModel(ONNX_CACHE_PATH)
    assert model.encode(["Evaluator warmup."], normalize_embeddings=True).shape == (1, 384)
    checksums = {}
    for filename in ONNX_ARTIFACTS:
        with (ONNX_CACHE_PATH / filename).open("rb") as stream:
            checksums[filename] = hashlib.file_digest(stream, "sha256").hexdigest()
    (ONNX_CACHE_PATH / "manifest.json").write_text(json.dumps({
        "model": DEFAULT_MODEL_NAME, "revision": ONNX_REVISION,
        "precision": "float32", "sha256": checksums,
    }, indent=2))


if __name__ == "__main__":
    prefetch()
    print("Full-precision ONNX model and tokenizer prefetched and verified.")
