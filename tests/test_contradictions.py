"""Factual contradiction regression tests."""

import pytest

from src.evaluators.contradictions import (
    detect_contradictions,
    matches_short_expected_value,
)
from src.evaluators.hybrid import OfflineHybridEvaluator


class HighSimilarityScorer:
    """Simulate the high semantic similarity that exposed the regression."""

    def similarity(self, left: str, right: str) -> float:
        return 90.0


class LowSimilarityScorer:
    """Expose deterministic equivalence boosts over weak semantic similarity."""

    def similarity(self, left: str, right: str) -> float:
        return 58.0


def _evaluator() -> OfflineHybridEvaluator:
    return OfflineHybridEvaluator(HighSimilarityScorer())


def test_named_entity_mismatch_riyadh_vs_jeddah() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "Jeddah is the capital of Saudi Arabia.",
        "The capital of Saudi Arabia is Riyadh.",
        "Riyadh is the capital and largest city of Saudi Arabia.",
    )

    assert result.status == "Fail"
    assert result.error_type == "Contradictory Answer"
    assert result.correctness_score <= 25
    assert result.groundedness_score <= 25
    assert result.quality_score < 70
    assert "Jeddah" in result.improvement_feedback
    assert "Riyadh" in result.improvement_feedback


def test_duration_mismatch_14_days_vs_30_days() -> None:
    result = _evaluator().evaluate(
        "How long is the return period?",
        "The return period is 30 days.",
        "The return period is 14 days.",
    )

    assert result.status == "Fail"
    assert result.error_type == "Contradictory Answer"
    assert result.correctness_score <= 25
    assert "30 days" in result.improvement_feedback
    assert "14 days" in result.improvement_feedback


def test_yes_vs_no_is_a_contradiction() -> None:
    result = _evaluator().evaluate(
        "Was the request approved?",
        "No.",
        "Yes.",
    )

    assert result.status == "Fail"
    assert result.error_type == "Contradictory Answer"
    assert result.correctness_score <= 25
    assert '"no"' in result.improvement_feedback.lower()
    assert '"yes"' in result.improvement_feedback.lower()


def test_percentage_date_and_opposite_word_mismatches() -> None:
    cases = (
        ("The rate is 10%.", "The rate is 20%.", "10%", "20%"),
        ("The policy starts in 2024.", "The policy starts in 2025.", "2024", "2025"),
        (
            "The request was approved.",
            "The request was rejected.",
            "approved",
            "rejected",
        ),
    )
    for answer, expected, answer_value, expected_value in cases:
        result = _evaluator().evaluate("What is the result?", answer, expected)
        assert result.error_type == "Contradictory Answer"
        assert result.status == "Fail"
        assert answer_value in result.improvement_feedback
        assert expected_value in result.improvement_feedback


def test_equivalent_duration_paraphrase_is_preserved() -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        "How long is the return period?",
        "Customers can return the product within two weeks.",
        "The return period is 14 days.",
        "Customers may return products within 14 days of purchase.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85
    assert result.groundedness_score >= 85
    assert result.quality_score > 70


def test_one_year_equals_twelve_months() -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        "How long is the coverage period?",
        "Coverage remains active for one year.",
        "The coverage period is 12 months.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85


def test_equivalent_percentage_formats() -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        "What proportion was approved?",
        "The approved proportion was 50 percent.",
        "The approved proportion was 0.5.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85


def test_equivalent_date_formats() -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        "When does coverage begin?",
        "Coverage begins on January 5, 2025.",
        "The coverage start date is 2025-01-05.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85


def test_correct_numeric_paraphrase_without_identical_wording() -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        "How many items are included?",
        "Inside the package, customers receive fourteen items.",
        "The package contains 14 items.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85


