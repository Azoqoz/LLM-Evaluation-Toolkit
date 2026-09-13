"""Characterize the current Python contract, including permissive inputs."""

import pytest

from src.evaluators.hybrid import OfflineHybridEvaluator
from src.scoring.quality import calculate_quality_score


FIELDS = (
    "relevance_score", "correctness_score", "groundedness_score",
    "completeness_score", "quality_score", "status", "error_type",
    "improvement_feedback", "evaluation_mode", "evaluated_at", "evaluator_version",
)
DISCLAIMER = "These local semantic and rule-based checks are estimates, not a guarantee of factual correctness."
UNAVAILABLE = "Unavailable: correctness (no expected answer); groundedness estimate (no context)."
ANSWER = "alpha beta gamma delta epsilon"


def test_exact_single_result_and_repeatability(scorer):
    evaluator = OfflineHybridEvaluator(scorer)
    expected = dict(zip(FIELDS, [
        80, None, None, 80.0, 80.0, "Pass", "No Error",
        "The answer passed the available offline quality checks. " + UNAVAILABLE + " " + DISCLAIMER,
        "Offline Hybrid", "2026-01-02T03:04:05+00:00", "1.3.0",
    ]))
    for _ in range(2):
        result = evaluator.evaluate(" query ", " " + ANSWER + " ", " \t", None)
        assert tuple(result.to_dict()) == FIELDS
        assert result.to_dict() == expected
    assert scorer.calls == [("query", ANSWER)] * 2


def test_reference_call_order_and_completeness(scorer):
    result = OfflineHybridEvaluator(scorer).evaluate(" q ", ANSWER, " reference ", " source ")
    assert scorer.calls == [("q", ANSWER), ("reference", ANSWER), ("source", ANSWER)]
    assert (result.relevance_score, result.correctness_score, result.groundedness_score,
            result.completeness_score, result.quality_score) == (80, 80, 80, 80, 80)
    assert result.improvement_feedback == "The answer passed the available offline quality checks. " + DISCLAIMER


@pytest.mark.parametrize("threshold,status,error", [(0, "Pass", "No Error"), (80, "Pass", "No Error"), (80.01, "Fail", "Irrelevant Answer"), (100, "Fail", "Irrelevant Answer")])
def test_threshold_inclusive_and_float_accepted(scorer, threshold, status, error):
    result = OfflineHybridEvaluator(scorer, threshold).evaluate("query", ANSWER)
    assert (result.quality_score, result.status, result.error_type) == (80, status, error)
    if status == "Fail":
        assert result.improvement_feedback == (
            "The relevance score (80.0) was the weakest available metric and the main reason the overall quality score fell below the "
            f"configured pass threshold ({threshold}). " + UNAVAILABLE + " " + DISCLAIMER
        )


@pytest.mark.parametrize("threshold", [-1, 101, float("nan")])
def test_invalid_threshold(scorer, threshold):
    with pytest.raises(ValueError, match="pass_threshold must be between 0 and 100"):
        OfflineHybridEvaluator(scorer, threshold)


@pytest.mark.parametrize("value", [None, "", " \t", 0, False])
def test_falsy_or_blank_answer_is_empty(scorer, value):
    result = OfflineHybridEvaluator(scorer, 0).evaluate(None, value)
    assert (result.relevance_score, result.completeness_score, result.quality_score) == (0, 0, 0)
    assert (result.status, result.error_type) == ("Fail", "Empty Answer")
    assert scorer.calls == []
    assert result.improvement_feedback == "Provide a substantive answer before evaluating it. " + UNAVAILABLE + " " + DISCLAIMER


@pytest.mark.parametrize("field", ["question", "answer", "expected_answer", "context"])
def test_truthy_non_string_raises(scorer, field):
    inputs = {"question": "query", "answer": ANSWER, field: 123}
    with pytest.raises(AttributeError):
        OfflineHybridEvaluator(scorer).evaluate(**inputs)


def test_empty_question_is_not_rejected_by_core(scorer):
    assert OfflineHybridEvaluator(scorer).evaluate(None, ANSWER).status == "Pass"
    assert scorer.calls == [("", ANSWER)]


def test_empty_answer_still_scores_references(scorer):
    result = OfflineHybridEvaluator(scorer).evaluate("q", "", "reference", "source")
    assert scorer.calls == [("reference", ""), ("source", "")]
    assert (result.correctness_score, result.groundedness_score, result.completeness_score, result.quality_score) == (80, 80, 26.67, 52.0)
    assert result.error_type == "Empty Answer"


