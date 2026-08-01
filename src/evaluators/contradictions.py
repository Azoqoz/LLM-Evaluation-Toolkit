"""Deterministic factual contradiction and key-value mismatch checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}
_NUMBER_PATTERN = (
    r"(?:\d+(?:\.\d+)?|"
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"hundred)(?:[-\s](?:one|two|three|four|five|six|seven|eight|nine))?)"
)
_DURATION_RE = re.compile(
    rf"\b(?P<value>{_NUMBER_PATTERN})\s*"
    r"(?P<unit>seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    rf"\b(?P<value>{_NUMBER_PATTERN})\s*"
    r"(?:%(?!\w)|percent(?:age points?)?\b)",
    re.IGNORECASE,
)
_TEMPERATURE_RE = re.compile(
    rf"\b(?P<value>{_NUMBER_PATTERN})\s*"
    r"(?:(?:degrees?\s*)?(?P<word_unit>celsius|fahrenheit)|"
    r"°\s*(?P<symbol_unit>[cf]))\b",
    re.IGNORECASE,
)
_FRACTION_RE = re.compile(
    r"\b(?:three[-\s]+quarters?|one[-\s]+quarters?|one[-\s]+halves?|"
    r"one[-\s]+half|one[-\s]+fifths?|halfway|half)\b",
    re.IGNORECASE,
)
_FRACTION_VALUES = {
    "halfway": 0.5,
    "half": 0.5,
    "one half": 0.5,
    "one halves": 0.5,
    "one quarter": 0.25,
    "one quarters": 0.25,
    "three quarter": 0.75,
    "three quarters": 0.75,
    "one fifth": 0.2,
    "one fifths": 0.2,
}
_STORAGE_RE = re.compile(
    rf"\b(?P<value>{_NUMBER_PATTERN})\s*"
    r"(?P<unit>kilobytes?|kb|megabytes?|mb|gigabytes?|gb)\b",
    re.IGNORECASE,
)
_STORAGE_FACTORS_KB = {
    "kilobyte": 1,
    "kb": 1,
    "megabyte": 1024,
    "mb": 1024,
    "gigabyte": 1024 * 1024,
    "gb": 1024 * 1024,
}
_MONTH_NUMBERS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_MONTH_PATTERN = "|".join(_MONTH_NUMBERS)
_ISO_DATE_RE = re.compile(
    r"\b(?P<year>(?:19|20)\d{2})[-/](?P<month>0?[1-9]|1[0-2])"
    r"[-/](?P<day>0?[1-9]|[12]\d|3[01])\b"
)
_MONTH_FIRST_DATE_RE = re.compile(
    rf"\b(?P<month>{_MONTH_PATTERN})\s+"
    r"(?P<day>[0-3]?\d)(?:st|nd|rd|th)?(?:,\s*|\s+)"
    r"(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_DAY_FIRST_DATE_RE = re.compile(
    rf"\b(?P<day>[0-3]?\d)(?:st|nd|rd|th)?\s+"
    rf"(?P<month>{_MONTH_PATTERN})(?:,\s*|\s+)"
    r"(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_NUMBER_RE = re.compile(rf"\b{_NUMBER_PATTERN}\b", re.IGNORECASE)
_ENTITY_RE = re.compile(
    r"\b[A-Z][A-Za-z'-]*(?:\s+(?:(?:of|the|and|bin|al)\s+)?"
    r"[A-Z][A-Za-z'-]*)*\b"
)

_DURATION_FACTORS = {
    "second": ("fixed", 1),
    "minute": ("fixed", 60),
    "hour": ("fixed", 3_600),
    "day": ("fixed", 86_400),
    "week": ("fixed", 604_800),
    "month": ("calendar", 1),
    "year": ("calendar", 12),
}
_ENTITY_EXCLUSIONS = {
    "a",
    "an",
    "the",
    "this",
    "that",
    "these",
    "those",
    "yes",
    "no",
    "true",
    "false",
    "approved",
    "rejected",
    "accepted",
    "denied",
    "allowed",
    "prohibited",
    "enabled",
    "disabled",
    "at",
    "there",
    "celsius",
    "fahrenheit",
    "kelvin",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}
_CONTENT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}
_OPPOSITE_PAIRS = (
    ("yes", "no"),
    ("approved", "rejected"),
    ("approved", "denied"),
    ("accepted", "rejected"),
    ("accepted", "denied"),
    ("allowed", "prohibited"),
    ("enabled", "disabled"),
    ("true", "false"),
    ("successful", "failed"),
    ("increase", "decrease"),
    ("increased", "decreased"),
    ("before", "after"),
)
_FACT_ALIASES = (
    ("chemical formula", re.compile(r"\bh\s*2\s*o\b", re.IGNORECASE), re.compile(r"\bwater\b", re.IGNORECASE)),
    ("chemical formula", re.compile(r"\bco\s*2\b", re.IGNORECASE), re.compile(r"\bcarbon\s+dioxide\b", re.IGNORECASE)),
)
_ENTITY_CANONICAL_FORMS = {
    "japan": "japan",
    "japanese": "japan",
    "saudi": "saudi arabia",
    "saudi arabia": "saudi arabia",
    "britain": "britain",
    "british": "britain",
}


@dataclass(frozen=True)
class Conflict:
    """One explainable conflict between an answer and a reference."""

    kind: str
    answer_value: str
    reference_value: str
    source: str

    def feedback(self) -> str:
        """Describe the conflicting values in plain language."""

        labels = {
            "named entity": "named-entity",
            "duration": "duration",
            "percentage": "percentage",
            "temperature": "temperature",
            "storage": "storage-unit",
            "date": "date",
            "number": "numeric",
            "polarity": "opposite-answer",
        }
        article = "an" if self.kind == "polarity" else "a"
        return (
            f'The answer uses "{self.answer_value}", while the {self.source} uses '
            f'"{self.reference_value}"; this is {article} {labels[self.kind]} conflict.'
        )


@dataclass(frozen=True)
class EquivalentFact:
    """One normalized factual value shared by an answer and a reference."""

    kind: str
    answer_value: str
    reference_value: str
    source: str


@dataclass(frozen=True)
class ContradictionAnalysis:
    """Conflicts and normalized equivalences found against references."""

    expected_conflicts: tuple[Conflict, ...] = ()
    context_conflicts: tuple[Conflict, ...] = ()
    expected_equivalences: tuple[EquivalentFact, ...] = ()
    context_equivalences: tuple[EquivalentFact, ...] = ()

    @property
    def detected(self) -> bool:
        return bool(self.expected_conflicts or self.context_conflicts)

    @property
    def primary(self) -> Conflict | None:
        conflicts = self.expected_conflicts or self.context_conflicts
        return conflicts[0] if conflicts else None


@dataclass(frozen=True)
class _Facts:
    durations: dict[tuple[str, float], str]
    percentages: dict[float, str]
    temperatures: dict[tuple[str, float], str]
    storage: dict[tuple[str, float], str]
    dates: dict[object, str]
    numbers: dict[float, str]
    entities: dict[str, str]


def _parse_number(value: str) -> float:
    cleaned = value.lower().replace("-", " ").strip()
    try:
        return float(cleaned)
    except ValueError:
        parts = cleaned.split()
        if "hundred" in parts:
            leading = sum(_NUMBER_WORDS.get(part, 0) for part in parts if part != "hundred")
            return float(max(1, leading) * 100)
        return float(sum(_NUMBER_WORDS[part] for part in parts))


def _overlaps(span: tuple[int, int], consumed: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in consumed)


def _singular(unit: str) -> str:
    return unit.lower().removesuffix("s")


def _canonical_entity(value: str) -> str:
    normalized = re.sub(r"(?:'s|’s)$", "", value.casefold()).strip()
    normalized = re.sub(r"^(?:the|a|an)\s+", "", normalized)
    return _ENTITY_CANONICAL_FORMS.get(normalized, normalized)


def _acronym_equivalence(left: str, right: str) -> tuple[str, str] | None:
    """Find an all-caps abbreviation matching an expansion's initials."""

    def acronyms(text: str) -> list[str]:
        return re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", text)

    def expansion_for(acronym: str, text: str) -> str | None:
        words = re.findall(r"[A-Za-z]+", text)
        size = len(acronym)
        for start in range(len(words) - size + 1):
            candidate = words[start : start + size]
            if any(word.casefold() in _CONTENT_STOPWORDS for word in candidate):
                continue
            if "".join(word[0] for word in candidate).casefold() == acronym.casefold():
                return " ".join(candidate)
        return None

    for abbreviated_text, expanded_text, reversed_values in (
        (left, right, False),
        (right, left, True),
    ):
        for acronym in acronyms(abbreviated_text):
            expansion = expansion_for(acronym, expanded_text)
            if expansion:
                return (expansion, acronym) if reversed_values else (acronym, expansion)
    return None


