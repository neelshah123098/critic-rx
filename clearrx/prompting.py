"""Prompt rendering for the row-local ClearRx endpoint contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
DEFAULT_SYSTEM_PROMPT = DEFAULT_PROMPT_DIR / "formalrx_system_prompt.md"
DEFAULT_ROW_TEMPLATE = DEFAULT_PROMPT_DIR / "formalrx_prompt_template.txt"


@dataclass(frozen=True)
class FormalRxRow:
    """Single FormalRx input row."""

    idx: str
    header: str
    informal_statement: str
    formal_statement: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "FormalRxRow":
        missing = [
            key
            for key in ("idx", "header", "informal_statement", "formal_statement")
            if key not in row
        ]
        if missing:
            raise ValueError(f"row is missing required fields: {', '.join(missing)}")
        return cls(
            idx=str(row["idx"]),
            header=str(row.get("header") or ""),
            informal_statement=str(row.get("informal_statement") or ""),
            formal_statement=str(row.get("formal_statement") or ""),
        )


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def render_user_prompt(row: FormalRxRow, template: str) -> str:
    """Render the exact final user message expected by the FormalRx runtime."""

    return template.format(
        header=row.header,
        informal_statement=row.informal_statement,
        formal_statement=row.formal_statement,
    ).strip()


def build_messages(
    row: FormalRxRow,
    *,
    system_prompt: str,
    row_template: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": render_user_prompt(row, row_template)})
    return messages

