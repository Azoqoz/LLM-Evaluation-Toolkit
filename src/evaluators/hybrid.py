"""Offline hybrid evaluator combining semantic and rule-based methods."""

from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import (
    DEFAULT_PASS_THRESHOLD,
    EVALUATION_MODE,
    EVALUATOR_VERSION,
)
from src.evaluators.contradictions import (
    detect_contradictions,
    matches_short_expected_value,
)
from src.evaluators.rules import evaluate_rules
from src.evaluators.semantic import SemanticScorer, SentenceTransformerScorer
from src.pipeline.models import EvaluationResult
from src.reporting.feedback import generate_feedback
from src.scoring.classification import classify_error, classify_threshold_failure
from src.scoring.quality import calculate_quality_score


class OfflineHybridEvaluator:
    """Evaluate answer quality locally without an external API."""

    def __init__(
        self,
        semantic_scorer: SemanticScorer | None = None,
        pass_threshold: int = DEFAULT_PASS_THRESHOLD,
    ) -> None:
        if not 0 <= pass_threshold <= 100:
            raise ValueError("pass_threshold must be between 0 and 100")
        self.semantic_scorer = semantic_scorer or SentenceTransformerScorer()
        self.pass_threshold = pass_threshold

    def evaluate(
        self,
        question: str,
        answer: str,
        expected_answer: str | None = None,
        context: str | None = None,
    ) -> EvaluationResult:
        """Evaluate one answer and return all available metrics."""

        question = (question or "").strip()
        answer = (answer or "").strip()
        expected_answer = (expected_answer or "").strip() or None
        context = (context or "").strip() or None
        rules = evaluate_rules(question, answer)

        relevance = (
            0.0 if rules.empty else self.semantic_scorer.similarity(question, answer)
        )
        if rules.question_repetition:
            relevance = min(relevance, 20.0)
        correctness = (
            self.semantic_scorer.similarity(expected_answer, answer)
            if expected_answer
            else None
        )
        groundedness = (
            self.semantic_scorer.similarity(context, answer) if context else None
        )
        contradictions = detect_contradictions(answer, expected_answer, context)
        expected_value_matched = matches_short_expected_value(
            answer, expected_answer
        )
        if contradictions.expected_conflicts and correctness is not None:
            correctness = min(correctness, 25.0)
        elif (
            contradictions.expected_equivalences or expected_value_matched
        ) and correctness is not None:
            correctness = max(correctness, 85.0)
        if contradictions.context_conflicts and groundedness is not None:
            groundedness = min(groundedness, 25.0)
        elif contradictions.context_equivalences and groundedness is not None:
            groundedness = max(groundedness, 85.0)

        reference_scores = [
            score for score in (correctness, groundedness) if score is not None
        ]
        short_answer_supported = bool(
            rules.extremely_short
            and reference_scores
            and max(reference_scores) >= 70
            and not contradictions.detected
        )
        if short_answer_supported:
            relevance = max(relevance, 70.0)
        length_score = min(100.0, rules.word_count / 20 * 100)
        if short_answer_supported:
            length_score = 100.0
        elif rules.word_count >= 5:
            length_score = max(60.0, length_score)
        effective_penalty = rules.penalty
        if short_answer_supported:
            effective_penalty = max(0.0, effective_penalty - 45.0)
        completeness_parts = [length_score, 100.0 - effective_penalty]
        if correctness is not None:
            completeness_parts.append(correctness)
        completeness = round(sum(completeness_parts) / len(completeness_parts), 2)
        if rules.question_repetition:
            completeness = min(completeness, 20.0)

        metrics = {
            "relevance_score": relevance,
            "correctness_score": correctness,
            "groundedness_score": groundedness,
            "completeness_score": completeness,
        }
        quality = calculate_quality_score(metrics)
        if contradictions.detected and quality is not None:
            quality = min(quality, 60.0)
        error_type = classify_error(
            rules,
            relevance,
            correctness,
            groundedness,
            completeness,
            contradiction_detected=contradictions.detected,
            short_answer_supported=short_answer_supported,
        )
        status = (
            "Pass"
            if quality is not None
            and quality >= self.pass_threshold
            and error_type == "No Error"
            else "Fail"
        )
        threshold_failure_metric: str | None = None
        threshold_failure_score: float | None = None
        threshold_failure = error_type == "No Error" and status == "Fail"
        if threshold_failure:
            (
                error_type,
                threshold_failure_metric,
                threshold_failure_score,
            ) = classify_threshold_failure(metrics)
        feedback = generate_feedback(
            error_type,
            metrics,
            contradiction_feedback=(
                contradictions.primary.feedback() if contradictions.primary else None
            ),
            threshold_failure=threshold_failure,
            threshold_failure_metric=threshold_failure_metric,
            threshold_failure_score=threshold_failure_score,
            question_repetition=rules.question_repetition,
            quality_score=quality,
            pass_threshold=self.pass_threshold,
        )

        return EvaluationResult(
            **metrics,
            quality_score=quality,
            status=status,
            error_type=error_type,
            improvement_feedback=feedback,
            evaluation_mode=EVALUATION_MODE,
            evaluated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            evaluator_version=EVALUATOR_VERSION,
        )