def _extract_facts(text: str) -> _Facts:
    consumed: list[tuple[int, int]] = []
    durations: dict[tuple[str, float], str] = {}
    percentages: dict[float, str] = {}
    temperatures: dict[tuple[str, float], str] = {}
    storage: dict[tuple[str, float], str] = {}
    dates: dict[object, str] = {}
    numbers: dict[float, str] = {}

    for pattern in (_ISO_DATE_RE, _MONTH_FIRST_DATE_RE, _DAY_FIRST_DATE_RE):
        for match in pattern.finditer(text):
            if _overlaps(match.span(), consumed):
                continue
            month_value = match.group("month")
            month = (
                _MONTH_NUMBERS[month_value.casefold()]
                if not month_value.isdigit()
                else int(month_value)
            )
            normalized_date = (
                int(match.group("year")),
                month,
                int(match.group("day")),
            )
            dates.setdefault(normalized_date, match.group(0))
            consumed.append(match.span())

    for match in _DURATION_RE.finditer(text):
        value = _parse_number(match.group("value"))
        family, factor = _DURATION_FACTORS[_singular(match.group("unit"))]
        durations.setdefault((family, value * factor), match.group(0))
        consumed.append(match.span())

    for match in _PERCENT_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        percentages.setdefault(
            _parse_number(match.group("value")) / 100.0, match.group(0)
        )
        consumed.append(match.span())

    for match in _TEMPERATURE_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        unit = (match.group("word_unit") or match.group("symbol_unit")).casefold()
        normalized_unit = "celsius" if unit in {"c", "celsius"} else "fahrenheit"
        temperatures.setdefault(
            (normalized_unit, _parse_number(match.group("value"))), match.group(0)
        )
        consumed.append(match.span())

    for match in _FRACTION_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        normalized_fraction = re.sub(r"[-\s]+", " ", match.group(0).casefold())
        percentages.setdefault(
            _FRACTION_VALUES[normalized_fraction], match.group(0)
        )
        consumed.append(match.span())

    for match in _STORAGE_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        unit = _singular(match.group("unit"))
        storage.setdefault(
            (
                "binary",
                _parse_number(match.group("value")) * _STORAGE_FACTORS_KB[unit],
            ),
            match.group(0),
        )
        consumed.append(match.span())

    for match in _YEAR_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        dates.setdefault(("year", int(match.group(0))), match.group(0))
        consumed.append(match.span())

    for match in _NUMBER_RE.finditer(text):
        if _overlaps(match.span(), consumed):
            continue
        numbers.setdefault(_parse_number(match.group(0)), match.group(0))

    entities: dict[str, str] = {}
    for match in _ENTITY_RE.finditer(text):
        original = match.group(0).strip()
        normalized = _canonical_entity(original)
        if (
            normalized in _ENTITY_EXCLUSIONS
            or normalized in _NUMBER_WORDS
            or len(normalized) == 1
        ):
            continue
        entities.setdefault(normalized, original)

    return _Facts(
        durations, percentages, temperatures, storage, dates, numbers, entities
    )


