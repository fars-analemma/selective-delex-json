# Re-generate utility outputs for schemas where v1 modified but v2 doesn't.
# These are the only schemas whose DeLex output differs between v1 and v2.
# For all other schemas, the v2 output is identical to v1 (same defense behavior).
# After running, the combined utility is computed from v1 results + these v2 delta results.

import argparse
import json
import os
import sys
import glob
import urllib.request
import jsonschema
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.delex import delexicalize_schema, restore_placeholders

JSONSCHEMABENCH_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "external", "jsonschemabench", "data",
)

USER_PROMPT = "Generate a JSON object that conforms to the given schema."


def server_alive(endpoint):
    health_url = endpoint.replace("/v1", "/health")
    try:
        urllib.request.urlopen(health_url, timeout=5)
        return True
    except Exception:
        return False


def validate_schema_compliance(json_str, schema):
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {"json_valid": False, "schema_compliant": False, "error": "invalid_json"}
    try:
        jsonschema.validate(data, schema)
        return {"json_valid": True, "schema_compliant": True, "error": None}
    except jsonschema.ValidationError as e:
        return {"json_valid": True, "schema_compliant": False, "error": str(e)[:200]}
    except jsonschema.SchemaError as e:
        return {"json_valid": True, "schema_compliant": False, "error": f"schema_error:{str(e)[:200]}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--fpr-v1", required=True, help="V1 FPR results file")
    parser.add_argument("--fpr-v2", required=True, help="V2 FPR results file")
    parser.add_argument("--v1-output-dir", required=True, help="V1 utility output dir")
    parser.add_argument("--v2-output-dir", required=True, help="V2 delta output dir")
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--data-dir", default=JSONSCHEMABENCH_DATA)
    parser.add_argument("--subsets", nargs="*", default=["Glaiveai2K", "Github_easy"])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    with open(args.fpr_v1) as f:
        fpr_v1 = json.load(f)
    with open(args.fpr_v2) as f:
        fpr_v2 = json.load(f)

    v1_modified = set()
    for d in fpr_v1.get("modified_details", []):
        v1_modified.add((d["subset"], d["file"]))
    v2_modified = set()
    for d in fpr_v2.get("modified_details", []):
        v2_modified.add((d["subset"], d["file"]))

    v1_only = {}
    for subset, fname in v1_modified - v2_modified:
        if subset in args.subsets:
            v1_only.setdefault(subset, set()).add(fname)

    total_delta = sum(len(v) for v in v1_only.values())
    print(f"Schemas to re-generate (v1-only modified): {total_delta}")
    for subset, files in sorted(v1_only.items()):
        print(f"  {subset}: {len(files)}")

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key, timeout=120)

    results = {}
    for subset in args.subsets:
        delta_files = v1_only.get(subset, set())
        if not delta_files:
            print(f"\n=== {subset}: no delta schemas, skipping ===")
            results[subset] = {"delta_count": 0, "regenerated": 0}
            continue

        subset_dir = os.path.join(args.data_dir, subset)
        v2_out_dir = os.path.join(args.v2_output_dir, subset)
        os.makedirs(v2_out_dir, exist_ok=True)

        print(f"\n=== {subset}: {len(delta_files)} delta schemas ===")
        regenerated = 0
        for fname in sorted(delta_files):
            schema_path = os.path.join(subset_dir, fname)
            out_path = os.path.join(v2_out_dir, fname)

            if os.path.exists(out_path):
                print(f"  {fname}: cached")
                regenerated += 1
                continue

            try:
                with open(schema_path) as f:
                    schema = json.load(f)
            except Exception as e:
                record = {"file": fname, "error_type": "load_error", "error": str(e)}
                with open(out_path, "w") as f:
                    json.dump(record, f, indent=2)
                continue

            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "benign_schema", "strict": True, "schema": schema},
            }

            sanitized_format, mapping, delex_report = delexicalize_schema(response_format)

            content = None
            for attempt in range(3):
                try:
                    resp = client.chat.completions.create(
                        model=args.model,
                        messages=[{"role": "user", "content": USER_PROMPT}],
                        response_format=sanitized_format,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                    )
                    content = resp.choices[0].message.content
                    break
                except Exception as e:
                    err_str = str(e)
                    if "Could not find" in err_str or "not supported" in err_str:
                        break
                    if args.endpoint and not server_alive(args.endpoint):
                        print(f"  SERVER DEAD at {fname}")
                        sys.exit(3)
                    if attempt < 2:
                        import time; time.sleep(2)

            if content is None:
                record = {"file": fname, "error_type": "generation_error", "error": "no_response"}
                with open(out_path, "w") as f:
                    json.dump(record, f, indent=2)
                continue

            restored_content = restore_placeholders(content, mapping) if mapping else content
            validation = validate_schema_compliance(restored_content, schema)
            schema_modified = len(mapping) > 0

            record = {
                "file": fname,
                "schema_modified": schema_modified,
                "placeholder_count": len(mapping),
                "response": content,
                "restored_response": restored_content if mapping else None,
                **validation,
            }
            with open(out_path, "w") as f:
                json.dump(record, f, indent=2)
            regenerated += 1
            status = "valid+compliant" if validation.get("schema_compliant") else (
                "valid" if validation.get("json_valid") else "invalid"
            )
            print(f"  {fname}: {status} (modified={schema_modified})")

        results[subset] = {"delta_count": len(delta_files), "regenerated": regenerated}

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDelta results saved to {args.result_output}")


if __name__ == "__main__":
    main()