def test_matching_factual_answer_is_not_a_contradiction() -> None:
    result = _evaluator().evaluate(
        "What is the capital of Saudi Arabia?",
        "The capital of Saudi Arabia is Riyadh.",
        "Riyadh is the capital of Saudi Arabia.",
        "Riyadh is the capital and largest city of Saudi Arabia.",
    )

    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score == 90
    assert result.groundedness_score == 90


@pytest.mark.parametrize(
    ("question", "answer", "expected_answer", "context"),
    [
        (
            "What is the boiling point of water at sea level?",
            "Water boils at 100 degrees Celsius at sea level.",
            "100 degrees Celsius.",
            "At standard atmospheric pressure, water boils at 100°C.",
        ),
        (
            "What is the largest ocean on Earth?",
            "The Pacific Ocean is the largest ocean on Earth.",
            "The Pacific Ocean.",
            "The Pacific Ocean is Earth's largest ocean.",
        ),
        (
            "What gas do plants absorb from the atmosphere?",
            "Plants absorb carbon dioxide.",
            "Carbon dioxide.",
            "Plants use carbon dioxide during photosynthesis.",
        ),
        (
            "How many continents are there?",
            "There are seven continents.",
            "Seven.",
            "Earth is commonly divided into seven continents.",
        ),
        (
            "What is H2O commonly called?",
            "H2O is water.",
            "Water.",
            "The chemical formula H2O represents water.",
        ),
        (
            "What is the square root of 81?",
            "The square root of 81 is 9.",
            "9.",
            "Nine multiplied by nine equals 81.",
        ),
    ],
)
def test_correct_batch_facts_are_not_contradictions(
    question: str,
    answer: str,
    expected_answer: str,
    context: str,
) -> None:
    result = _evaluator().evaluate(question, answer, expected_answer, context)
    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85
    assert result.groundedness_score >= 85


@pytest.mark.parametrize(
    ("question", "answer", "expected_answer", "context"),
    [
        (
            "At what temperature does water boil?",
            "Water boils at 100°C.",
            "Water boils at 100 degrees Celsius.",
            "The boiling point is 100 degrees Celsius.",
        ),
        (
            "What gas do plants absorb?",
            "Plants absorb CO2.",
            "Plants absorb carbon dioxide.",
            "Carbon dioxide is absorbed during photosynthesis.",
        ),
        (
            "How long does the session last?",
            "The session lasts one hour.",
            "The session lasts 60 minutes.",
            "The scheduled duration is 60 minutes.",
        ),
    ],
)
def test_normalized_factual_forms_boost_weak_semantic_scores(
    question: str,
    answer: str,
    expected_answer: str,
    context: str,
) -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        question, answer, expected_answer, context
    )
    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85
    assert result.groundedness_score >= 85


@pytest.mark.parametrize(
    ("question", "answer", "expected_answer", "context"),
    [
        (
            "What is the square root of 81?",
            "The square root of 81 is 9.",
            "9.",
            "Nine multiplied by nine equals 81.",
        ),
        (
            "How many continents are there?",
            "There are seven continents.",
            "Seven.",
            "Earth is commonly divided into seven continents.",
        ),
        (
            "What is H2O commonly called?",
            "H2O is water.",
            "Water.",
            "The chemical formula H2O represents water.",
        ),
        (
            "Which planet is known as the Red Planet?",
            "Mars is known as the Red Planet.",
            "Mars.",
            "The Red Planet is Mars because of iron oxide on its surface.",
        ),
        (
            "What is the boiling point of water at sea level?",
            "Water boils at 100°C at sea level.",
            "100 degrees Celsius.",
            "At standard pressure, the boiling point is 100 degrees Celsius.",
        ),
        (
            "Which country contains the city of Paris?",
            "Paris is a major city in France.",
            "France.",
            "France contains Paris, its capital city.",
        ),
    ],
)
def test_short_expected_factual_value_gets_correctness_floor(
    question: str,
    answer: str,
    expected_answer: str,
    context: str,
) -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        question, answer, expected_answer, context
    )
    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85
    assert result.quality_score >= 70