def _value_comparison(
    answer_values: dict[object, str],
    reference_values: dict[object, str],
    kind: str,
    source: str,
) -> tuple[Conflict | None, EquivalentFact | None]:
    if not answer_values or not reference_values:
        return None, None
    shared = set(answer_values).intersection(reference_values)
    if shared:
        if set(answer_values) == set(reference_values):
            shared_key = next(iter(shared))
            return None, EquivalentFact(
                kind,
                answer_values[shared_key],
                reference_values[shared_key],
                source,
            )
        return None, None
    answer_key = next(iter(answer_values))
    reference_key = next(iter(reference_values))
    return (
        Conflict(
            kind,
            answer_values[answer_key],
            reference_values[reference_key],
            source,
        ),
        None,
    )


def _normalized_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"\b[a-z][a-z'-]*\b", text.casefold()))
    return {
        token.removesuffix("s") if len(token) > 4 else token
        for token in tokens
        if token not in _CONTENT_STOPWORDS
    }


def _entity_conflict(
    answer: str,
    reference: str,
    answer_facts: _Facts,
    reference_facts: _Facts,
    source: str,
) -> Conflict | None:
    answer_entities = answer_facts.entities
    reference_entities = reference_facts.entities
    if _acronym_equivalence(answer, reference):
        return None
    answer_text = re.sub(r"(?:'s|’s)\b", "", answer.casefold())
    reference_text = re.sub(r"(?:'s|’s)\b", "", reference.casefold())

    def mentioned(entity: str, text: str) -> bool:
        return bool(re.search(rf"\b{re.escape(entity)}\b", text))

    answer_only = [
        key
        for key in answer_entities
        if key not in reference_entities and not mentioned(key, reference_text)
    ]
    reference_only = [
        key
        for key in reference_entities
        if key not in answer_entities and not mentioned(key, answer_text)
    ]
    if not answer_only or not reference_only:
        return None

    shared_entities = set(answer_entities).intersection(reference_entities)
    shared_content = _normalized_tokens(answer).intersection(
        _normalized_tokens(reference)
    )
    short_values = len(_normalized_tokens(answer)) <= 4 and len(
        _normalized_tokens(reference)
    ) <= 4
    if not (shared_entities or shared_content or short_values):
        return None

    return Conflict(
        "named entity",
        answer_entities[answer_only[0]],
        reference_entities[reference_only[0]],
        source,
    )


