"""LeanLens: lightweight reconstruction of candidate Lean statements."""

from __future__ import annotations

import re

from .premodel_common import (
    CONCEPT_PATTERNS,
    DOMAIN_PATTERNS,
    FUNCTION_PATTERNS,
    OPERATOR_PATTERNS,
    constants,
    find_patterns,
    lean_type_to_domain,
    normalize_space,
    relation_constraint_label,
    unique,
)
from .premodel_types import LeanSchema, SourceFragment


DECL_RE = re.compile(r"\b(theorem|lemma|example|def)\s+([A-Za-z_][A-Za-z0-9_'.]*)?")


def strip_comments(text: str) -> str:
    text = re.sub(r"/-.*?-/", " ", text or "", flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in text.splitlines())


def split_before_proof(text: str) -> str:
    depth = 0
    i = 0
    while i < len(text) - 1:
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == ":" and text[i + 1] == "=" and depth == 0:
            return text[:i].strip()
        i += 1
    return text.strip()


def balanced_groups(text: str) -> list[tuple[str, str, int, int]]:
    groups: list[tuple[str, str, int, int]] = []
    pairs = {"(": ")", "{": "}", "[": "]"}
    i = 0
    while i < len(text):
        if text[i] not in pairs:
            i += 1
            continue
        opener = text[i]
        closer = pairs[opener]
        depth = 1
        j = i + 1
        while j < len(text) and depth:
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
            j += 1
        if depth == 0:
            groups.append((opener + closer, text[i + 1 : j - 1].strip(), i, j))
            i = j
        else:
            i += 1
    return groups


def find_target_colon(head: str, search_from: int) -> int | None:
    depth = 0
    for i in range(search_from, len(head)):
        ch = head[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == ":" and depth == 0:
            return i
    return None


def parse_binder(group_text: str, delimiter: str) -> dict[str, str]:
    if ":" not in group_text:
        return {"names": normalize_space(group_text), "type": "", "kind": "implicit" if delimiter == "{}" else "binder"}
    names, type_text = group_text.split(":", 1)
    names = normalize_space(names)
    type_text = normalize_space(type_text)
    label = relation_constraint_label(type_text)
    kind = "hypothesis" if label or names.startswith("h") else "variable"
    return {"names": names, "type": type_text, "kind": kind}


def parse_header_variables(header: str) -> list[dict[str, str]]:
    binders: list[dict[str, str]] = []
    for line in (header or "").splitlines():
        if not re.search(r"\bvariables?\b", line):
            continue
        for delimiter, text, _, _ in balanced_groups(line):
            binders.append(parse_binder(text, delimiter))
    return binders


def first_fragment(formal_statement: str, token: str) -> SourceFragment | None:
    if not token:
        return None
    pos = formal_statement.find(token)
    if pos >= 0:
        return SourceFragment(text=token, start=pos, end=pos + len(token))
    return None


def analyze_lean(header: str, formal_statement: str) -> LeanSchema:
    raw = formal_statement or ""
    clean = strip_comments(raw)
    head = split_before_proof(clean)
    match = DECL_RE.search(head)
    declaration_kind = match.group(1) if match else ""
    declaration_name = match.group(2) if match and match.group(2) else ""
    after_name = head[match.end() :] if match else head
    offset = match.end() if match else 0

    groups = balanced_groups(after_name)
    last_group_end = max((end for _, _, _, end in groups), default=0)
    target_colon = find_target_colon(after_name, last_group_end)
    target = normalize_space(after_name[target_colon + 1 :]) if target_colon is not None else normalize_space(after_name)

    binders = parse_header_variables(header)
    for delimiter, text, _, _ in groups:
        binders.append(parse_binder(text, delimiter))

    hypotheses = [binder for binder in binders if binder.get("kind") == "hypothesis"]
    variables = []
    domains = []
    constraints = []
    for binder in binders:
        names = binder.get("names", "")
        type_text = binder.get("type", "")
        if binder.get("kind") == "variable":
            variables.extend(re.findall(r"[A-Za-z_][A-Za-z0-9_']*", names))
            domain = lean_type_to_domain(type_text)
            if domain:
                domains.append(domain)
        label = relation_constraint_label(type_text)
        if label:
            constraints.append(label)

    text_for_features = f"{header or ''}\n{head}"
    operators = find_patterns(text_for_features, OPERATOR_PATTERNS, flags=0)
    functions = find_patterns(text_for_features, FUNCTION_PATTERNS, flags=0)
    concepts = find_patterns(text_for_features, CONCEPT_PATTERNS, flags=re.I)

    fragments: dict[str, SourceFragment] = {}
    for token in unique(operators + functions + concepts + constants(head)):
        fragment = first_fragment(raw, token)
        if fragment:
            fragments[token] = fragment

    # Add source fragments for hypotheses and target chunks.
    for hyp in hypotheses:
        fragment = first_fragment(raw, hyp.get("type", ""))
        if fragment:
            fragments[f"hypothesis:{hyp.get('names')}"] = fragment
    if target:
        fragment = first_fragment(raw, target)
        if fragment:
            fragments["target"] = fragment

    return LeanSchema(
        declaration_kind=declaration_kind,
        declaration_name=declaration_name,
        binders=binders,
        hypotheses=hypotheses,
        variables=unique(variables),
        domains=unique(domains + find_patterns(text_for_features, DOMAIN_PATTERNS, flags=0)),
        constraints=unique(constraints),
        functions=functions,
        operators=operators,
        constants=constants(head),
        concepts=concepts,
        target=target,
        fragments=fragments,
        raw_statement=raw,
    )

