"""Deterministic primary error classification."""

from __future__ import annotations

from src.evaluators.rules import RuleFindings


_THRESHOLD_FAILURE_METRICS = (
    ("relevance_score", "Irrelevant Answer"),
    ("correctness_score", "Incorrect Answer"),
    ("groundedness_score", "Unsupported Answer"),
    ("completeness_score", "Incomplete Answer"),
)


def classify_threshold_failure(
    scores: dict[str, float | None],
) -> tuple[str, str, float]:
    """Classify a quality-only failure by its weakest available metric.

    Metric order is a deterministic tie-breaker: relevance, correctness,
    groundedness, then completeness.
    """

    available = [
        (score, priority, metric_name, error_type)
        for priority, (metric_name, error_type) in enumerate(
            _THRESHOLD_FAILURE_METRICS
        )
        if (score := scores.get(metric_name)) is not None
    ]
    if not available:
        return "Incomplete Answer", "completeness_score", 0.0
    score, _, metric_name, error_type = min(available)
    return error_type, metric_name, float(score)


def classify_error(
    rules: RuleFindings,
    relevance_score: float | None,
    correctness_score: float | None,
    groundedness_score: float | None,
    completeness_score: float | None,
    contradiction_detected: bool = False,
    short_answer_supported: bool = False,
) -> str:
    """Choose one explainable error using a fixed priority order."""

    if rules.empty:
        return "Empty Answer"
    if rules.placeholder:
        return "Insufficient Data"
    if rules.unwanted_refusal:
        return "Unwanted Refusal"
    if rules.question_repetition:
        return "Incomplete Answer"
    if contradiction_detected:
        return "Contradictory Answer"
    if rules.formatting_problem:
        return "Formatting Issue"
    if rules.excessively_verbose:
        return "Overly Verbose"
    if relevance_score is not None and relevance_score < 35:
        return "Irrelevant Answer"
    if correctness_score is not None and correctness_score < 30:
        return "Contradictory Answer"
    if correctness_score is not None and correctness_score < 55:
        return "Incorrect Answer"
    if groundedness_score is not None and groundedness_score < 50:
        return "Unsupported Answer"
    if (
        (rules.extremely_short and not short_answer_supported)
        or rules.excessive_repetition
        or (completeness_score is not None and completeness_score < 55)
    ):
        return "Incomplete Answer"
    return "No Error"
