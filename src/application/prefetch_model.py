"""Render build step: python -m src.application.prefetch_model."""

from src.config.model_cache import MODEL_CACHE_PATH
from src.config.settings import DEFAULT_MODEL_NAME


def prefetch() -> None:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(DEFAULT_MODEL_NAME)
    MODEL_CACHE_PATH.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_CACHE_PATH))
    # Fail the build if the saved artifact cannot load and run without download.
    cached = SentenceTransformer(str(MODEL_CACHE_PATH), local_files_only=True)
    cached.encode(["Evaluator warmup."], normalize_embeddings=True)


if __name__ == "__main__":
    prefetch()
    print("Evaluator model prefetched and verified.")
