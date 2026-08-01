"""Question-repetition detection and concise-answer regression tests."""

from src.evaluators.hybrid import OfflineHybridEvaluator


class PerfectSimilarityScorer:
    """Keep semantic similarity high so deterministic rules drive each test."""

    def similarity(self, left: str, right: str) -> float:
        return 100.0


class ExactMatchOnlyScorer:
    """Give short reference matches support without inflating relevance."""

    def similarity(self, left: str, right: str) -> float:
        return 100.0 if left.strip().casefold() == right.strip().casefold() else 20.0


def _evaluator() -> OfflineHybridEvaluator:
    return OfflineHybridEvaluator(PerfectSimilarityScorer())


def test_exact_question_repetition_fails() -> None:
    question = "What is the capital of Saudi Arabia?"
    result = _evaluator().evaluate(question, question)

    assert result.status == "Fail"
    assert result.error_type == "Incomplete Answer"
    assert result.relevance_score <= 20
    assert result.completeness_score <= 20
    assert result.quality_score < 70
    assert "repeats or closely reformulates" in result.improvement_feedback


def test_close_question_paraphrase_fails() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "Which city serves as Saudi Arabia's capital?",
    )

    assert result.status == "Fail"
    assert result.error_type == "Incomplete Answer"
    assert result.relevance_score <= 20


def test_copied_question_with_punctuation_change_fails() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "What is the capital of Saudi Arabia.",
    )

    assert result.status == "Fail"
    assert result.error_type == "Incomplete Answer"


def test_question_reformatted_as_statement_fails() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "The capital of Saudi Arabia is what.",
    )

    assert result.status == "Fail"
    assert result.error_type == "Incomplete Answer"


def test_valid_short_factual_answer_passes_when_supported() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "Riyadh.",
        "The capital of Saudi Arabia is Riyadh.",
        "Riyadh is the capital of Saudi Arabia.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.completeness_score >= 90


def test_valid_yes_answer_passes_when_supported() -> None:
    result = OfflineHybridEvaluator(ExactMatchOnlyScorer()).evaluate(
        "Is the request approved?",
        "Yes.",
        "Yes.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.relevance_score >= 70
    assert result.completeness_score >= 90
