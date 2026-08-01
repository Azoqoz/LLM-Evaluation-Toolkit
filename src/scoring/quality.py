"""Quality score calculation."""

from __future__ import annotations

from collections.abc import Mapping

from src.config.settings import METRIC_WEIGHTS


def calculate_quality_score(
    scores: Mapping[str, float | None],
    weights: Mapping[str, float] = METRIC_WEIGHTS,
) -> float | None:
    """Return the normalized weighted mean of only the available metrics."""

    available = [
        (float(scores[name]), weight)
        for name, weight in weights.items()
        if scores.get(name) is not None
    ]
    if not available:
        return None
    total_weight = sum(weight for _, weight in available)
    if total_weight <= 0:
        return None
    return round(sum(score * weight for score, weight in available) / total_weight, 2)
