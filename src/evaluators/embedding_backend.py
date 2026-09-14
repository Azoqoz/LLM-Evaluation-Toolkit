"""Select model execution without duplicating semantic/evaluator scoring."""

from src.evaluators.semantic import SentenceTransformerScorer


def create_semantic_scorer(app_mode: str) -> SentenceTransformerScorer:
    if app_mode == "demo":
        from src.evaluators.onnx_embeddings import OnnxEmbeddingModel

        return SentenceTransformerScorer(model=OnnxEmbeddingModel())
    return SentenceTransformerScorer()
