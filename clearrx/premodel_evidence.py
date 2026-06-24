"""Neutral pre-model evidence composer for system-prompt augmentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .premodel_delta import compute_deltas
from .premodel_intent import analyze_intent
from .premodel_lean import analyze_lean
from .prompting import FormalRxRow
from .taxonomy_lens import score_taxonomy_candidates


@dataclass
class EvidenceBundle:
    idx: str
    evidence: dict[str, Any]
    system_prompt_block: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "idx": self.idx,
            "evidence": self.evidence,
            "system_prompt_block": self.system_prompt_block,
        }


def _small_list(items: list[str], limit: int = 12) -> list[str]:
    return [item for item in items if item][:limit]


def _short(text: object, limit: int = 180) -> str:
    value = str(text or "").replace("\n", " ").strip()
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _csv(items: Iterable[object], *, limit: int = 8, empty: str = "none") -> str:
    values = [_short(item, 60) for item in items if str(item or "").strip()]
    if not values:
        return empty
    if len(values) > limit:
        values = values[:limit] + [f"+{len(values) - limit} more"]
    return ", ".join(values)


def _binder_summary(binders: list[dict[str, str]], *, limit: int = 5) -> str:
    parts = []
    for binder in binders[:limit]:
        names = _short(binder.get("names", ""), 40)
        type_text = _short(binder.get("type", ""), 90)
        kind = _short(binder.get("kind", ""), 24)
        if type_text:
            parts.append(f"{names} : {type_text} ({kind})")
        elif names:
            parts.append(f"{names} ({kind})")
    if len(binders) > limit:
        parts.append(f"+{len(binders) - limit} more")
    return _csv(parts, limit=limit + 1)


def _fragment_dict(fragment: Any) -> dict[str, Any] | None:
    if fragment is None:
        return None
    return {
        "text": fragment.text,
        "start": fragment.start,
        "end": fragment.end,
        "source": fragment.source,
    }


def build_evidence(row_mapping: Mapping[str, object], *, max_deltas: int = 8) -> dict[str, Any]:
    """Build row-local, non-authoritative evidence for the final critic.

    This function deliberately avoids final labels such as verdict_guess. It
    produces observations and checkpoints only.
    """

    row = FormalRxRow.from_mapping(row_mapping)
    intent = analyze_intent(row.informal_statement)
    lean = analyze_lean(row.header, row.formal_statement)
    deltas = compute_deltas(intent, lean)[:max_deltas]

    candidate_fragments = []
    for key, fragment in lean.fragments.items():
        if key == "target" or key.startswith("hypothesis:"):
            candidate_fragments.append({"label": key, **fragment.to_dict()})
    candidate_fragments = candidate_fragments[:10]

    checkpoints = []
    for delta in deltas:
        checkpoints.append(
            {
                "kind": delta.kind,
                "expected_cue": delta.expected,
                "observed_cue": delta.observed,
                "sci_category_to_check": delta.category_hint,
                "confidence": round(delta.confidence, 4),
                "rationale": delta.rationale,
                "candidate_span": _fragment_dict(delta.span_hint),
            }
        )

    return {
        "informal_intent_cues": {
            "quantifiers": _small_list(intent.quantifiers),
            "variables": _small_list(intent.variables),
            "domains": _small_list(intent.domains),
            "constraints": _small_list(intent.constraints),
            "functions": _small_list(intent.functions),
            "operators": _small_list(intent.operators),
            "constants": _small_list(intent.constants),
            "concepts": _small_list(intent.concepts),
            "conclusion_surface": intent.conclusion[:600],
        },
        "lean_statement_cues": {
            "declaration_kind": lean.declaration_kind,
            "declaration_name": lean.declaration_name,
            "variables": _small_list(lean.variables),
            "domains": _small_list(lean.domains),
            "constraints": _small_list(lean.constraints),
            "functions": _small_list(lean.functions),
            "operators": _small_list(lean.operators),
            "constants": _small_list(lean.constants),
            "concepts": _small_list(lean.concepts),
            "target_surface": lean.target[:800],
            "binders": lean.binders[:12],
            "hypotheses": lean.hypotheses[:12],
        },
        "candidate_lean_fragments": candidate_fragments,
        "semantic_checkpoints": checkpoints,
        "repair_guidance": [
            "If aligned, ignore checkpoint noise and return aligned with null diagnosis fields.",
            "If misaligned, choose the most specific SCI category supported by the row.",
            "Localize the smallest Lean fragment that must change.",
            "Prefer a local repair that preserves the candidate theorem structure.",
            "If this generated evidence conflicts with the original row, trust the original row.",
        ],
    }


def render_system_prompt_block(evidence: dict[str, Any]) -> str:
    """Render the final SCI-28-aware evidence block for the model prompt."""

    intent = evidence.get("informal_intent_cues", {})
    lean = evidence.get("lean_statement_cues", {})
    taxonomy_focus = evidence.get("taxonomy_focus") or score_taxonomy_candidates(evidence)
    categories = taxonomy_focus.get("all_categories_by_dimension", {})
    likely_categories = taxonomy_focus.get("likely_categories", [])

    lines = [
        "# Row-Local Premodel Evidence",
        "This block is generated from only the current row. It is non-authoritative.",
        "Trust the original informal statement, header/context, and Lean formal_statement if any generated cue conflicts.",
        "",
        "## SCI-28 Valid Category Checklist",
        f"Semantic: {categories.get('Semantic', 'none')}",
        f"Constraint: {categories.get('Constraint', 'none')}",
        f"Implementation: {categories.get('Implementation', 'none')}",
        "",
        "## Row Evidence Summary",
        (
            "Informal intent cues: "
            f"quantifiers={_csv(intent.get('quantifiers', []), limit=10)}; "
            f"domains={_csv(intent.get('domains', []), limit=10)}; "
            f"constraints={_csv(intent.get('constraints', []), limit=10)}; "
            f"functions={_csv(intent.get('functions', []), limit=10)}; "
            f"operators={_csv(intent.get('operators', []), limit=12)}; "
            f"constants={_csv(intent.get('constants', []), limit=10)}; "
            f"concepts={_csv(intent.get('concepts', []), limit=10)}."
        ),
        (
            "Lean statement cues: "
            f"decl={_short(lean.get('declaration_kind', ''), 24)} "
            f"{_short(lean.get('declaration_name', ''), 64)}; "
            f"variables={_csv(lean.get('variables', []), limit=10)}; "
            f"domains={_csv(lean.get('domains', []), limit=10)}; "
            f"constraints={_csv(lean.get('constraints', []), limit=10)}; "
            f"functions={_csv(lean.get('functions', []), limit=10)}; "
            f"operators={_csv(lean.get('operators', []), limit=14)}; "
            f"constants={_csv(lean.get('constants', []), limit=10)}; "
            f"concepts={_csv(lean.get('concepts', []), limit=10)}."
        ),
        f"Lean binders/hypotheses: {_binder_summary(lean.get('binders', []), limit=8)}.",
        f"Informal conclusion cue: {_short(intent.get('conclusion_surface', ''), 360)}",
        f"Lean target cue: {_short(lean.get('target_surface', ''), 420)}",
        "",
        "## Likely SCI Categories To Inspect",
    ]

    if likely_categories:
        for item in likely_categories:
            lines.append(
                f"- {item.get('code')} {item.get('name')} ({item.get('dimension')}): "
                f"{item.get('short_definition')}"
            )
            for reason in item.get("evidence", [])[:3]:
                lines.append(f"  Evidence: {_short(reason, 220)}")
            if item.get("disambiguation"):
                lines.append(f"  Disambiguation: {_short(item.get('disambiguation'), 220)}")
    else:
        lines.append("- No strong taxonomy shortlist was generated; use the SCI-28 checklist above.")

    lines.extend(
        [
            "",
            "## FormalRx Priority And Disambiguation Rules",
        ]
    )
    for rule in taxonomy_focus.get("priority_rules", []):
        lines.append(f"- {rule}")
    for rule in taxonomy_focus.get("disambiguation_rules", []):
        lines.append(f"- {rule}")

    lines.extend(
        [
            "",
            "## Final Decision Rule",
            "Compare the mathematical meanings yourself. If aligned, output aligned with null/N/A diagnosis fields.",
            "If misaligned, choose exactly one SCI-28 category name, localize the smallest responsible Lean fragment, and provide the corrected Lean statement.",
            "Return only the required FormalRx JSON object.",
        ]
    )
    return "\n".join(lines)


def compose_evidence(
    row_mapping: Mapping[str, object],
    *,
    max_deltas: int = 8,
) -> EvidenceBundle:
    row = FormalRxRow.from_mapping(row_mapping)
    evidence = build_evidence(row_mapping, max_deltas=max_deltas)
    taxonomy_focus = score_taxonomy_candidates(evidence)
    evidence = {**evidence, "taxonomy_focus": taxonomy_focus}
    system_prompt_block = render_system_prompt_block(evidence)
    return EvidenceBundle(
        idx=row.idx,
        evidence=evidence,
        system_prompt_block=system_prompt_block,
    )
