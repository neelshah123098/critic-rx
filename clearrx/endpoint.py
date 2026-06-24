"""OpenAI-compatible endpoint client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EndpointResult:
    content: str
    raw_response: dict[str, Any]
    usage: dict[str, Any]


def chat_completion(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> EndpointResult:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
    parsed = json.loads(body)
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError("endpoint response has no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("endpoint choice has no string message.content")
    usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {}
    return EndpointResult(content=content, raw_response=parsed, usage=usage)

