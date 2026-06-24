"""Run ClearRx inference over a FormalRx JSONL file."""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .endpoint import chat_completion
from .prompting import (
    DEFAULT_ROW_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT,
    FormalRxRow,
    build_messages,
    read_text,
)
from .premodel_evidence import compose_evidence
from .schema import (
    dump_jsonl_rows,
    fallback_prediction,
    normalize_prediction,
    parse_prediction_content,
)

PREMODEL_MAX_DELTAS = 8


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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
                raise ValueError(f"{path}:{line_no}: row must be a JSON object")
            rows.append(value)
    return rows


def write_submission_zip(zip_path: Path, predictions_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(predictions_path, arcname="predictions.jsonl")


def run_one(
    raw_row: dict[str, Any],
    *,
    args: argparse.Namespace,
    system_prompt: str,
    row_template: str,
) -> dict[str, Any]:
    row = FormalRxRow.from_mapping(raw_row)
    evidence_bundle = compose_evidence(raw_row, max_deltas=PREMODEL_MAX_DELTAS)
    system_prompt_for_row = (
        system_prompt.rstrip() + "\n\n" + evidence_bundle.system_prompt_block
    )
    messages = build_messages(
        row,
        system_prompt=system_prompt_for_row,
        row_template=row_template,
    )

    started = time.time()
    attempts = 0
    last_error: str | None = None
    while attempts <= args.retries:
        attempts += 1
        try:
            result = chat_completion(
                base_url=args.base_url,
                model=args.model,
                messages=messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
            parsed = parse_prediction_content(
                result.content,
                allow_loose_json=args.allow_loose_json,
            )
            normalized = normalize_prediction(row.idx, parsed)
            return {
                "idx": row.idx,
                "prediction": normalized.row,
                "ok": normalized.ok,
                "schema_errors": list(normalized.errors),
                "parse_error": None,
                "request_error": None,
                "raw_content": result.content if args.keep_raw else None,
                "usage": result.usage,
                "premodel_context": evidence_bundle.to_dict() if evidence_bundle else None,
                "latency_sec": round(time.time() - started, 4),
                "attempts": attempts,
            }
        except Exception as exc:  # noqa: BLE001 - report must retain failure details.
            last_error = f"{type(exc).__name__}: {exc}"
            if attempts <= args.retries:
                time.sleep(args.retry_sleep)

    return {
        "idx": row.idx,
        "prediction": fallback_prediction(row.idx),
        "ok": False,
        "schema_errors": [],
        "parse_error": last_error,
        "request_error": last_error,
        "raw_content": None,
        "usage": {},
        "premodel_context": evidence_bundle.to_dict() if evidence_bundle else None,
        "latency_sec": round(time.time() - started, 4),
        "attempts": attempts,
    }


def build_report(results: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    parse_errors = [r for r in results if r["parse_error"]]
    request_errors = [r for r in results if r["request_error"]]
    schema_errors = [r for r in results if r["schema_errors"]]
    valid_responses = [
        r
        for r in results
        if not r["parse_error"] and not r["request_error"] and not r["schema_errors"]
    ]
    return {
        "dataset": str(args.dataset),
        "model": args.model,
        "base_url": args.base_url,
        "limit": args.limit,
        "offset": args.offset,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": False,
        "premodel_evidence": True,
        "premodel_max_deltas": PREMODEL_MAX_DELTAS,
        "rows_written": len(results),
        "valid_responses": len(valid_responses),
        "parse_errors": len(parse_errors),
        "request_errors": len(request_errors),
        "schema_errors": len(schema_errors),
        "examples": {
            "parse_errors": parse_errors[:3],
            "request_errors": request_errors[:3],
            "schema_errors": schema_errors[:3],
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="criticleanGPT-Qwen3-8B-RL")
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--row-template", type=Path, default=DEFAULT_ROW_TEMPLATE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--zip-output", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--allow-loose-json", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--premodel-context-output", type=Path)
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    all_rows = load_jsonl(args.dataset)
    rows = all_rows[args.offset :]
    if args.limit is not None:
        rows = rows[: args.limit]

    system_prompt = read_text(args.system_prompt)
    row_template = read_text(args.row_template)

    results: list[dict[str, Any] | None] = [None] * len(rows)
    started = time.time()

    if args.workers == 1:
        for i, row in enumerate(rows):
            result = run_one(
                row,
                args=args,
                system_prompt=system_prompt,
                row_template=row_template,
            )
            results[i] = result
            print(
                f"{i + 1}/{len(rows)} {result['idx']} ok={result['ok']} "
                f"attempts={result['attempts']} latency={result['latency_sec']}",
                file=sys.stderr,
                flush=True,
            )
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_to_index = {
                pool.submit(
                    run_one,
                    row,
                    args=args,
                    system_prompt=system_prompt,
                    row_template=row_template,
                ): i
                for i, row in enumerate(rows)
            }
            completed = 0
            for future in as_completed(future_to_index):
                i = future_to_index[future]
                result = future.result()
                results[i] = result
                completed += 1
                print(
                    f"{completed}/{len(rows)} {result['idx']} ok={result['ok']} "
                    f"attempts={result['attempts']} latency={result['latency_sec']}",
                    file=sys.stderr,
                    flush=True,
                )

    complete_results = [r for r in results if r is not None]
    predictions = [r["prediction"] for r in complete_results]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump_jsonl_rows(predictions), encoding="utf-8")

    if args.premodel_context_output:
        contexts = [
            r["premodel_context"]
            for r in complete_results
            if r.get("premodel_context") is not None
        ]
        args.premodel_context_output.parent.mkdir(parents=True, exist_ok=True)
        args.premodel_context_output.write_text(
            "".join(
                json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n"
                for context in contexts
            ),
            encoding="utf-8",
        )

    report = build_report(complete_results, args)
    report["elapsed_sec"] = round(time.time() - started, 4)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.zip_output:
        write_submission_zip(args.zip_output, args.output)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.fail_on_error and (
        report["parse_errors"] or report["request_errors"] or report["schema_errors"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
