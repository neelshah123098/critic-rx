"""FormalRx SCI-28 taxonomy focus for rich prompt augmentation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .taxonomy import SCI_28_CATEGORIES


@dataclass(frozen=True)
class TaxonomyEntry:
    code: str
    name: str
    dimension: str
    short_definition: str
    disambiguation: str = ""


@dataclass
class TaxonomyCandidate:
    code: str
    name: str
    dimension: str
    score: float
    short_definition: str
    evidence: list[str] = field(default_factory=list)
    disambiguation: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = round(self.score, 4)
        return data


SCI_TAXONOMY: tuple[TaxonomyEntry, ...] = (
    TaxonomyEntry("S1.1", "Quantifier Strengthening", "Semantic", "Quantifier or domain changes make the formal claim stronger than the informal claim."),
    TaxonomyEntry("S1.2", "Quantifier Weakening", "Semantic", "Quantifier or domain changes make the formal claim weaker than the informal claim."),
    TaxonomyEntry("S1.3", "Logical Connective Misuse", "Semantic", "Logical connectives such as and, or, implies, iff, or not are misused."),
    TaxonomyEntry("S2.1", "Object Type Error", "Semantic", "The mathematical object type or algebraic structure is incorrectly stated.", "Use Domain Constraint Error for basic domain restrictions without structural algebraic change."),
    TaxonomyEntry("S2.2", "Function Confusion", "Semantic", "A named mathematical function is substituted for another.", "Use Operator Confusion for symbolic arithmetic operators such as +, *, /, mod, subset, or divides."),
    TaxonomyEntry("S2.3", "Operator Confusion", "Semantic", "Arithmetic or algebraic operators are substituted or modified.", "Use Function Confusion for named functions; use Exponent/Power Error for exponent-only changes."),
    TaxonomyEntry("S2.4", "Exponent/Power Error", "Semantic", "Polynomial degrees, exponents, or powers are incorrect."),
    TaxonomyEntry("S2.5", "Coefficient/Constant Error", "Semantic", "Coefficients, multipliers, constants, or unit conversions are incorrect."),
    TaxonomyEntry("S2.6", "Index/Subscript Error", "Semantic", "Indices or subscripts reference the wrong element in an indexed object.", "Use Range Error for Finset.range/List.range boundary mistakes."),
    TaxonomyEntry("S2.7", "(Partial) Order Error", "Semantic", "Order-like relations are reversed, loosened, tightened, or otherwise altered."),
    TaxonomyEntry("S3.1", "Infinity Misinterpretation", "Semantic", "Infinitude is formalized as the wrong quantifier or cardinality structure."),
    TaxonomyEntry("S3.2", "Extremum Concept Error", "Semantic", "Minimum/maximum attainment is confused with a mere bound."),
    TaxonomyEntry("S3.3", "Cardinality Error", "Semantic", "Set size or counting meaning is misrepresented."),
    TaxonomyEntry("S3.4", "Integration/Diff. Confusion", "Semantic", "Integration, differentiation, or antiderivative relationships are confused."),
    TaxonomyEntry("S3.5", "Geometric Error", "Semantic", "Geometric objects, relations, or constructions are incorrectly selected."),
    TaxonomyEntry("C1.1", "Positivity Constraint Error", "Constraint", "Positivity constraints are missing, redundant, or incorrect."),
    TaxonomyEntry("C1.2", "Bound Constraint Error", "Constraint", "Non-positivity bounds or thresholds are missing, redundant, or incorrect."),
    TaxonomyEntry("C1.3", "Domain Constraint Error", "Constraint", "A basic domain or definitional validity condition is wrong without deeper algebraic structure change.", "Use Object Type Error for algebraic structure changes such as Group/Ring/Field/PID/UFD."),
    TaxonomyEntry("C1.4", "Variable Constraint Error", "Constraint", "Variable constraints not covered by positivity, bound, or domain constraints are wrong."),
    TaxonomyEntry("C2.1", "Range Shift", "Constraint", "An index range is shifted by a constant offset while preserving a similar size."),
    TaxonomyEntry("C2.2", "Range Error", "Constraint", "An index range has the wrong size, boundary, finite/infinite extent, or off-by-one behavior.", "Use Range Shift for pure constant-offset shifts."),
    TaxonomyEntry("C3.1", "Missing Premise", "Constraint", "A necessary assumption is absent from the formal statement."),
    TaxonomyEntry("C3.2", "Redundant Premise", "Constraint", "An unnecessary premise is added to the formal statement."),
    TaxonomyEntry("C3.3", "Incorrect Premise", "Constraint", "An existing premise is changed incorrectly."),
    TaxonomyEntry("C4", "Conclusion Error", "Constraint", "The statement goal or conclusion is incorrect.", "Use this as a lower-priority catch-all when no specific semantic, implementation, or constraint category fits."),
    TaxonomyEntry("C5", "Auxiliary Construction Error", "Constraint", "A helper definition, lemma, structure, or local construction is wrong."),
    TaxonomyEntry("I1", "Truncation Error", "Implementation", "Lean discrete-type arithmetic such as Nat division or subtraction changes the intended mathematical value."),
    TaxonomyEntry("I2", "Operator Precedence Error", "Implementation", "Missing or wrong parentheses change parse order and expression semantics."),
)

ENTRY_BY_NAME = {entry.name: entry for entry in SCI_TAXONOMY}

if tuple(entry.name for entry in SCI_TAXONOMY) != SCI_28_CATEGORIES:
    raise RuntimeError("SCI taxonomy definitions must match SCI_28_CATEGORIES")


def _items(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value is None:
        return []
    return [str(value)]


def _set(value: object) -> set[str]:
    return {item for item in _items(value) if item}


def _short(value: object, limit: int = 140) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _surface_operators(text: object) -> set[str]:
    value = str(text or "")
    tokens = set(re.findall(r"<=|>=|!=|=|<|>|\+|-|\*|/|\^|↔|→|∧|∨|¬", value))
    word_ops = {
        "times": "*",
        "product": "*",
        "sum": "+",
        "plus": "+",
        "minus": "-",
        "divides": "divides",
        "subset": "subset",
        "iff": "iff",
    }
    lower = value.lower()
    for word, op in word_ops.items():
        if re.search(rf"\b{re.escape(word)}\b", lower):
            tokens.add(op)
    return tokens


def _add(
    scores: dict[str, float],
    reasons: dict[str, list[str]],
    category: str,
    amount: float,
    reason: str,
) -> None:
    if category not in ENTRY_BY_NAME:
        return
    scores[category] = scores.get(category, 0.0) + amount
    if reason:
        reasons.setdefault(category, [])
        if reason not in reasons[category]:
            reasons[category].append(reason)


def _join_categories(names: Iterable[str]) -> str:
    return "; ".join(names)


def taxonomy_checklist_by_dimension() -> dict[str, str]:
    grouped: dict[str, list[str]] = {"Semantic": [], "Constraint": [], "Implementation": []}
    for entry in SCI_TAXONOMY:
        grouped[entry.dimension].append(f"{entry.code} {entry.name}")
    return {dimension: _join_categories(names) for dimension, names in grouped.items()}


def score_taxonomy_candidates(evidence: dict[str, Any], *, top_k: int = 5) -> dict[str, Any]:
    """Rank SCI-28 categories from row-local evidence without producing a verdict."""

    intent = evidence.get("informal_intent_cues", {})
    lean = evidence.get("lean_statement_cues", {})
    checkpoints = evidence.get("semantic_checkpoints", [])
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    for checkpoint in checkpoints:
        category = str(checkpoint.get("sci_category_to_check") or "")
        confidence = float(checkpoint.get("confidence") or 0.0)
        expected = _short(checkpoint.get("expected_cue"), 80)
        observed = _short(checkpoint.get("observed_cue"), 80)
        rationale = _short(checkpoint.get("rationale"), 120)
        reason = f"DeltaMap checkpoint: expected={expected or 'none'}; observed={observed or 'none'}; {rationale}"
        _add(scores, reasons, category, 2.0 + confidence, reason)

    intent_ops = _set(intent.get("operators"))
    lean_ops = _set(lean.get("operators"))
    intent_functions = _set(intent.get("functions"))
    lean_functions = _set(lean.get("functions"))
    intent_constraints = _set(intent.get("constraints"))
    lean_constraints = _set(lean.get("constraints"))
    intent_domains = _set(intent.get("domains"))
    lean_domains = _set(lean.get("domains"))
    intent_constants = _set(intent.get("constants"))
    lean_constants = _set(lean.get("constants"))
    concepts = _set(intent.get("concepts")) | _set(lean.get("concepts"))
    conclusion = str(intent.get("conclusion_surface") or "")
    target = str(lean.get("target_surface") or "")

    arithmetic_ops = {"+", "-", "*", "/", "mod", "divides", "subset", "in"}
    order_ops = {"<", "<=", ">", ">=", "=", "!="}
    logical_ops = {"and", "or", "implies", "iff", "not"}

    if intent_ops & arithmetic_ops and lean_ops & arithmetic_ops and not (intent_ops & lean_ops & arithmetic_ops):
        _add(scores, reasons, "Operator Confusion", 1.7, "Informal and Lean surfaces emphasize different arithmetic/algebraic operators.")
    elif intent_ops & arithmetic_ops and (intent_ops & arithmetic_ops) - lean_ops:
        _add(scores, reasons, "Operator Confusion", 0.9, "Some informal arithmetic/algebraic operators are not visible in the Lean cues.")

    conclusion_ops = _surface_operators(conclusion) & arithmetic_ops
    target_ops = _surface_operators(target) & arithmetic_ops
    if conclusion_ops and target_ops and conclusion_ops != target_ops:
        _add(
            scores,
            reasons,
            "Operator Confusion",
            3.6,
            f"Informal conclusion operators {sorted(conclusion_ops)} differ from Lean target operators {sorted(target_ops)}.",
        )

    if intent_ops & order_ops and lean_ops & order_ops and not (intent_ops & lean_ops & order_ops):
        _add(scores, reasons, "(Partial) Order Error", 1.5, "Order-like relation cues differ between informal and Lean surfaces.")

    if intent_ops & logical_ops and lean_ops & logical_ops and not (intent_ops & lean_ops & logical_ops):
        _add(scores, reasons, "Logical Connective Misuse", 1.4, "Logical connective families differ between informal and Lean surfaces.")

    if intent_functions and lean_functions and intent_functions != lean_functions:
        _add(scores, reasons, "Function Confusion", 1.3, "Named function cues differ between informal and Lean surfaces.")

    if intent_constants and lean_constants and intent_constants != lean_constants:
        _add(scores, reasons, "Coefficient/Constant Error", 1.3, "Numeric constants differ between informal and Lean surfaces.")

    if intent_domains and lean_domains and not (intent_domains & lean_domains):
        _add(scores, reasons, "Object Type Error", 0.8, "Informal and Lean domain/type cues appear disjoint.")
        _add(scores, reasons, "Domain Constraint Error", 0.5, "Domain/type mismatch may be a basic validity constraint rather than structural object change.")

    missing_constraints = intent_constraints - lean_constraints
    extra_constraints = lean_constraints - intent_constraints
    if {"positive", "nonnegative"} & (missing_constraints | extra_constraints):
        _add(scores, reasons, "Positivity Constraint Error", 1.2, "Positivity/nonnegativity constraint cues differ.")
    if "bound" in missing_constraints or "bound" in extra_constraints:
        _add(scores, reasons, "Bound Constraint Error", 1.2, "Bound constraint cues differ.")
    variable_constraint_cues = {"membership", "nonzero", "distinctness", "coprime", "parity"}
    if variable_constraint_cues & (missing_constraints | extra_constraints):
        _add(scores, reasons, "Variable Constraint Error", 1.0, "Variable-side constraint cues differ.")

    if "range" in intent_functions or "range" in lean_functions or "range" in target:
        _add(scores, reasons, "Range Error", 0.9, "Range-related surface cue appears in the row.")
    if any(token in target for token in ("+ 1", "- 1", "succ", "pred")) and "range" in target:
        _add(scores, reasons, "Range Shift", 0.9, "Range expression appears with a constant shift cue.")

    if "^" in intent_ops or "^" in lean_ops or "pow" in target:
        _add(scores, reasons, "Exponent/Power Error", 0.5, "Power/exponent cue appears and should be checked if the exponent differs.")
    if any(token in target for token in ("[", "]")):
        _add(scores, reasons, "Index/Subscript Error", 0.4, "Indexed expression cue appears in the Lean target.")

    concept_to_category = {
        "infinity": "Infinity Misinterpretation",
        "extremum": "Extremum Concept Error",
        "cardinality": "Cardinality Error",
        "calculus": "Integration/Diff. Confusion",
        "geometry": "Geometric Error",
    }
    for concept, category in concept_to_category.items():
        if concept in concepts:
            _add(scores, reasons, category, 1.1, f"{concept} concept cue appears in informal or Lean features.")

    if "Nat" in lean_domains and ({"/", "-"} & lean_ops or "Nat.div" in target or "Nat.sub" in target):
        _add(scores, reasons, "Truncation Error", 1.4, "Lean Nat arithmetic cue may truncate subtraction or division.")
    if any(token in target for token in ("(", ")")) and len(lean_ops & arithmetic_ops) >= 2:
        _add(scores, reasons, "Operator Precedence Error", 0.35, "Expression contains multiple operators and parentheses; precedence should be checked if a parse mismatch is suspected.")

    if checkpoints and "Conclusion Error" not in scores:
        _add(scores, reasons, "Conclusion Error", 0.25, "Fallback only: use if the mismatch is in the goal and no specific category fits better.")

    ranked = sorted(scores.items(), key=lambda item: (-item[1], ENTRY_BY_NAME[item[0]].code))
    candidates = []
    for name, score in ranked[:top_k]:
        entry = ENTRY_BY_NAME[name]
        candidates.append(
            TaxonomyCandidate(
                code=entry.code,
                name=entry.name,
                dimension=entry.dimension,
                score=score,
                short_definition=entry.short_definition,
                evidence=reasons.get(name, [])[:4],
                disambiguation=entry.disambiguation,
            ).to_dict()
        )

    return {
        "all_categories_by_dimension": taxonomy_checklist_by_dimension(),
        "likely_categories": candidates,
        "priority_rules": [
            "Choose by error nature before code location.",
            "Prefer specific Semantic or Implementation categories over catch-all premise/conclusion categories.",
            "Use C3 premise categories for assumptions; use C4 only for goal/conclusion errors without a more specific nature.",
            "Use the exact SCI-28 category name if misaligned; use null/N/A diagnosis fields if aligned.",
            "Treat generated category hints as non-authoritative; the original row is the source of truth.",
        ],
        "disambiguation_rules": [
            "Function Confusion is for named mathematical functions; Operator Confusion is for symbolic operators.",
            "Object Type Error is for algebraic/object-structure changes; Domain Constraint Error is for basic domain validity constraints.",
            "Range Shift is a constant offset; Range Error changes the size, boundary, or finite/infinite extent.",
            "Coefficient/Constant Error covers wrong numbers and unit conversions; Cardinality Error covers wrong set-size meaning.",
            "Conclusion Error is a fallback after checking more specific semantic, implementation, and constraint categories.",
        ],
    }
