"""Deterministic rule-based answer checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleFindings:
    """Boolean findings and simple measurements for an answer."""

    empty: bool = False
    extremely_short: bool = False
    question_repetition: bool = False
    excessive_repetition: bool = False
    placeholder: bool = False
    unwanted_refusal: bool = False
    excessively_verbose: bool = False
    formatting_problem: bool = False
    word_count: int = 0

    @property
    def penalty(self) -> float:
        """Return a bounded completeness penalty from all active checks."""

        penalties = (
            (self.empty, 100),
            (self.extremely_short, 45),
            (self.question_repetition, 80),
            (self.excessive_repetition, 25),
            (self.placeholder, 65),
            (self.unwanted_refusal, 45),
            (self.excessively_verbose, 15),
            (self.formatting_problem, 10),
        )
        return float(min(100, sum(value for active, value in penalties if active)))


_PLACEHOLDERS = re.compile(
    r"^\s*(?:n/?a|none|unknown|todo|tbd|placeholder|no answer|not sure|idk)[.!]?\s*$",
    re.IGNORECASE,
)
_REFUSALS = re.compile(
    r"\b(?:i (?:cannot|can't|won't|am unable to)|as an ai|i must refuse|"
    r"i do not have the ability|i'm sorry,? but i can't)\b",
    re.IGNORECASE,
)
_QUESTION_WORDS = {
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "when",
    "where",
    "why",
    "how",
}
_QUESTION_COMMANDS = {"answer", "identify", "name", "state", "tell"}
_REPETITION_STOPWORDS = {
    "a",
    "an",
    "are",
    "as",
    "be",
    "being",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "please",
    "question",
    "query",
    "asked",
    "asking",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "would",
    *(_QUESTION_WORDS | _QUESTION_COMMANDS),
}


def _question_repetition(question: str, answer: str) -> bool:
    """Return whether an answer mostly restates a question without new content."""

    question_tokens = re.findall(r"\b[\w'-]+\b", (question or "").casefold())
    answer_tokens = re.findall(r"\b[\w'-]+\b", (answer or "").casefold())
    if not question_tokens or not answer_tokens:
        return False
    if question_tokens == answer_tokens:
        return True

    question_content = {
        token for token in question_tokens if token not in _REPETITION_STOPWORDS
    }
    answer_content = {
        token for token in answer_tokens if token not in _REPETITION_STOPWORDS
    }
    if not question_content:
        return False

    coverage = len(question_content & answer_content) / len(question_content)
    new_content = answer_content - question_content
    question_like_answer = (
        (answer or "").strip().endswith("?")
        or answer_tokens[0] in _QUESTION_WORDS
        or answer_tokens[0] in _QUESTION_COMMANDS
    )
    if question_like_answer and coverage >= 0.65:
        return True
    return coverage >= 0.8 and not new_content


def evaluate_rules(question: str, answer: str) -> RuleFindings:
    """Inspect an answer for deterministic quality issues."""

    cleaned = (answer or "").strip()
    words = re.findall(r"\b[\w'-]+\b", cleaned.lower())
    word_count = len(words)
    empty = not cleaned

    sentence_chunks = [
        chunk.strip().lower()
        for chunk in re.split(r"[.!?\n]+", cleaned)
        if chunk.strip()
    ]
    repeated_sentence = bool(
        sentence_chunks
        and len(sentence_chunks) >= 3
        and (len(sentence_chunks) - len(set(sentence_chunks))) / len(sentence_chunks) >= 0.4
    )
    token_repetition = bool(
        word_count >= 12
        and max((words.count(word) for word in set(words)), default=0) / word_count >= 0.35
    )

    question_words = len(re.findall(r"\b[\w'-]+\b", question or ""))
    excessively_verbose = word_count > 350 or (
        word_count > 160 and question_words > 0 and word_count / question_words > 30
    )
    formatting_problem = bool(
        re.search(r"(?:[!?]){4,}", cleaned)
        or re.search(r"\b[A-Z]{5,}(?:\s+[A-Z]{5,}){2,}\b", cleaned)
        or any(len(line) > 500 for line in cleaned.splitlines())
    )

    return RuleFindings(
        empty=empty,
        extremely_short=not empty and word_count < 5,
        question_repetition=_question_repetition(question, cleaned),
        excessive_repetition=repeated_sentence or token_repetition,
        placeholder=bool(_PLACEHOLDERS.match(cleaned)),
        unwanted_refusal=bool(_REFUSALS.search(cleaned)),
        excessively_verbose=excessively_verbose,
        formatting_problem=formatting_problem,
        word_count=word_count,
    )
