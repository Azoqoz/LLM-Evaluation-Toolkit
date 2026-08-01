"""Shared deterministic test doubles."""

from __future__ import annotations

import re

import pytest

from src.evaluators.hybrid import OfflineHybridEvaluator


class TokenOverlapScorer:
    """Fast semantic test double based on token Jaccard similarity."""

    def similarity(self, left: str, right: str) -> float:
        left_tokens = set(re.findall(r"\w+", left.lower()))
        right_tokens = set(re.findall(r"\w+", right.lower()))
        union = left_tokens | right_tokens
        return round(len(left_tokens & right_tokens) / len(union) * 100, 2) if union else 0.0


@pytest.fixture
def evaluator() -> OfflineHybridEvaluator:
    return OfflineHybridEvaluator(TokenOverlapScorer(), pass_threshold=50)
