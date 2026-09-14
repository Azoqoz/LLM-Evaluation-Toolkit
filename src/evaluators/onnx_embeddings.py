"""Local-only float32 MiniLM embeddings; no Torch/Transformers imports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.config.model_cache import ONNX_CACHE_PATH


def mean_pool_and_normalize(hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Match the model's attention-mask mean pooling and Normalize module."""
    hidden = np.asarray(hidden, dtype=np.float32)
    weights = np.asarray(mask, dtype=np.float32)[..., None]
    pooled = (hidden * weights).sum(axis=1) / np.maximum(weights.sum(axis=1), np.float32(1e-9))
    return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), np.float32(1e-12))


class OnnxEmbeddingModel:
    """Small encode-compatible backend, initialized only by service warm-up."""

    def __init__(self, cache_path: Path = ONNX_CACHE_PATH):
        # These packages are imported only when Demo startup constructs a model.
        import onnxruntime as ort
        from tokenizers import Tokenizer

        config = json.loads((cache_path / "sentence_bert_config.json").read_text())
        self.max_seq_length = config["max_seq_length"]
        if self.max_seq_length != 256:
            raise ValueError("Unexpected MiniLM sequence length")
        self.tokenizer = Tokenizer.from_file(str(cache_path / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=self.max_seq_length, direction="right")
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", direction="right")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.add_session_config_entry("session.disable_prepacking", "1")
        self.session = ort.InferenceSession(
            str(cache_path / "onnx" / "model.onnx"),
            sess_options=options, providers=["CPUExecutionProvider"],
        )
        self.input_names = {value.name for value in self.session.get_inputs()}

    def tokenize(self, texts: list[str]) -> dict[str, np.ndarray]:
        encodings = self.tokenizer.encode_batch([text.strip() for text in texts])
        return {
            "input_ids": np.asarray([value.ids for value in encodings], dtype=np.int64),
            "attention_mask": np.asarray([value.attention_mask for value in encodings], dtype=np.int64),
            "token_type_ids": np.asarray([value.type_ids for value in encodings], dtype=np.int64),
        }

    def encode(self, texts: list[str], normalize_embeddings: bool = False) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        results = []
        # The evaluator compares pairs. Bound tensor memory even for diagnostic
        # callers encoding a larger collection; this does not truncate rows.
        for start in range(0, len(texts), 2):
            tokens = self.tokenize(texts[start:start + 2])
            hidden = self.session.run(None, {key: value for key, value in tokens.items() if key in self.input_names})[0]
            if hidden.dtype != np.float32 or hidden.ndim != 3 or hidden.shape[-1] != 384:
                raise ValueError("Unexpected MiniLM output")
            embeddings = mean_pool_and_normalize(hidden, tokens["attention_mask"])
            if normalize_embeddings:
                # SentenceTransformer has both a Normalize module and the
                # encode(normalize_embeddings=True) normalization.
                embeddings /= np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), np.float32(1e-12))
            results.append(embeddings)
        return np.concatenate(results, axis=0)
