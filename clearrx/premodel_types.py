"""Typed data structures for the experimental ClearRx pre-model pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceFragment:
    text: str
    start: int | None = None
    end: int | None = None
    source: str = "formal_statement"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntentSchema:
    quantifiers: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    conclusion: str = ""
    raw_statement: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeanSchema:
    declaration_kind: str = ""
    declaration_name: str = ""
    binders: list[dict[str, str]] = field(default_factory=list)
    hypotheses: list[dict[str, str]] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    target: str = ""
    fragments: dict[str, SourceFragment] = field(default_factory=dict)
    raw_statement: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fragments"] = {key: value.to_dict() for key, value in self.fragments.items()}
        return data


@dataclass
class Delta:
    kind: str
    expected: str | None
    observed: str | None
    category_hint: str
    confidence: float
    rationale: str
    span_hint: SourceFragment | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.span_hint is not None:
            data["span_hint"] = self.span_hint.to_dict()
        return data


@dataclass
class PremodelDiagnosis:
    idx: str
    intent: IntentSchema
    lean: LeanSchema
    deltas: list[Delta]
    verdict_guess: str
    error_category_guess: str | None
    error_segment_guess: str | None
    corrected_statement_guess: str | None
    confidence: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self, *, include_schemas: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "idx": self.idx,
            "verdict_guess": self.verdict_guess,
            "error_category_guess": self.error_category_guess,
            "error_segment_guess": self.error_segment_guess,
            "corrected_statement_guess": self.corrected_statement_guess,
            "confidence": round(self.confidence, 4),
            "deltas": [delta.to_dict() for delta in self.deltas],
            "notes": self.notes,
        }
        if include_schemas:
            data["intent"] = self.intent.to_dict()
            data["lean"] = self.lean.to_dict()
        return data