def test_incorrect_short_numeric_value_remains_a_contradiction() -> None:
    result = _evaluator().evaluate(
        "What is the square root of 81?",
        "The square root of 81 is 8.",
        "9.",
        "Nine multiplied by nine equals 81.",
    )
    assert result.status == "Fail"
    assert result.error_type == "Contradictory Answer"
    assert result.correctness_score <= 25


@pytest.mark.parametrize(
    ("question", "answer", "expected_answer", "context"),
    [
        (
            "What is the currency of Japan?",
            "Japan uses the yen.",
            "The Japanese yen.",
            "The official currency of Japan is the yen.",
        ),
        (
            "What is retrieval-augmented generation?",
            "RAG retrieves relevant context before generating an answer.",
            "RAG combines retrieval with text generation.",
            "Retrieval-augmented generation retrieves external context and uses it to support generation.",
        ),
        (
            "What percentage of the project is complete?",
            "The project is halfway complete.",
            "The project is 50% complete.",
            "Current progress is 50 percent.",
        ),
        (
            "How much is the discount?",
            "The discount is one quarter of the price.",
            "The discount is 25%.",
            "Customers receive a 25 percent discount.",
        ),
        (
            "What is the storage limit?",
            "The storage limit is one gigabyte.",
            "The limit is 1024 megabytes.",
            "The account allows approximately 1 GB of storage.",
        ),
    ],
)
def test_remaining_valid_batch_cases_pass_with_normalized_evidence(
    question: str,
    answer: str,
    expected_answer: str,
    context: str,
) -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        question, answer, expected_answer, context
    )
    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85
    assert result.groundedness_score >= 85
    assert result.quality_score >= 70


@pytest.mark.parametrize(
    ("abbreviation", "expansion"),
    [
        ("RAG", "Retrieval-augmented generation"),
        ("CPU", "Central Processing Unit"),
        ("API", "Application Programming Interface"),
        ("RAM", "Random Access Memory"),
    ],
)
def test_abbreviation_expansions_are_reusable(
    abbreviation: str, expansion: str
) -> None:
    result = OfflineHybridEvaluator(LowSimilarityScorer()).evaluate(
        f"What does {abbreviation} stand for?",
        f"{abbreviation}.",
        f"{expansion}.",
        f"{expansion} is abbreviated as {abbreviation}.",
    )
    assert result.status == "Pass"
    assert result.error_type == "No Error"
    assert result.correctness_score >= 85


@pytest.mark.parametrize(
    ("answer", "reference"),
    [
        ("Japan uses the yen.", "The Japanese currency is the yen."),
        ("Saudi policy applies.", "The Saudi Arabia policy applies."),
        ("Britain uses this system.", "The British system is in use."),
    ],
)
def test_country_and_adjective_forms_are_not_entity_conflicts(
    answer: str, reference: str
) -> None:
    assert not detect_contradictions(answer, reference).detected


@pytest.mark.parametrize(
    ("answer", "expected_answer"),
    [
        ("The value is half.", "50%."),
        ("The value is one half.", "0.5."),
        ("The value is three quarters.", "75 percent."),
        ("The value is one fifth.", "20%."),
    ],
)
def test_common_fractions_match_normalized_percentages(
    answer: str, expected_answer: str
) -> None:
    assert matches_short_expected_value(answer, expected_answer)


@pytest.mark.parametrize(
    ("answer", "expected_answer"),
    [
        ("The discount is one half.", "The discount is 25%."),
        ("The storage limit is 1 GB.", "The storage limit is 512 MB."),
    ],
)
def test_incompatible_normalized_values_remain_contradictions(
    answer: str, expected_answer: str
) -> None:
    result = _evaluator().evaluate("What is the value?", answer, expected_answer)
    assert result.status == "Fail"
    assert result.error_type == "Contradictory Answer"
