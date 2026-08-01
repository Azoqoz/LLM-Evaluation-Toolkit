"""Deterministic improvement feedback."""

from __future__ import annotations

from collections.abc import Mapping


_ERROR_FEEDBACK = {
    "Empty Answer": "Provide a substantive answer before evaluating it.",
    "Irrelevant Answer": "Revise the answer so it directly addresses the question.",
    "Incorrect Answer": "The answer does not closely match the expected answer; review the key claims and missing details.",
    "Incomplete Answer": "Expand the answer with the essential details needed to resolve the question.",
    "Unsupported Answer": "The groundedness estimate is low. Remove unsupported claims or connect them more clearly to the supplied context.",
    "Contradictory Answer": "The answer strongly conflicts with the expected answer. Recheck its central claim.",
    "Overly Verbose": "Make the answer more concise while preserving the information needed to answer the question.",
    "Unwanted Refusal": "Answer the request directly when it is safe and possible instead of using a generic refusal.",
    "Formatting Issue": "Improve readability by using normal capitalization, punctuation, and shorter lines.",
    "Insufficient Data": "Replace placeholder text with a complete, meaningful answer.",
}


def generate_feedback(
    error_type: str,
    scores: Mapping[str, float | None],
    contradiction_feedback: str | None = None,
    threshold_failure: bool = False,
    threshold_failure_metric: str | None = None,
    threshold_failure_score: float | None = None,
    quality_score: float | None = None,
    pass_threshold: int | None = None,
    question_repetition: bool = False,
) -> str:
    """Build concise feedback and disclose unavailable optional metrics."""

    messages: list[str] = []
    if question_repetition:
        messages.append(
            "The response repeats or closely reformulates the question without "
            "providing an answer. Supply the requested factual value or conclusion."
        )
    elif contradiction_feedback:
        messages.append(contradiction_feedback)
    elif threshold_failure:
        metric_label = (threshold_failure_metric or "quality_score").removesuffix(
            "_score"
        ).replace("_", " ")
        metric_text = (
            "N/A"
            if threshold_failure_score is None
            else f"{threshold_failure_score:.1f}"
        )
        messages.append(
            f"The {metric_label} score ({metric_text}) was the weakest available "
            f"metric and the main reason the overall quality score fell below the "
            f"configured pass threshold ({pass_threshold})."
        )
    elif error_type == "No Error":
        messages.append("The answer passed the available offline quality checks.")
    else:
        messages.append(_ERROR_FEEDBACK[error_type])

    unavailable = []
    if scores.get("correctness_score") is None:
        unavailable.append("correctness (no expected answer)")
    if scores.get("groundedness_score") is None:
        unavailable.append("groundedness estimate (no context)")
    if unavailable:
        messages.append("Unavailable: " + "; ".join(unavailable) + ".")

    messages.append(
        "These local semantic and rule-based checks are estimates, not a guarantee of factual correctness."
    )
    return " ".join(messages)
