# IFEval JSON subset evaluation for DeLex-JSON defense.
# Filters IFEval for instances with detectable_format:json_format constraint,
# generates with and without DeLex-JSON using a permissive JSON schema,
# measures JSON validity and instruction-following accuracy.

import argparse
import json
import os
import sys
import time

from datasets import load_from_disk
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.delex import delexicalize_schema

IFEVAL_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "ifeval",
)

PERMISSIVE_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "json_output",
        "strict": False,
        "schema": {
            "type": "object",
        },
    },
}


def is_json_valid(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def generate_with_schema(client, model, prompt, response_format, temperature, max_tokens):
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--data-dir", default=IFEVAL_DATA)
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    ds = load_from_disk(args.data_dir)

    json_instances = []
    for idx, ex in enumerate(ds):
        for inst_id in ex.get("instruction_id_list", []):
            if "json_format" in inst_id:
                json_instances.append({"idx": idx, **ex})
                break

    print(f"Found {len(json_instances)} IFEval instances with json_format constraint")

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key)

    results = []
    for i, inst in enumerate(json_instances):
        prompt = inst["prompt"]
        idx = inst["idx"]

        no_defense_output = generate_with_schema(
            client, args.model, prompt, PERMISSIVE_JSON_SCHEMA,
            args.temperature, args.max_tokens,
        )

        delex_format, mapping, report = delexicalize_schema(PERMISSIVE_JSON_SCHEMA)
        delex_output = generate_with_schema(
            client, args.model, prompt, delex_format,
            args.temperature, args.max_tokens,
        )

        nd_valid = is_json_valid(no_defense_output) if no_defense_output else False
        dx_valid = is_json_valid(delex_output) if delex_output else False

        record = {
            "ifeval_idx": idx,
            "prompt": prompt[:200],
            "instruction_ids": inst.get("instruction_id_list", []),
            "no_defense_output": no_defense_output,
            "no_defense_json_valid": nd_valid,
            "delex_output": delex_output,
            "delex_json_valid": dx_valid,
            "delex_schema_modified": len(mapping) > 0,
            "delex_mapping": mapping,
        }
        results.append(record)

        print(f"  [{i+1}/{len(json_instances)}] idx={idx} nd_valid={nd_valid} dx_valid={dx_valid} modified={len(mapping) > 0}")

    nd_valid_count = sum(1 for r in results if r["no_defense_json_valid"])
    dx_valid_count = sum(1 for r in results if r["delex_json_valid"])
    modified_count = sum(1 for r in results if r["delex_schema_modified"])
    total = len(results)

    summary = {
        "total_instances": total,
        "no_defense_json_valid": nd_valid_count,
        "no_defense_json_valid_rate": nd_valid_count / total if total else 0,
        "delex_json_valid": dx_valid_count,
        "delex_json_valid_rate": dx_valid_count / total if total else 0,
        "delex_schema_modified_count": modified_count,
        "delex_schema_modified_rate": modified_count / total if total else 0,
        "json_valid_delta": (dx_valid_count - nd_valid_count) / total if total else 0,
        "per_instance": results,
    }

    print(f"\n=== IFEval JSON Subset Results ===")
    print(f"Total: {total}")
    print(f"No-defense JSON valid: {nd_valid_count}/{total} ({nd_valid_count/total*100:.1f}%)")
    print(f"DeLex JSON valid: {dx_valid_count}/{total} ({dx_valid_count/total*100:.1f}%)")
    print(f"Schema modified: {modified_count}/{total}")
    print(f"Delta: {(dx_valid_count - nd_valid_count) / total * 100:.1f}pp")

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.result_output}")


if __name__ == "__main__":
    main()
