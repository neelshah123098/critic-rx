#!/usr/bin/env python3
"""Check that the OpenAI-compatible endpoint is reachable."""

from __future__ import annotations

import argparse
import json
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def get_json(url: str, timeout: float) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_args()
    root = args.base_url.rstrip("/")
    health_url = root.rsplit("/v1", 1)[0] + "/health"
    results = {}
    for name, url in {
        "health": health_url,
        "models": root + "/models",
    }.items():
        try:
            results[name] = get_json(url, args.timeout)
        except Exception as exc:  # noqa: BLE001 - command-line health report.
            results[name] = {"error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if "error" not in results.get("models", {}) else 1


if __name__ == "__main__":
    raise SystemExit(main())

