"""Output parsing and Codabench schema validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .taxonomy import CATEGORY_ALIASES, SCI_28_SET

REQUIRED_FIELDS = (
    "idx",
    "verdict",
    "error_category",
    "error_segment",
    "corrected_statement",
)


@dataclass(frozen=True)
class NormalizedPrediction:
    row: dict[str, Any]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def is_nullish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "n/a", "na", "null", "none"}:
        return True
    return False


def nullable_string(value: Any) -> str | None:
    if is_nullish(value):
        return None
    return str(value)


def parse_prediction_content(content: str, *, allow_loose_json: bool = False) -> dict[str, Any]:
    text = content.strip()
    if not text:
        raise ValueError("empty endpoint content")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if not allow_loose_json:
            raise
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("endpoint content is not a JSON object")
    return parsed


def normalize_prediction(idx: str, raw: Mapping[str, Any]) -> NormalizedPrediction:
    errors: list[str] = []
    verdict_raw = str(raw.get("verdict", "")).strip().lower()

    if verdict_raw not in {"aligned", "misaligned"}:
        errors.append(f"invalid verdict: {raw.get('verdict')!r}")
        verdict = "aligned"
    else:
        verdict = verdict_raw

    error_category = nullable_string(raw.get("error_category"))
    error_segment = nullable_string(raw.get("error_segment"))
    corrected_statement = nullable_string(raw.get("corrected_statement"))

    if verdict == "aligned":
        # The challenge treats the diagnosis fields as irrelevant/null when the
        # verdict is aligned. The submitted JSONL must still write real nulls.
        error_category = None
        error_segment = None
        corrected_statement = None
    else:
        if error_category is None:
            errors.append("misaligned prediction is missing error_category")
        else:
            error_category = CATEGORY_ALIASES.get(error_category, error_category)
        if error_category is not None and error_category not in SCI_28_SET:
            errors.append(f"unknown SCI category: {error_category!r}")
        if error_segment is None:
            errors.append("misaligned prediction is missing error_segment")
        if corrected_statement is None:
            errors.append("misaligned prediction is missing corrected_statement")

    row = {
        "idx": idx,
        "verdict": verdict,
        "error_category": error_category,
        "error_segment": error_segment,
        "corrected_statement": corrected_statement,
    }
    return NormalizedPrediction(row=row, errors=tuple(errors))


def fallback_prediction(idx: str) -> dict[str, Any]:
    return {
        "idx": idx,
        "verdict": "aligned",
        "error_category": None,
        "error_segment": None,
        "corrected_statement": None,
    }


def validate_prediction_row(row: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    keys = set(row.keys())
    missing = [key for key in REQUIRED_FIELDS if key not in row]
    extra = sorted(keys - set(REQUIRED_FIELDS))
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"extra fields: {', '.join(extra)}")
    if missing:
        return errors
    normalized = normalize_prediction(str(row["idx"]), row)
    errors.extend(normalized.errors)
    if normalized.row != dict(row):
        errors.append("row is not normalized")
    return errors


def dump_jsonl_rows(rows: list[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
