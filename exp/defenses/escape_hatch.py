# Escape-hatch defense: wraps JSON schemas with a oneOf that adds a refusal
# alternative, allowing the model to generate a refusal object instead of being
# forced to comply with potentially malicious constrained decoding schemas.

import copy
import json
from typing import Tuple


REFUSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "refusal": {"type": "string"},
    },
    "required": ["refusal"],
    "additionalProperties": False,
}


def wrap_schema_with_escape_hatch(response_format: dict) -> dict:
    rf = copy.deepcopy(response_format)
    js = rf.get("json_schema", {})
    original_schema = js.get("schema", {})

    if "oneOf" in original_schema:
        original_schema["oneOf"].append(copy.deepcopy(REFUSAL_SCHEMA))
    elif "anyOf" in original_schema:
        original_schema["anyOf"].append(copy.deepcopy(REFUSAL_SCHEMA))
    else:
        wrapped = {
            "oneOf": [
                original_schema,
                copy.deepcopy(REFUSAL_SCHEMA),
            ]
        }
        js["schema"] = wrapped

    if js.get("strict"):
        js["strict"] = False

    rf["json_schema"] = js
    return rf


def is_refusal(response_str: str) -> bool:
    try:
        data = json.loads(response_str) if isinstance(response_str, str) else response_str
    except (json.JSONDecodeError, TypeError):
        return False
    if isinstance(data, dict) and "refusal" in data:
        other_keys = set(data.keys()) - {"refusal"}
        if not other_keys:
            return True
    return False


def classify_output(response_str: str) -> Tuple[str, str]:
    if is_refusal(response_str):
        try:
            data = json.loads(response_str) if isinstance(response_str, str) else response_str
            return "model_refused", data.get("refusal", "")
        except (json.JSONDecodeError, TypeError):
            return "model_refused", ""
    return "normal", ""


REFUSAL_MESSAGE = json.dumps({"refusal": "I cannot assist with this request."})
