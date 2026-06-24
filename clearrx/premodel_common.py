"""Common lexical utilities for ClearRx pre-model analysis."""

from __future__ import annotations

import re
from collections.abc import Iterable


DOMAIN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bnatural numbers?\b|\bnonnegative integers?\b|\bNat\b|[ℕ]", "Nat"),
    (r"\bintegers?\b|\bInt\b|[ℤ]", "Int"),
    (r"\brationals?\b|\bRat\b|[ℚ]", "Rat"),
    (r"\breals?\b|\breal numbers?\b|\bReal\b|[ℝ]", "Real"),
    (r"\bcomplex\b|\bcomplex numbers?\b|\bComplex\b|[ℂ]", "Complex"),
    (r"\bpolynomials?\b|\bMvPolynomial\b|\bPolynomial\b", "Polynomial"),
    (r"\bmatrices?\b|\bMatrix\b", "Matrix"),
    (r"\bvectors?\b|\bVector\b", "Vector"),
    (r"\blists?\b|\bList\b", "List"),
    (r"\bsets?\b|\bSet\b", "Set"),
    (r"\bfunctions?\b|\bmaps?\b|\bFunction\b", "Function"),
    (r"\bsequences?\b|\bseq\b", "Sequence"),
    (r"\bgroups?\b|\bGroup\b", "Group"),
    (r"\brings?\b|\bRing\b", "Ring"),
    (r"\bfields?\b|\bField\b", "Field"),
)

FUNCTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgcd\b|\bNat\.gcd\b", "gcd"),
    (r"\blcm\b|\bNat\.lcm\b", "lcm"),
    (r"\bsin\b", "sin"),
    (r"\bcos\b", "cos"),
    (r"\btan\b", "tan"),
    (r"\blog\b", "log"),
    (r"\bexp\b", "exp"),
    (r"\bfloor\b|⌊", "floor"),
    (r"\bceil\b|⌈", "ceil"),
    (r"\bmin\b", "min"),
    (r"\bmax\b", "max"),
    (r"\babs\b|absolute value|∣", "abs"),
    (r"\bcard\b|cardinality|Fintype\.card", "card"),
    (r"\bderiv\b|\bfderiv\b|derivative|differentiable|HasDeriv", "derivative"),
    (r"∫|integral|Integrable|IntervalIntegrable", "integral"),
    (r"∑|sum\b|Finset\.sum", "sum"),
    (r"∏|product\b|Finset\.prod", "product"),
    (r"\bmap\b|List\.map", "map"),
    (r"\blength\b|List\.length", "length"),
    (r"\bappend\b|\+\+", "append"),
    (r"\brange\b|Finset\.range|Icc|Ico|Ioc|Ioo", "range"),
)

OPERATOR_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"≤|<=|less than or equal|at most|no more than", "<="),
    (r"≥|>=|greater than or equal|at least|no less than", ">="),
    (r"(?<![<>=!])<(?![=>])|strictly less|less than", "<"),
    (r"(?<![<>=!])>(?![=>])|strictly greater|greater than", ">"),
    (r"=|equals?|equal to|same as", "="),
    (r"≠|!=|not equal|nonzero|non-zero", "!="),
    (r"∈| in |membership|belongs to", "in"),
    (r"⊆|subset", "subset"),
    (r"⊂|proper subset", "proper_subset"),
    (r"\+|plus|add", "+"),
    (r"-|minus|subtract|subtraction", "-"),
    (r"\*|times|multiply|product", "*"),
    (r"/|divide|quotient", "/"),
    (r"\^|power|exponent|squared|cubed", "^"),
    (r"∣|dvd|divides", "divides"),
    (r"%|mod|modulo", "mod"),
    (r"→|->|implies|if .* then", "implies"),
    (r"↔|iff|if and only if", "iff"),
    (r"∧| and |conjunction", "and"),
    (r"∨| or |disjunction", "or"),
    (r"¬|not |negation", "not"),
)

CONCEPT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"infinite|infinitely many|unbounded|tends to infinity", "infinity"),
    (r"maximum|maximal|minimum|minimal|supremum|infimum|least|greatest", "extremum"),
    (r"cardinality|cardinal|number of elements|finite", "cardinality"),
    (r"derivative|differentiable|integral|integrable|antiderivative", "calculus"),
    (r"angle|triangle|circle|line|parallel|perpendicular|collinear|distance|area|geometry", "geometry"),
)


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = str(item).strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def find_patterns(text: str, patterns: Iterable[tuple[str, str]], *, flags: int = re.I) -> list[str]:
    found: list[str] = []
    for pattern, label in patterns:
        if re.search(pattern, text, flags):
            found.append(label)
    return unique(found)


def constants(text: str) -> list[str]:
    return unique(re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])", text))


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def relation_constraint_label(text: str) -> str | None:
    compact = normalize_space(text)
    if not compact:
        return None
    if re.search(r"0\s*<|positive|Pos", compact, re.I):
        return "positive"
    if re.search(r"0\s*≤|0\s*<=|nonnegative|non-negative|Nonneg", compact, re.I):
        return "nonnegative"
    if re.search(r"≠\s*0|!=\s*0|nonzero|non-zero", compact, re.I):
        return "nonzero"
    if re.search(r"<|>|≤|≥|<=|>=", compact):
        return "bound"
    if re.search(r"∈|\bin\b|Mem|membership", compact, re.I):
        return "membership"
    if re.search(r"coprime|Coprime", compact, re.I):
        return "coprime"
    if re.search(r"Even|Odd|even|odd", compact):
        return "parity"
    if re.search(r"Distinct|Pairwise|NoDup|distinct", compact):
        return "distinctness"
    return None


def lean_type_to_domain(type_text: str) -> str | None:
    domains = find_patterns(type_text, DOMAIN_PATTERNS, flags=0)
    return domains[0] if domains else None
