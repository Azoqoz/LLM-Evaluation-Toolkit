"""Single Evaluation form interaction tests."""

import pytest
from streamlit.testing.v1 import AppTest


_TEST_APP = """
import src.ui.app as ui
from src.evaluators.hybrid import OfflineHybridEvaluator

class PerfectSimilarityScorer:
    def similarity(self, left, right):
        return 100.0

ui.get_evaluator = lambda threshold: OfflineHybridEvaluator(
    PerfectSimilarityScorer(), pass_threshold=threshold
)
ui._render_single(70)
"""


@pytest.mark.parametrize(
    ("question", "answer", "expected", "result_heading"),
    [
        (
            "What is the capital of Saudi Arabia?",
            "Riyadh is the capital of Saudi Arabia.",
            "The capital of Saudi Arabia is Riyadh.",
            "✓ Pass",
        ),
        (
            "What is the capital of Saudi Arabia?",
            "What is the capital of Saudi Arabia?",
            "",
            "× Fail",
        ),
    ],
)
def test_clear_fields_resets_inputs_and_pass_or_fail_result(
    question: str,
    answer: str,
    expected: str,
    result_heading: str,
) -> None:
    app = AppTest.from_string(_TEST_APP).run()
    app.text_area[0].set_value(question)
    app.text_area[1].set_value(answer)
    app.text_area[2].set_value(expected)
    app.text_area[3].set_value("Riyadh is the capital of Saudi Arabia.")
    app.button[0].click().run()

    assert app.button[0].label == "Run Evaluation"
    assert any(heading.value == result_heading for heading in app.subheader)

    app.button[1].click().run()

    assert [field.value for field in app.text_area] == ["", "", "", ""]
    assert not any(
        heading.value in {"✓ Pass", "× Fail"} for heading in app.subheader
    )


def test_clear_fields_preserves_threshold_and_is_single_page_only() -> None:
    app = AppTest.from_file("app.py").run()
    app.slider[0].set_value(83).run()
    for index, value in enumerate(("Question", "Answer", "Expected", "Context")):
        app.text_area[index].set_value(value)

    app.button[1].click().run()

    assert app.slider[0].value == 83
    assert [field.value for field in app.text_area] == ["", "", "", ""]

    app.radio[0].set_value("Batch Evaluation").run()
    assert all(button.label != "Clear fields" for button in app.button)
