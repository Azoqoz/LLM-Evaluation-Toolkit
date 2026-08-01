"""Local sentence-transformer semantic similarity."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol

import numpy as np

from src.config.settings import DEFAULT_MODEL_NAME


class SemanticScorer(Protocol):
    """Protocol used by the hybrid evaluator for testable semantic scoring."""

    def similarity(self, left: str, right: str) -> float:
        """Return a similarity score from 0 to 100."""


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> Any:
    """Load from the local cache first, downloading only when absent."""

    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except OSError:
        return SentenceTransformer(model_name)


class SentenceTransformerScorer:
    """Cosine similarity backed by a lazily loaded local embedding model."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, model: Any | None = None) -> None:
        self.model_name = model_name
        self._model = model

    @property
    def model(self) -> Any:
        """Return the injected model or load the configured model once."""

        if self._model is None:
            self._model = _load_model(self.model_name)
        return self._model

    def similarity(self, left: str, right: str) -> float:
        """Return cosine similarity mapped to the intuitive 0–100 range."""

        if not (left or "").strip() or not (right or "").strip():
            return 0.0
        embeddings = np.asarray(
            self.model.encode([left, right], normalize_embeddings=True),
            dtype=float,
        )
        cosine = float(np.dot(embeddings[0], embeddings[1]))
        return round(max(0.0, min(100.0, cosine * 100.0)), 2)