@pytest.mark.parametrize("scores,expected", [({}, None), ({"unknown": 99}, None), ({"relevance_score": 0}, 0), ({"relevance_score": 120}, 120), ({"relevance_score": -5}, -5), ({"relevance_score": 80, "completeness_score": 60}, 72.5), ({"correctness_score": 100, "relevance_score": 80, "groundedness_score": 60, "completeness_score": 40}, 76), ({"relevance_score": "12.345"}, 12.35)])
def test_weighting_and_no_clamping(scores, expected):
    assert calculate_quality_score(scores) == expected


@pytest.mark.parametrize("weights", [{"x": 0}, {"x": -1}])
def test_nonpositive_total_weight(weights):
    assert calculate_quality_score({"x": 90}, weights) is None


@pytest.mark.parametrize("answer,reference,correctness,groundedness,completeness,quality,error", [
    ("two weeks", "14 days", 85, 85, 95, 82.75, "No Error"),
    ("30 days", "14 days", 25, 25, 30, 37, "Contradictory Answer"),
])
def test_factual_overrides(scorer, answer, reference, correctness, groundedness, completeness, quality, error):
    scorer.score = 10 if error == "No Error" else 70
    result = OfflineHybridEvaluator(scorer).evaluate("duration?", answer, reference, reference)
    assert (result.correctness_score, result.groundedness_score, result.completeness_score, result.quality_score, result.error_type) == (correctness, groundedness, completeness, quality, error)
    if error != "No Error":
        assert result.improvement_feedback == 'The answer uses "30 days", while the expected answer uses "14 days"; this is a duration conflict. ' + DISCLAIMER


def test_question_repetition_caps_scores_and_overrides_feedback(scorer):
    result = OfflineHybridEvaluator(scorer).evaluate(ANSWER, ANSWER)
    assert (result.relevance_score, result.completeness_score, result.quality_score, result.error_type) == (20, 20, 20, "Incomplete Answer")
    assert result.improvement_feedback == "The response repeats or closely reformulates the question without providing an answer. Supply the requested factual value or conclusion. " + UNAVAILABLE + " " + DISCLAIMER


def test_semantic_failure_propagates(scorer):
    def fail(*args):
        raise RuntimeError("embedding failure")
    scorer.similarity = fail
    with pytest.raises(RuntimeError, match="embedding failure"):
        OfflineHybridEvaluator(scorer).evaluate("q", ANSWER)


@pytest.mark.parametrize("score,relevance,completeness,quality,error", [
    (69.99, 69.99, 30, 60.76, "Incomplete Answer"),
    (70, 70, 100, 76.92, "No Error"),
])
def test_short_answer_support_boundary_with_context_only(scorer, score, relevance, completeness, quality, error):
    scorer.score = score
    result = OfflineHybridEvaluator(scorer).evaluate("query", "brief", context="source")
    assert (result.relevance_score, result.completeness_score, result.quality_score, result.error_type) == (relevance, completeness, quality, error)


def test_quality_cap_for_context_conflict(scorer):
    scorer.score = 100
    answer = "the delay is 30 days and additional descriptive words explain the timing without adding any further factual claims here today"
    result = OfflineHybridEvaluator(scorer, 0).evaluate("query", answer, "reference", "14 days")
    assert (result.correctness_score, result.groundedness_score, result.completeness_score) == (100, 25, 100)
    assert (result.quality_score, result.status, result.error_type) == (60, "Fail", "Contradictory Answer")


def test_placeholder_can_have_high_quality_and_still_fail(scorer):
    scorer.score = 100
    result = OfflineHybridEvaluator(scorer, 0).evaluate("query", "unknown", "unknown", "unknown")
    assert (result.quality_score, result.status, result.error_type) == (97.25, "Fail", "Insufficient Data")


@pytest.mark.parametrize("words,completeness,quality", [(4, 37.5, 64.06), (5, 80, 80), (12, 80, 80), (13, 82.5, 80.94), (20, 100, 87.5)])
def test_length_completeness_boundaries(scorer, words, completeness, quality):
    answer = " ".join(f"token{index}" for index in range(words))
    result = OfflineHybridEvaluator(scorer).evaluate("query", answer)
    assert (result.completeness_score, result.quality_score) == (completeness, quality)
