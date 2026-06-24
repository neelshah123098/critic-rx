"""DeltaMap: compare informal intent and Lean proposition schemas."""

from __future__ import annotations

from .premodel_types import Delta, IntentSchema, LeanSchema, SourceFragment


def _set(items: list[str]) -> set[str]:
    return {item for item in items if item}


def _span_for(lean: LeanSchema, observed: str | None) -> SourceFragment | None:
    if observed and observed in lean.fragments:
        return lean.fragments[observed]
    if observed:
        for key, fragment in lean.fragments.items():
            if observed in key or observed in fragment.text:
                return fragment
    return lean.fragments.get("target")


def compare_quantifiers(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    iq = _set(intent.quantifiers)
    lean_text = f"{lean.raw_statement} {lean.target}"
    has_exists = "∃" in lean_text or "Exists" in lean_text
    has_forall = "∀" in lean_text or len(lean.variables) > 0
    if "forall" in iq and has_exists and not has_forall:
        deltas.append(
            Delta(
                kind="quantifier",
                expected="forall",
                observed="exists",
                category_hint="Quantifier Weakening",
                confidence=0.78,
                rationale="informal statement appears universal while Lean uses existential structure",
                span_hint=_span_for(lean, "∃"),
            )
        )
    if "exists" in iq and has_forall and not has_exists:
        deltas.append(
            Delta(
                kind="quantifier",
                expected="exists",
                observed="forall",
                category_hint="Quantifier Strengthening",
                confidence=0.78,
                rationale="informal statement appears existential while Lean is binder/universal shaped",
                span_hint=lean.fragments.get("target"),
            )
        )
    return deltas


def compare_domains(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    idom = _set(intent.domains)
    ldom = _set(lean.domains)
    if not idom or not ldom or idom & ldom:
        return []
    return [
        Delta(
            kind="domain",
            expected=", ".join(sorted(idom)),
            observed=", ".join(sorted(ldom)),
            category_hint="Object Type Error",
            confidence=0.7,
            rationale="informal and Lean statements mention disjoint mathematical domains",
            span_hint=lean.fragments.get("target"),
        )
    ]


def compare_constraints(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    expected = _set(intent.constraints)
    observed = _set(lean.constraints)
    for item in sorted(expected - observed):
        category = {
            "positive": "Positivity Constraint Error",
            "nonnegative": "Positivity Constraint Error",
            "bound": "Bound Constraint Error",
            "membership": "Variable Constraint Error",
            "nonzero": "Variable Constraint Error",
            "distinctness": "Variable Constraint Error",
            "coprime": "Variable Constraint Error",
            "parity": "Variable Constraint Error",
        }.get(item, "Missing Premise")
        deltas.append(
            Delta(
                kind="missing_constraint",
                expected=item,
                observed=None,
                category_hint=category,
                confidence=0.62,
                rationale=f"informal statement mentions {item} constraint not visible in Lean binders",
                span_hint=lean.fragments.get("target"),
            )
        )
    for item in sorted(observed - expected):
        deltas.append(
            Delta(
                kind="extra_constraint",
                expected=None,
                observed=item,
                category_hint="Redundant Premise",
                confidence=0.48,
                rationale=f"Lean statement contains {item} constraint not detected in informal statement",
                span_hint=lean.fragments.get("target"),
            )
        )
    return deltas


def compare_functions(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    expected = _set(intent.functions)
    observed = _set(lean.functions)
    if not expected or not observed:
        return deltas
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing and extra:
        deltas.append(
            Delta(
                kind="function",
                expected=missing[0],
                observed=extra[0],
                category_hint="Function Confusion",
                confidence=0.66,
                rationale="informal and Lean statements emphasize different named functions",
                span_hint=_span_for(lean, extra[0]),
            )
        )
    return deltas


def compare_operators(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    expected = _set(intent.operators)
    observed = _set(lean.operators)
    order_ops = {"<", "<=", ">", ">="}
    logical_ops = {"and", "or", "implies", "iff", "not"}
    if expected & order_ops and observed & order_ops and not (expected & observed & order_ops):
        deltas.append(
            Delta(
                kind="order",
                expected=", ".join(sorted(expected & order_ops)),
                observed=", ".join(sorted(observed & order_ops)),
                category_hint="(Partial) Order Error",
                confidence=0.72,
                rationale="order relation detected in both statements but relation polarity/strictness differs",
                span_hint=_span_for(lean, next(iter(observed & order_ops), None)),
            )
        )
    if expected & logical_ops and observed & logical_ops and not (expected & observed & logical_ops):
        deltas.append(
            Delta(
                kind="logical_connective",
                expected=", ".join(sorted(expected & logical_ops)),
                observed=", ".join(sorted(observed & logical_ops)),
                category_hint="Logical Connective Misuse",
                confidence=0.67,
                rationale="both statements expose logical connectives but the connective family differs",
                span_hint=lean.fragments.get("target"),
            )
        )
    for op in sorted((expected - observed) - order_ops - logical_ops):
        category = {
            "^": "Exponent/Power Error",
            "+": "Operator Confusion",
            "-": "Operator Confusion",
            "*": "Operator Confusion",
            "/": "Operator Confusion",
            "mod": "Operator Confusion",
            "divides": "Operator Confusion",
            "subset": "Operator Confusion",
            "in": "Operator Confusion",
        }.get(op, "Operator Confusion")
        deltas.append(
            Delta(
                kind="operator_missing_or_changed",
                expected=op,
                observed=None,
                category_hint=category,
                confidence=0.5,
                rationale=f"operator/concept {op} appears in informal statement but not Lean surface",
                span_hint=lean.fragments.get("target"),
            )
        )
    return deltas


def compare_lean_specific(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    lean_text = f"{lean.raw_statement} {lean.target}"
    has_nat = "Nat" in lean.domains
    if has_nat and ("/" in lean.operators or "-" in lean.operators or "Nat.div" in lean_text or "Nat.sub" in lean_text):
        observed = "/" if "/" in lean.operators or "Nat.div" in lean_text else "-"
        deltas.append(
            Delta(
                kind="lean_truncation",
                expected="mathematical integer/rational arithmetic",
                observed=f"Nat {observed} semantics",
                category_hint="Truncation Error",
                confidence=0.68,
                rationale="Lean Nat division/subtraction can silently truncate or floor compared with informal arithmetic",
                span_hint=_span_for(lean, observed),
            )
        )
    if "range" in lean.functions and "range" not in intent.functions:
        deltas.append(
            Delta(
                kind="range",
                expected=None,
                observed="range",
                category_hint="Range Error",
                confidence=0.52,
                rationale="Lean uses an explicit indexed range not clearly mirrored in informal surface text",
                span_hint=_span_for(lean, "range"),
            )
        )
    return deltas


def compare_constants(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    expected = _set(intent.constants)
    observed = _set(lean.constants)
    if not expected or not observed or expected == observed:
        return []
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if not missing or not extra:
        return []
    return [
        Delta(
            kind="constant",
            expected=missing[0],
            observed=extra[0],
            category_hint="Coefficient/Constant Error",
            confidence=0.64,
            rationale="different numeric constants detected between informal and Lean statements",
            span_hint=_span_for(lean, extra[0]),
        )
    ]


def compare_concepts(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    expected = _set(intent.concepts)
    observed = _set(lean.concepts)
    for concept in sorted(expected - observed):
        category = {
            "infinity": "Infinity Misinterpretation",
            "extremum": "Extremum Concept Error",
            "cardinality": "Cardinality Error",
            "calculus": "Integration/Diff. Confusion",
            "geometry": "Geometric Error",
        }.get(concept, "Conclusion Error")
        deltas.append(
            Delta(
                kind="concept",
                expected=concept,
                observed=None,
                category_hint=category,
                confidence=0.58,
                rationale=f"informal concept {concept} is not visible in Lean surface features",
                span_hint=lean.fragments.get("target"),
            )
        )
    return deltas


def generic_conclusion_delta(intent: IntentSchema, lean: LeanSchema, deltas: list[Delta]) -> list[Delta]:
    if deltas:
        return []
    if not intent.conclusion or not lean.target:
        return []
    intent_terms = _set(intent.functions + intent.operators + intent.constants + intent.concepts)
    lean_terms = _set(lean.functions + lean.operators + lean.constants + lean.concepts)
    if intent_terms and lean_terms and intent_terms != lean_terms:
        return [
            Delta(
                kind="conclusion",
                expected=intent.conclusion[:160],
                observed=lean.target[:160],
                category_hint="Conclusion Error",
                confidence=0.42,
                rationale="surface theorem atoms differ but no specific mismatch dominated",
                span_hint=lean.fragments.get("target"),
            )
        ]
    return []


def compute_deltas(intent: IntentSchema, lean: LeanSchema) -> list[Delta]:
    deltas: list[Delta] = []
    for fn in (
        compare_quantifiers,
        compare_domains,
        compare_constraints,
        compare_functions,
        compare_operators,
        compare_constants,
        compare_concepts,
        compare_lean_specific,
    ):
        deltas.extend(fn(intent, lean))
    deltas.extend(generic_conclusion_delta(intent, lean, deltas))
    deltas.sort(key=lambda delta: delta.confidence, reverse=True)
    return deltas
