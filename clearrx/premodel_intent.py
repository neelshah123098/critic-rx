"""IntentLens: heuristic reconstruction of the informal theorem."""

from __future__ import annotations

import re

from .premodel_common import (
    CONCEPT_PATTERNS,
    DOMAIN_PATTERNS,
    FUNCTION_PATTERNS,
    OPERATOR_PATTERNS,
    constants,
    find_patterns,
    normalize_space,
    relation_constraint_label,
    unique,
)
from .premodel_types import IntentSchema


QUANTIFIER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bfor all\b|\bfor every\b|\bevery\b|\beach\b|\bany\b|\ball\b", "forall"),
    (r"\bthere exists\b|\bexists\b|\bsome\b|\bthere is\b", "exists"),
    (r"\bunique\b|\bexactly one\b", "unique"),
    (r"\bat least one\b", "exists"),
    (r"\bat most one\b", "at_most_one"),
)


def extract_variables(text: str) -> list[str]:
    candidates: list[str] = []
    patterns = [
        r"\b(?:number|integer|real|complex|natural|function|sequence|set|list|matrix|polynomial)\s+([a-zA-Z][a-zA-Z0-9_]*)\b",
        r"\b(?:variable|variables|let|given)\s+([a-zA-Z][a-zA-Z0-9_]*)\b",
        r"\bfor (?:all|every|each|any)\s+([a-zA-Z][a-zA-Z0-9_]*)\b",
        r"\b([a-zA-Z][a-zA-Z0-9_]*)\s*(?:is|are)\s+(?:positive|nonnegative|nonzero|an?|a)\b",
    ]
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text, flags=re.I))
    math_vars = re.findall(r"\b([a-z])\b\s*(?:[<>=≤≥≠]|∈)", text)
    candidates.extend(math_vars)
    return unique(candidates)


def extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    phrase_patterns = (
        (r"positive", "positive"),
        (r"nonnegative|non-negative", "nonnegative"),
        (r"nonzero|non-zero|not zero", "nonzero"),
        (r"bounded|at least|at most|less than|greater than|between", "bound"),
        (r"belongs to|member of|in the set|∈", "membership"),
        (r"coprime|relatively prime", "coprime"),
        (r"even|odd", "parity"),
        (r"distinct|different from|pairwise", "distinctness"),
    )
    constraints.extend(find_patterns(text, phrase_patterns))
    for fragment in re.findall(r"[^.;,]*(?:≤|>=|≥|<=|<|>|≠|!=|∈)[^.;,]*", text):
        label = relation_constraint_label(fragment)
        if label:
            constraints.append(label)
    return unique(constraints)


def extract_conclusion(text: str) -> str:
    patterns = [
        r"\bthen\b(.+)$",
        r"\bshow that\b(.+)$",
        r"\bprove that\b(.+)$",
        r"\bwe have\b(.+)$",
        r"\bimplies that\b(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            return normalize_space(match.group(1))
    parts = re.split(r"\b(?:such that|where|with)\b", text, maxsplit=1, flags=re.I)
    return normalize_space(parts[-1] if parts else text)


def analyze_intent(informal_statement: str) -> IntentSchema:
    text = informal_statement or ""
    return IntentSchema(
        quantifiers=find_patterns(text, QUANTIFIER_PATTERNS),
        variables=extract_variables(text),
        domains=find_patterns(text, DOMAIN_PATTERNS),
        constraints=extract_constraints(text),
        functions=find_patterns(text, FUNCTION_PATTERNS),
        operators=find_patterns(text, OPERATOR_PATTERNS),
        constants=constants(text),
        concepts=find_patterns(text, CONCEPT_PATTERNS),
        conclusion=extract_conclusion(text),
        raw_statement=text,
    )

