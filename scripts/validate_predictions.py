#!/usr/bin/env python3
"""Validate FormalRx predictions.jsonl against Codabench schema."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clearrx.schema import REQUIRED_FIELDS, validate_prediction_row  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--check-order", action="store_true", default=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: row is not a JSON object")
            rows.append(value)
    return rows


def resolve_predictions(path: Path) -> Path:
    if path.suffix != ".zip":
        return path
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if names != ["predictions.jsonl"]:
            raise ValueError("submission zip must contain exactly one predictions.jsonl file")
        target = path.with_suffix(".unzipped.predictions.jsonl")
        target.write_bytes(archive.read("predictions.jsonl"))
        return target


def main() -> int:
    args = parse_args()
    prediction_path = resolve_predictions(args.predictions)
    predictions = read_jsonl(prediction_path)

    errors: list[str] = []
    if args.expected_count is not None and len(predictions) != args.expected_count:
        errors.append(f"expected {args.expected_count} rows, found {len(predictions)}")

    for i, row in enumerate(predictions, 1):
        row_errors = validate_prediction_row(row)
        for row_error in row_errors:
            idx = row.get("idx", f"line_{i}")
            errors.append(f"{idx}: {row_error}")
        if tuple(row.keys()) != REQUIRED_FIELDS:
            idx = row.get("idx", f"line_{i}")
            errors.append(f"{idx}: field order should be {REQUIRED_FIELDS}")

    if args.dataset:
        dataset = read_jsonl(args.dataset)
        expected_ids = [str(row.get("idx")) for row in dataset[: len(predictions)]]
        observed_ids = [str(row.get("idx")) for row in predictions]
        if args.expected_count is None and len(predictions) != len(dataset):
            errors.append(f"dataset has {len(dataset)} rows, predictions has {len(predictions)}")
        if args.check_order and observed_ids != expected_ids:
            for pos, (expected, observed) in enumerate(zip(expected_ids, observed_ids), 1):
                if expected != observed:
                    errors.append(f"order mismatch at row {pos}: expected {expected}, found {observed}")
                    break

    report = {
        "predictions": str(args.predictions),
        "rows": len(predictions),
        "errors": len(errors),
        "examples": errors[:10],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

