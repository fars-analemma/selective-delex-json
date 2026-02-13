# Field extractor: identifies forced (enum/const) vs free-text fields in a JSON
# model output given its schema, and returns only the free-text content for
# downstream safety evaluation.

import json
from typing import Optional


def _is_forced_field(prop_schema: dict) -> bool:
    if "const" in prop_schema:
        return True
    if "enum" in prop_schema and len(prop_schema["enum"]) == 1:
        return True
    return False


def extract_free_text(json_str: str, schema: dict) -> str:
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
    except (json.JSONDecodeError, TypeError):
        return json_str if isinstance(json_str, str) else ""

    properties = schema.get("properties", {})
    if not properties:
        inner = schema.get("json_schema", {}).get("schema", {})
        properties = inner.get("properties", {})

    free_parts = []
    for field_name, field_val in data.items():
        prop_def = properties.get(field_name, {})
        if not _is_forced_field(prop_def):
            if isinstance(field_val, str):
                free_parts.append(field_val)
            else:
                free_parts.append(json.dumps(field_val))

    return "\n".join(free_parts)


def extract_free_text_from_output(
    output_file: str, schema: Optional[dict] = None
) -> str:
    with open(output_file) as f:
        record = json.load(f)

    json_str = record.get("response", record.get("output", ""))
    if schema is None:
        schema = record.get("schema", record.get("response_format", {}))
        rf = schema.get("json_schema", {}).get("schema", schema)
    else:
        rf = schema

    return extract_free_text(json_str, rf)
