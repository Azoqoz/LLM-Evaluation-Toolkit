"""Hybrid evaluation and scoring tests."""

import pytest

from src.evaluators.semantic import SentenceTransformerScorer
from src.evaluators.rules import evaluate_rules
from src.scoring.classification import classify_error, classify_threshold_failure
from src.scoring.quality import calculate_quality_score


class FakeEmbeddingModel:
    """Minimal model double for testing the cosine similarity path."""

    def encode(self, texts, normalize_embeddings=True):
        assert normalize_embeddings is True
        return [[1.0, 0.0], [0.6, 0.8]]


def test_empty_answer_is_detected(evaluator) -> None:
    result = evaluator.evaluate("What is RAG?", "")
    assert result.error_type == "Empty Answer"
    assert result.status == "Fail"


def test_semantic_scores_use_scorer(evaluator) -> None:
    result = evaluator.evaluate(
        "What is a vector database?",
        "A vector database stores vector embeddings for search.",
        "A vector database stores embeddings.",
        "Vector databases store embeddings and support similarity search.",
    )
    assert result.relevance_score > 0
    assert result.correctness_score > 0
    assert result.groundedness_score > 0


def test_sentence_transformer_cosine_mapping() -> None:
    scorer = SentenceTransformerScorer(model=FakeEmbeddingModel())
    assert scorer.similarity("first text", "second text") == 60.0


def test_optional_metrics_are_unavailable(evaluator) -> None:
    result = evaluator.evaluate(
        "Name a Python web framework.",
        "Streamlit is a Python framework for interactive data applications.",
    )
    assert result.correctness_score is None
    assert result.groundedness_score is None
    assert "Unavailable:" in result.improvement_feedback


def test_quality_score_normalizes_available_weights() -> None:
    quality = calculate_quality_score(
        {
            "correctness_score": None,
            "relevance_score": 80,
            "groundedness_score": None,
            "completeness_score": 60,
        }
    )
    assert quality == 72.5


def test_pass_fail_threshold(evaluator) -> None:
    evaluator.pass_threshold = 0
    passing = evaluator.evaluate(
        "Python lists store ordered values",
        "Python lists store ordered values in a mutable collection.",
    )
    assert passing.status == "Pass"
    assert passing.error_type == "No Error"

    evaluator.pass_threshold = 100
    failing = evaluator.evaluate(
        "Python lists store ordered values",
        "Python lists store ordered values in a mutable collection.",
    )
    assert failing.status == "Fail"
    assert failing.error_type != "No Error"
    assert "weakest available metric" in failing.improvement_feedback
    assert "configured pass threshold" in failing.improvement_feedback


@pytest.mark.parametrize(
    ("scores", "expected_error", "expected_metric"),
    [
        (
            {
                "relevance_score": 45.0,
                "correctness_score": 80.0,
                "groundedness_score": 80.0,
                "completeness_score": 80.0,
            },
            "Irrelevant Answer",
            "relevance_score",
        ),
        (
            {
                "relevance_score": 80.0,
                "correctness_score": 45.0,
                "groundedness_score": 80.0,
                "completeness_score": 80.0,
            },
            "Incorrect Answer",
            "correctness_score",
        ),
        (
            {
                "relevance_score": 80.0,
                "correctness_score": 80.0,
                "groundedness_score": 45.0,
                "completeness_score": 80.0,
            },
            "Unsupported Answer",
            "groundedness_score",
        ),
        (
            {
                "relevance_score": 80.0,
                "correctness_score": 80.0,
                "groundedness_score": 80.0,
                "completeness_score": 45.0,
            },
            "Incomplete Answer",
            "completeness_score",
        ),
    ],
)
def test_threshold_failure_uses_weakest_metric(
    scores, expected_error, expected_metric
) -> None:
    error_type, metric_name, metric_score = classify_threshold_failure(scores)
    assert error_type == expected_error
    assert metric_name == expected_metric
    assert metric_score == 45.0


def test_threshold_failure_ties_use_deterministic_metric_priority() -> None:
    error_type, metric_name, _ = classify_threshold_failure(
        {
            "relevance_score": 45.0,
            "correctness_score": 45.0,
            "groundedness_score": 45.0,
            "completeness_score": 45.0,
        }
    )
    assert error_type == "Irrelevant Answer"
    assert metric_name == "relevance_score"


def test_error_classification_is_deterministic() -> None:
    rules = evaluate_rules("Question?", "I cannot answer that request.")
    assert classify_error(rules, 80, None, None, 80) == "Unwanted Refusal"
