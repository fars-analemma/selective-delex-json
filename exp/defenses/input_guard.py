# Input guard baseline defense.
# Uses Llama Guard 3 to classify (prompt + serialized schema) as safe/unsafe
# before allowing constrained decoding. If unsafe, request is rejected.

import json
from typing import Tuple

from openai import OpenAI


REFUSAL_MESSAGE = json.dumps({"error": "Refused by input guard"})


def build_audit_string(user_prompt: str, schema: dict) -> str:
    schema_body = schema
    if "json_schema" in schema:
        schema_body = schema["json_schema"].get("schema", schema)
    return f"User prompt: {user_prompt}\n\nJSON Schema:\n{json.dumps(schema_body, indent=2)}"


def classify_input(
    client: OpenAI,
    model: str,
    audit_string: str,
    max_retries: int = 2,
) -> Tuple[str, str]:
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": audit_string}],
                temperature=0.0,
                max_tokens=100,
            )
            text = resp.choices[0].message.content.strip()
            first_line = text.split("\n")[0].strip().lower()
            if "unsafe" in first_line:
                return "unsafe", text
            return "safe", text
        except Exception as e:
            if attempt < max_retries:
                continue
            return "error", str(e)
    return "error", "max retries exceeded"


def run_input_guard(
    guard_client: OpenAI,
    guard_model: str,
    user_prompt: str,
    response_format: dict,
) -> dict:
    audit_string = build_audit_string(user_prompt, response_format)
    decision, guard_response = classify_input(guard_client, guard_model, audit_string)

    if decision == "unsafe":
        return {
            "decision": decision,
            "guard_response": guard_response,
            "refused": True,
            "user_prompt": user_prompt,
            "response_format": response_format,
        }

    return {
        "decision": decision,
        "guard_response": guard_response,
        "refused": False,
        "user_prompt": user_prompt,
        "response_format": response_format,
    }
