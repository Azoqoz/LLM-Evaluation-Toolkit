"""Lock rule boundaries, classification priority, and embedding plumbing."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.evaluators import semantic
from src.evaluators.contradictions import detect_contradictions
from src.evaluators.rules import RuleFindings, evaluate_rules
from src.scoring.classification import classify_error, classify_threshold_failure
from src.reporting.feedback import generate_feedback


# Capture the actual cached loader before the offline fixture guards it.
MODEL_LOADER = semantic._load_model


@pytest.mark.parametrize("scores,error", [
    ((34.99, 80, 80, 80), "Irrelevant Answer"),
    ((35, 80, 80, 80), "No Error"),
    ((80, 29.99, 80, 80), "Contradictory Answer"),
    ((80, 30, 80, 80), "Incorrect Answer"),
    ((80, 54.99, 80, 80), "Incorrect Answer"),
    ((80, 55, 80, 80), "No Error"),
    ((80, 80, 49.99, 80), "Unsupported Answer"),
    ((80, 80, 50, 80), "No Error"),
    ((80, 80, 80, 54.99), "Incomplete Answer"),
    ((80, 80, 80, 55), "No Error"),
    ((None, None, None, None), "No Error"),
])
def test_classification_cutoffs(scores, error):
    assert classify_error(RuleFindings(), *scores) == error


@pytest.mark.parametrize("flags,contradiction,error", [
    ({"empty": True, "placeholder": True}, True, "Empty Answer"),
    ({"placeholder": True, "unwanted_refusal": True}, True, "Insufficient Data"),
    ({"unwanted_refusal": True, "question_repetition": True}, True, "Unwanted Refusal"),
    ({"question_repetition": True}, True, "Incomplete Answer"),
    ({"formatting_problem": True}, True, "Contradictory Answer"),
    ({"formatting_problem": True, "excessively_verbose": True}, False, "Formatting Issue"),
    ({"excessively_verbose": True}, False, "Overly Verbose"),
    ({}, False, "Irrelevant Answer"),
])
def test_priority_over_other_rules_and_low_metrics(flags, contradiction, error):
    assert classify_error(RuleFindings(**flags), 0, 0, 0, 0, contradiction) == error


@pytest.mark.parametrize("flags,penalty", [
    ({"empty": True}, 100), ({"extremely_short": True}, 45),
    ({"question_repetition": True}, 80), ({"excessive_repetition": True}, 25),
    ({"placeholder": True}, 65), ({"unwanted_refusal": True}, 45),
    ({"excessively_verbose": True}, 15), ({"formatting_problem": True}, 10),
    ({"placeholder": True, "extremely_short": True}, 100),
])
def test_penalties(flags, penalty):
    assert RuleFindings(**flags).penalty == penalty


@pytest.mark.parametrize("answer,flag,expected", [
    ("a b c d", "extremely_short", True), ("a b c d e", "extremely_short", False),
    ("", "extremely_short", False), ("N/A", "placeholder", True),
    ("unknown!", "placeholder", True), ("unknown value", "placeholder", False),
    ("as an AI I can help", "unwanted_refusal", True),
    ("yes!!!", "formatting_problem", False), ("yes!!!!", "formatting_problem", True),
    ("x" * 500, "formatting_problem", False), ("x" * 501, "formatting_problem", True),
    ("same. same.", "excessive_repetition", False),
    ("same. same. same.", "excessive_repetition", True),
    ("word " * 11, "excessive_repetition", False),
    ("word " * 12, "excessive_repetition", True),
])
def test_rule_detection_boundaries(answer, flag, expected):
    assert getattr(evaluate_rules("query", answer), flag) is expected


@pytest.mark.parametrize("question,count,expected", [("", 350, False), ("", 351, True), ("q", 160, False), ("q", 161, True), ("a b c d e f", 180, False), ("a b c d e f", 181, True)])
def test_verbosity_limits(question, count, expected):
    assert evaluate_rules(question, "word " * count).excessively_verbose is expected


def test_threshold_tie_order_and_missing_fallback():
    scores = {"completeness_score": 80, "groundedness_score": 80, "correctness_score": 80, "relevance_score": 80}
    for metric, error in [("relevance_score", "Irrelevant Answer"), ("correctness_score", "Incorrect Answer"), ("groundedness_score", "Unsupported Answer"), ("completeness_score", "Incomplete Answer")]:
        assert classify_threshold_failure(scores) == (error, metric, 80.0)
        del scores[metric]
    assert classify_threshold_failure({}) == ("Incomplete Answer", "completeness_score", 0.0)


@pytest.mark.parametrize("cosine,expected", [(-1, 0), (0, 0), (0.123456, 12.35), (1, 100), (2, 100)])
def test_embedding_dot_product_clamp_and_round(cosine, expected):
    model = Mock()
    model.encode.return_value = [[1, 0], [cosine, 0]]
    scorer = semantic.SentenceTransformerScorer(model=model)
    assert scorer.similarity(" left ", "right") == expected
    model.encode.assert_called_once_with([" left ", "right"], normalize_embeddings=True)


@pytest.mark.parametrize("left,right", [("", "x"), ("x", " \t"), (None, "x")])
def test_blank_semantic_input_never_loads_model(left, right):
    assert semantic.SentenceTransformerScorer().similarity(left, right) == 0


def test_loader_local_first_fallback_and_cache(monkeypatch):
    model = Mock()
    constructor = Mock(side_effect=[OSError("cache miss"), model])
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    MODEL_LOADER.cache_clear()
    try:
        assert MODEL_LOADER("parity-model") is model
        assert MODEL_LOADER("parity-model") is model
        assert constructor.call_args_list == [(("parity-model",), {"local_files_only": True}), (("parity-model",), {})]
        assert MODEL_LOADER.cache_info().maxsize == 2
    finally:
        MODEL_LOADER.cache_clear()


def test_loader_does_not_retry_other_errors(monkeypatch):
    constructor = Mock(side_effect=RuntimeError("broken model"))
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    MODEL_LOADER.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="broken model"):
            MODEL_LOADER("parity-model")
        assert constructor.call_count == 1
    finally:
        MODEL_LOADER.cache_clear()


def test_lazy_instance_loading(monkeypatch):
    model = Mock()
    model.encode.return_value = [[1, 0], [1, 0]]
    loader = Mock(return_value=model)
    monkeypatch.setattr(semantic, "_load_model", loader)
    scorer = semantic.SentenceTransformerScorer()
    loader.assert_not_called()
    assert scorer.similarity("a", "b") == scorer.similarity("c", "d") == 100
    loader.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")


def test_local_cache_hit_never_uses_download_fallback(monkeypatch):
    model = Mock()
    constructor = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=constructor))
    MODEL_LOADER.cache_clear()
    try:
        assert MODEL_LOADER("cached-model") is model
        constructor.assert_called_once_with("cached-model", local_files_only=True)
    finally:
        MODEL_LOADER.cache_clear()


@pytest.mark.parametrize("answer,reference,conflict,equivalent", [
    ("14 days or 30 days", "14 days", False, False),
    ("one month", "30 days", True, False),
    # Uppercase unit abbreviations also become conflicting named entities.
    ("1 GB", "1024 MB", True, True),
    ("1 gb", "1024 mb", False, True),
    ("0 celsius", "32 fahrenheit", True, False),
    ("0.5", "50%", False, True),
    ("2026-02-31", "February 31, 2026", False, True),
])
def test_fact_normalization_current_limits(answer, reference, conflict, equivalent):
    result = detect_contradictions(answer, reference)
    assert result.detected is conflict
    assert bool(result.expected_equivalences) is equivalent


@pytest.mark.parametrize("error,message", [
    ("Irrelevant Answer", "Revise the answer so it directly addresses the question."),
    ("Incorrect Answer", "The answer does not closely match the expected answer; review the key claims and missing details."),
    ("Incomplete Answer", "Expand the answer with the essential details needed to resolve the question."),
    ("Unsupported Answer", "The groundedness estimate is low. Remove unsupported claims or connect them more clearly to the supplied context."),
    ("Contradictory Answer", "The answer strongly conflicts with the expected answer. Recheck its central claim."),
    ("Overly Verbose", "Make the answer more concise while preserving the information needed to answer the question."),
    ("Unwanted Refusal", "Answer the request directly when it is safe and possible instead of using a generic refusal."),
    ("Formatting Issue", "Improve readability by using normal capitalization, punctuation, and shorter lines."),
    ("Insufficient Data", "Replace placeholder text with a complete, meaningful answer."),
])
def test_exact_error_feedback(error, message):
    assert generate_feedback(error, {"correctness_score": 0, "groundedness_score": 0}) == message + " These local semantic and rule-based checks are estimates, not a guarantee of factual correctness."
