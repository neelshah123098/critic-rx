#!/usr/bin/env python3
"""Download the FormalRx test JSONL from Hugging Face."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default="LARK-Lab/FormalRx-Test")
    parser.add_argument("--repo-type", default="dataset")
    parser.add_argument("--filename", default="FormalRx_Test.jsonl")
    parser.add_argument("--output", type=Path, default=Path("data/FormalRx_Test.jsonl"))
    parser.add_argument("--cache-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError as exc:
        raise SystemExit("Install dependencies first: python -m pip install -r requirements.txt") from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)

    candidates = [
        args.filename,
        "FormalRx_Test.jsonl",
        "formalrx_test.jsonl",
        "test.jsonl",
    ]
    last_error: Exception | None = None
    for filename in dict.fromkeys(candidates):
        try:
            downloaded = hf_hub_download(
                repo_id=args.repo_id,
                repo_type=args.repo_type,
                filename=filename,
                cache_dir=str(args.cache_dir) if args.cache_dir else None,
            )
            shutil.copyfile(downloaded, args.output)
            print(f"downloaded {args.repo_id}/{filename} -> {args.output}")
            return 0
        except Exception as exc:  # noqa: BLE001 - try common names before snapshot.
            last_error = exc

    snapshot = Path(
        snapshot_download(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            cache_dir=str(args.cache_dir) if args.cache_dir else None,
        )
    )
    jsonl_files = sorted(snapshot.rglob("*.jsonl"))
    if not jsonl_files:
        raise SystemExit(f"no JSONL files found in snapshot; last error was {last_error}")
    chosen = jsonl_files[0]
    shutil.copyfile(chosen, args.output)
    print(f"downloaded {args.repo_id}/{chosen.name} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

