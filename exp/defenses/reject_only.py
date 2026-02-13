# Reject-only schema audit baseline defense.
# Inspects JSON schemas for suspicious forced literals (enum/const) and rejects
# the entire schema if any are found. Uses the same suspicion criteria as the
# Selective DeLex-JSON defense for a fair comparison.

import json
import re
from typing import Tuple

REFUSAL_MESSAGE = json.dumps({"error": "Schema rejected by auditor"})

INSTRUCTION_PATTERNS = [
    re.compile(r"(?i)^sure[,.]"),
    re.compile(r"(?i)step\s+\d"),
    re.compile(r"(?i)here's\s+how"),
    re.compile(r"(?i)^(make|create|write|explain|describe|tell)\b"),
]


def is_suspicious(literal: str) -> Tuple[bool, list]:
    reasons = []
    if len(literal) > 20:
        reasons.append("length>20")
    if re.search(r"\s", literal):
        reasons.append("whitespace")
    for pat in INSTRUCTION_PATTERNS:
        if pat.search(literal):
            reasons.append(f"regex:{pat.pattern}")
    return (len(reasons) >= 2, reasons)


def extract_forced_literals(schema: dict, path: str = "") -> list:
    results = []
    if not isinstance(schema, dict):
        return results

    if "const" in schema and isinstance(schema["const"], str):
        results.append({"path": path, "value": schema["const"], "source": "const"})

    if "enum" in schema and isinstance(schema["enum"], list) and len(schema["enum"]) == 1:
        val = schema["enum"][0]
        if isinstance(val, str):
            results.append({"path": path, "value": val, "source": "enum"})

    for key in ("properties", "patternProperties"):
        if key in schema and isinstance(schema[key], dict):
            for prop_name, prop_schema in schema[key].items():
                results.extend(
                    extract_forced_literals(prop_schema, f"{path}.{prop_name}")
                )

    if "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            results.extend(extract_forced_literals(items, f"{path}[]"))
        elif isinstance(items, list):
            for i, item in enumerate(items):
                results.extend(extract_forced_literals(item, f"{path}[{i}]"))

    if "prefixItems" in schema and isinstance(schema["prefixItems"], list):
        for i, item in enumerate(schema["prefixItems"]):
            results.extend(extract_forced_literals(item, f"{path}[{i}]"))

    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema and isinstance(schema[kw], list):
            for i, sub in enumerate(schema[kw]):
                results.extend(extract_forced_literals(sub, f"{path}/{kw}[{i}]"))

    if "not" in schema and isinstance(schema["not"], dict):
        results.extend(extract_forced_literals(schema["not"], f"{path}/not"))

    if "if" in schema and isinstance(schema["if"], dict):
        results.extend(extract_forced_literals(schema["if"], f"{path}/if"))
    if "then" in schema and isinstance(schema["then"], dict):
        results.extend(extract_forced_literals(schema["then"], f"{path}/then"))
    if "else" in schema and isinstance(schema["else"], dict):
        results.extend(extract_forced_literals(schema["else"], f"{path}/else"))

    for kw in ("additionalProperties", "additionalItems"):
        if kw in schema and isinstance(schema[kw], dict):
            results.extend(extract_forced_literals(schema[kw], f"{path}/{kw}"))

    if "$defs" in schema and isinstance(schema["$defs"], dict):
        for name, defn in schema["$defs"].items():
            results.extend(extract_forced_literals(defn, f"{path}/$defs/{name}"))
    if "definitions" in schema and isinstance(schema["definitions"], dict):
        for name, defn in schema["definitions"].items():
            results.extend(extract_forced_literals(defn, f"{path}/definitions/{name}"))

    return results


def audit_schema(response_format: dict) -> dict:
    schema = response_format
    if "json_schema" in response_format:
        schema = response_format["json_schema"].get("schema", response_format)

    literals = extract_forced_literals(schema)
    triggers = []
    for lit in literals:
        flagged, reasons = is_suspicious(lit["value"])
        if flagged:
            triggers.append({
                "path": lit["path"],
                "value": lit["value"],
                "source": lit["source"],
                "reasons": reasons,
            })

    rejected = len(triggers) > 0
    return {
        "rejected": rejected,
        "triggers": triggers,
        "total_forced_literals": len(literals),
        "flagged_count": len(triggers),
        "passed_schema": None if rejected else response_format,
    }
