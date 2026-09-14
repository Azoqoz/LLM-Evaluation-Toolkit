"""Direct application use independent of the HTTP adapter."""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from src.application.serialization import serialize_rows
from src.application.service import ApplicationError, EvaluationService
from src.config.settings import METRIC_WEIGHTS
from src.evaluators.hybrid import OfflineHybridEvaluator


def test_direct_service_matches_evaluator(service, scorer):
    args = {"question": "query", "answer": "alpha beta gamma delta epsilon", "expected_answer": "reference"}
    assert service.evaluate(**args) == OfflineHybridEvaluator(scorer).evaluate(**args).to_dict()


def test_configuration_returns_independent_copies(service):
    config = service.configuration()
    config["metric_weights"]["correctness_score"] = 0
    assert service.configuration()["metric_weights"] == METRIC_WEIGHTS
    assert METRIC_WEIGHTS["correctness_score"] == .35


@pytest.mark.parametrize("threshold", [-1, 101, float("nan"), float("inf"), True, "70", None])
def test_service_validates_threshold_without_constructing_evaluator(service, factory, threshold):
    with pytest.raises(ApplicationError) as exc:
        service.evaluate("q", "a", pass_threshold=threshold)
    assert exc.value.code == "invalid_request"
    factory.assert_not_called()


def test_service_rejects_invalid_text_types(service, factory):
    with pytest.raises(ApplicationError) as exc:
        service.evaluate("q", {"answer": "a"})
    assert exc.value.details == {"field": "answer"}
    factory.assert_not_called()


def test_parallel_thresholds_remain_request_local(service):
    def evaluate(threshold):
        return service.evaluate("query", "alpha beta gamma delta epsilon", pass_threshold=threshold)
    thresholds = [100, 0, 80.01, 80] * 4
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(evaluate, thresholds))
    assert [result["status"] for result in results] == ["Fail", "Pass", "Fail", "Pass"] * 4


def test_serialization_preserves_precision_nulls_and_source():
    original = pd.DataFrame({"metric": [None, 12.3456789012345], "extra": [float("inf"), float("-inf")]})
    copy = original.copy(deep=True)
    assert serialize_rows(original) == [{"metric": None, "extra": None}, {"metric": 12.3456789012345, "extra": None}]
    pd.testing.assert_frame_equal(original, copy)


def test_initialized_service_evaluates_empty_text_without_loading_weights(service):
    result = service.evaluate(None, "")
    assert (result["quality_score"], result["error_type"]) == (0, "Empty Answer")


def test_batch_service_preserves_native_frame_and_csv(service):
    result = service.evaluate_csv(b"question,answer\nq,alpha beta gamma delta epsilon\n")
    assert isinstance(result.results, pd.DataFrame)
    assert result.validation.can_evaluate
    assert result.to_dict()["rows"][0]["correctness_score"] is None


def test_service_requires_csv_bytes(service, factory):
    with pytest.raises(ApplicationError) as exc:
        service.evaluate_csv("question,answer")
    assert exc.value.code == "invalid_csv"
    factory.assert_not_called()