def _polarity_conflict(answer: str, reference: str, source: str) -> Conflict | None:
    answer_lower = re.sub(r"n['’]t\b", " not", answer.casefold())
    reference_lower = re.sub(r"n['’]t\b", " not", reference.casefold())

    for positive, negative in _OPPOSITE_PAIRS:
        positive_re = rf"\b{re.escape(positive)}\b"
        negative_re = rf"\b{re.escape(negative)}\b"
        if re.search(positive_re, answer_lower) and re.search(negative_re, reference_lower):
            return Conflict("polarity", positive, negative, source)
        if re.search(negative_re, answer_lower) and re.search(positive_re, reference_lower):
            return Conflict("polarity", negative, positive, source)

    for negated_text, plain_text, reversed_values in (
        (answer_lower, reference_lower, False),
        (reference_lower, answer_lower, True),
    ):
        for match in re.finditer(r"\b(?:not|never)\s+([a-z]+)\b", negated_text):
            predicate = match.group(1)
            if predicate == "only" or not re.search(rf"\b{re.escape(predicate)}\b", plain_text):
                continue
            negative_value = match.group(0)
            if reversed_values:
                return Conflict("polarity", predicate, negative_value, source)
            return Conflict("polarity", negative_value, predicate, source)
    return None


def _compare(
    answer: str, reference: str, source: str
) -> tuple[tuple[Conflict, ...], tuple[EquivalentFact, ...]]:
    answer_facts = _extract_facts(answer)
    reference_facts = _extract_facts(reference)
    conflicts: list[Conflict] = []
    equivalences: list[EquivalentFact] = []

    for answer_values, reference_values, kind in (
        (answer_facts.durations, reference_facts.durations, "duration"),
        (answer_facts.percentages, reference_facts.percentages, "percentage"),
        (answer_facts.temperatures, reference_facts.temperatures, "temperature"),
        (answer_facts.storage, reference_facts.storage, "storage"),
        (answer_facts.dates, reference_facts.dates, "date"),
        (answer_facts.numbers, reference_facts.numbers, "number"),
    ):
        conflict, equivalence = _value_comparison(
            answer_values, reference_values, kind, source
        )
        if conflict:
            conflicts.append(conflict)
        if equivalence:
            equivalences.append(equivalence)

    answer_proportions = {
        key: value
        for key, value in answer_facts.numbers.items()
        if 0.0 <= key <= 1.0
    }
    reference_proportions = {
        key: value
        for key, value in reference_facts.numbers.items()
        if 0.0 <= key <= 1.0
    }
    for answer_values, reference_values in (
        (answer_facts.percentages, reference_proportions),
        (answer_proportions, reference_facts.percentages),
    ):
        if not answer_values or not reference_values:
            continue
        shared = set(answer_values).intersection(reference_values)
        if shared:
            shared_key = next(iter(shared))
            equivalences.append(
                EquivalentFact(
                    "percentage",
                    answer_values[shared_key],
                    reference_values[shared_key],
                    source,
                )
            )
        else:
            answer_key = next(iter(answer_values))
            reference_key = next(iter(reference_values))
            conflicts.append(
                Conflict(
                    "percentage",
                    answer_values[answer_key],
                    reference_values[reference_key],
                    source,
                )
            )

    polarity = _polarity_conflict(answer, reference, source)
    if polarity:
        conflicts.append(polarity)

    entity = _entity_conflict(
        answer, reference, answer_facts, reference_facts, source
    )
    if entity:
        conflicts.append(entity)

    shared_entities = set(answer_facts.entities).intersection(
        reference_facts.entities
    )
    if shared_entities:
        shared_entity = next(iter(shared_entities))
        equivalences.append(
            EquivalentFact(
                "named entity",
                answer_facts.entities[shared_entity],
                reference_facts.entities[shared_entity],
                source,
            )
        )

    acronym_match = _acronym_equivalence(answer, reference)
    if acronym_match:
        equivalences.append(
            EquivalentFact("abbreviation", *acronym_match, source)
        )

    for kind, abbreviated, expanded in _FACT_ALIASES:
        answer_abbreviated = abbreviated.search(answer)
        answer_expanded = expanded.search(answer)
        reference_abbreviated = abbreviated.search(reference)
        reference_expanded = expanded.search(reference)
        if (answer_abbreviated and reference_expanded) or (
            answer_expanded and reference_abbreviated
        ):
            answer_value = (
                answer_abbreviated.group(0)
                if answer_abbreviated
                else answer_expanded.group(0)
            )
            reference_value = (
                reference_abbreviated.group(0)
                if reference_abbreviated
                else reference_expanded.group(0)
            )
            equivalences.append(
                EquivalentFact(kind, answer_value, reference_value, source)
            )
    return tuple(conflicts), tuple(equivalences)


