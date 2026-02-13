# Selective DeLex-JSON schema transformer.
# Delexicalizes suspicious enum/const values in JSON schemas to neutralize
# control-plane payloads while preserving schema structure for constrained decoding.
# Unlike reject_only.py which rejects entire schemas, this replaces suspicious
# literals with opaque placeholders (E0, E1, ...) and strips non-semantic free-text
# fields (description, title, examples, default).

import copy
import json
import re
from typing import Tuple

INSTRUCTION_PATTERNS = [
    re.compile(r"(?i)^sure[,.]"),
    re.compile(r"(?i)step\s+\d"),
    re.compile(r"(?i)here's\s+how"),
    re.compile(r"(?i)^(make|create|write|explain|describe|tell)\b"),
    re.compile(r"(?i)^(yes|ok|absolutely|certainly)[,!.]"),
]

FREE_TEXT_FIELDS = {"description", "title", "examples", "default"}


def is_suspicious(literal: str) -> Tuple[bool, list]:
    reasons = []
    if len(literal) > 20:
        reasons.append("length>20")
    if re.search(r"\s", literal):
        reasons.append("whitespace")
    for pat in INSTRUCTION_PATTERNS:
        if pat.search(literal):
            reasons.append(f"regex:{pat.pattern}")
    return (len(reasons) > 0, reasons)


def _strip_free_text(schema: dict) -> int:
    if not isinstance(schema, dict):
        return 0
    stripped = 0
    for field in list(schema.keys()):
        if field in FREE_TEXT_FIELDS:
            del schema[field]
            stripped += 1

    for key in ("properties", "patternProperties"):
        if key in schema and isinstance(schema[key], dict):
            for prop_schema in schema[key].values():
                stripped += _strip_free_text(prop_schema)

    if "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            stripped += _strip_free_text(items)
        elif isinstance(items, list):
            for item in items:
                stripped += _strip_free_text(item)

    if "prefixItems" in schema and isinstance(schema["prefixItems"], list):
        for item in schema["prefixItems"]:
            stripped += _strip_free_text(item)

    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema and isinstance(schema[kw], list):
            for sub in schema[kw]:
                stripped += _strip_free_text(sub)

    if "not" in schema and isinstance(schema["not"], dict):
        stripped += _strip_free_text(schema["not"])

    for kw in ("if", "then", "else"):
        if kw in schema and isinstance(schema[kw], dict):
            stripped += _strip_free_text(schema[kw])

    for kw in ("additionalProperties", "additionalItems"):
        if kw in schema and isinstance(schema[kw], dict):
            stripped += _strip_free_text(schema[kw])

    if "$defs" in schema and isinstance(schema["$defs"], dict):
        for defn in schema["$defs"].values():
            stripped += _strip_free_text(defn)
    if "definitions" in schema and isinstance(schema["definitions"], dict):
        for defn in schema["definitions"].values():
            stripped += _strip_free_text(defn)

    return stripped


def _delexicalize_literals(schema: dict, counter: list, mapping: dict,
                           report: list, path: str = "") -> int:
    if not isinstance(schema, dict):
        return 0
    replaced = 0

    if "const" in schema and isinstance(schema["const"], str):
        flagged, reasons = is_suspicious(schema["const"])
        if flagged:
            placeholder = f"E{counter[0]}"
            mapping[placeholder] = schema["const"]
            report.append({
                "path": path,
                "source": "const",
                "original": schema["const"],
                "replacement": placeholder,
                "reasons": reasons,
            })
            schema["const"] = placeholder
            counter[0] += 1
            replaced += 1

    if "enum" in schema and isinstance(schema["enum"], list):
        for i, val in enumerate(schema["enum"]):
            if not isinstance(val, str):
                continue
            flagged, reasons = is_suspicious(val)
            if flagged:
                placeholder = f"E{counter[0]}"
                mapping[placeholder] = val
                report.append({
                    "path": f"{path}[enum:{i}]",
                    "source": "enum",
                    "original": val,
                    "replacement": placeholder,
                    "reasons": reasons,
                })
                schema["enum"][i] = placeholder
                counter[0] += 1
                replaced += 1

    for key in ("properties", "patternProperties"):
        if key in schema and isinstance(schema[key], dict):
            for prop_name, prop_schema in schema[key].items():
                replaced += _delexicalize_literals(
                    prop_schema, counter, mapping, report, f"{path}.{prop_name}"
                )

    if "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            replaced += _delexicalize_literals(items, counter, mapping, report, f"{path}[]")
        elif isinstance(items, list):
            for i, item in enumerate(items):
                replaced += _delexicalize_literals(item, counter, mapping, report, f"{path}[{i}]")

    if "prefixItems" in schema and isinstance(schema["prefixItems"], list):
        for i, item in enumerate(schema["prefixItems"]):
            replaced += _delexicalize_literals(item, counter, mapping, report, f"{path}[{i}]")

    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema and isinstance(schema[kw], list):
            for i, sub in enumerate(schema[kw]):
                replaced += _delexicalize_literals(sub, counter, mapping, report, f"{path}/{kw}[{i}]")

    if "not" in schema and isinstance(schema["not"], dict):
        replaced += _delexicalize_literals(schema["not"], counter, mapping, report, f"{path}/not")

    for kw in ("if", "then", "else"):
        if kw in schema and isinstance(schema[kw], dict):
            replaced += _delexicalize_literals(schema[kw], counter, mapping, report, f"{path}/{kw}")

    for kw in ("additionalProperties", "additionalItems"):
        if kw in schema and isinstance(schema[kw], dict):
            replaced += _delexicalize_literals(schema[kw], counter, mapping, report, f"{path}/{kw}")

    if "$defs" in schema and isinstance(schema["$defs"], dict):
        for name, defn in schema["$defs"].items():
            replaced += _delexicalize_literals(defn, counter, mapping, report, f"{path}/$defs/{name}")
    if "definitions" in schema and isinstance(schema["definitions"], dict):
        for name, defn in schema["definitions"].items():
            replaced += _delexicalize_literals(defn, counter, mapping, report, f"{path}/definitions/{name}")

    return replaced


def delexicalize_schema(response_format: dict) -> Tuple[dict, dict, list]:
    sanitized = copy.deepcopy(response_format)

    if "json_schema" in sanitized:
        schema = sanitized["json_schema"].get("schema", sanitized)
    else:
        schema = sanitized

    stripped_count = _strip_free_text(schema)
    mapping = {}
    report = []
    counter = [0]
    replaced_count = _delexicalize_literals(schema, counter, mapping, report, "")

    if stripped_count > 0:
        report.insert(0, {
            "action": "strip_free_text",
            "fields_stripped": stripped_count,
        })

    return sanitized, mapping, report


def restore_placeholders(json_str: str, mapping: dict) -> str:
    if not mapping:
        return json_str
    result = json_str
    for placeholder, original in mapping.items():
        escaped = json.dumps(original)[1:-1]
        result = result.replace(json.dumps(placeholder)[1:-1], escaped)
    return result
