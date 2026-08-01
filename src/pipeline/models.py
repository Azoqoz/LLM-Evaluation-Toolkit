"""Typed evaluation result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EvaluationResult:
    """Complete output of one offline hybrid evaluation."""

    relevance_score: float | None
    correctness_score: float | None
    groundedness_score: float | None
    completeness_score: float | None
    quality_score: float | None
    status: str
    error_type: str
    improvement_feedback: str
    evaluation_mode: str
    evaluated_at: str
    evaluator_version: str

    def to_dict(self) -> dict[str, object]:
        """Return a serialization-friendly dictionary."""

        return asdict(self)