def matches_short_expected_value(answer: str, expected_answer: str | None) -> bool:
    """Return whether a short expected factual value is present in the answer.

    A match is accepted only when deterministic comparison finds no conflict
    with the expected answer. Typed values are compared in normalized form;
    concise textual values use content-token containment so they can appear in
    a longer answer.
    """

    if not expected_answer:
        return False
    expected_words = re.findall(r"\b[\w%°'-]+\b", expected_answer.casefold())
    expected_content = _normalized_tokens(expected_answer)
    if len(expected_words) > 8 or len(expected_content) > 5:
        return False

    conflicts, equivalences = _compare(
        answer, expected_answer, "expected answer"
    )
    if conflicts:
        return False

    answer_facts = _extract_facts(answer)
    expected_facts = _extract_facts(expected_answer)
    typed_groups = (
        (answer_facts.durations, expected_facts.durations),
        (answer_facts.percentages, expected_facts.percentages),
        (answer_facts.temperatures, expected_facts.temperatures),
        (answer_facts.storage, expected_facts.storage),
        (answer_facts.dates, expected_facts.dates),
        (answer_facts.numbers, expected_facts.numbers),
    )
    expected_typed_groups = [
        (answer_values, expected_values)
        for answer_values, expected_values in typed_groups
        if expected_values
    ]
    if expected_typed_groups and all(
        set(expected_values).issubset(answer_values)
        for answer_values, expected_values in expected_typed_groups
    ):
        return True

    if equivalences:
        return True

    answer_content = _normalized_tokens(answer)
    return bool(expected_content and expected_content.issubset(answer_content))


def detect_contradictions(
    answer: str,
    expected_answer: str | None = None,
    context: str | None = None,
) -> ContradictionAnalysis:
    """Compare an answer with available references for factual conflicts."""

    expected_comparison = (
        _compare(answer, expected_answer, "expected answer")
        if expected_answer
        else ((), ())
    )
    context_comparison = (
        _compare(answer, context, "context") if context else ((), ())
    )
    return ContradictionAnalysis(
        expected_conflicts=expected_comparison[0],
        context_conflicts=context_comparison[0],
        expected_equivalences=expected_comparison[1],
        context_equivalences=context_comparison[1],
    )
