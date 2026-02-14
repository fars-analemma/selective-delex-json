# Utility evaluation of ablation DeLex-JSON variants on JSONSchemaBench.
# Supports --delex-mode: strip_only, delex_all, heuristic_only.
# Same pipeline as run_delex_utility.py but uses delexicalize_schema_ablation().
# Validates against ORIGINAL schema (not sanitized) for compliance.

import argparse
import glob
import json
import os
import sys
import time
import urllib.request

import jsonschema
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.delex import delexicalize_schema_ablation, restore_placeholders

JSONSCHEMABENCH_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "external", "jsonschemabench", "data",
)

TARGET_SUBSETS = ["Glaiveai2K", "Github_easy"]
USER_PROMPT = "Generate a JSON object that conforms to the given schema."


def server_alive(endpoint):
    health_url = endpoint.replace("/v1", "/health")
    try:
        urllib.request.urlopen(health_url, timeout=5)
        return True
    except Exception:
        return False


def validate_schema_compliance(json_str: str, schema: dict) -> dict:
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


def run_utility_eval(
    client: OpenAI, model: str, data_dir: str, subsets: list,
    output_dir: str, delex_mode: str,
    temperature: float = 0.6, max_tokens: int = 1024,
    batch_limit: int = 0, endpoint: str = "",
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    all_results = {}
    grand_total = 0
    grand_json_valid = 0
    grand_schema_compliant = 0
    grand_errors = 0
    grand_modified = 0
    new_processed = 0
    hit_batch_limit = False

    for subset in subsets:
        subset_dir = os.path.join(data_dir, subset)
        files = sorted(glob.glob(os.path.join(subset_dir, "*.json")))
        subset_out_dir = os.path.join(output_dir, subset)
        os.makedirs(subset_out_dir, exist_ok=True)

        total = len(files)
        json_valid_count = 0
        schema_compliant_count = 0
        error_count = 0
        modified_count = 0

        print(f"\n=== {subset}: {total} schemas (mode={delex_mode}) ===")

        for idx, fpath in enumerate(files):
            fname = os.path.basename(fpath)
            out_path = os.path.join(subset_out_dir, fname)

            if os.path.exists(out_path):
                try:
                    with open(out_path) as f:
                        cached = json.load(f)
                except (json.JSONDecodeError, Exception):
                    os.remove(out_path)
                else:
                    if cached.get("error_type"):
                        error_count += 1
                    else:
                        if cached.get("json_valid"):
                            json_valid_count += 1
                        if cached.get("schema_compliant"):
                            schema_compliant_count += 1
                        if cached.get("schema_modified"):
                            modified_count += 1
                    continue

            if batch_limit > 0 and new_processed >= batch_limit:
                hit_batch_limit = True
                break

            try:
                with open(fpath) as f:
                    schema = json.load(f)
            except Exception as e:
                error_count += 1
                record = {"file": fname, "error_type": "load_error", "error": str(e)}
                with open(out_path, "w") as f:
                    json.dump(record, f, indent=2)
                continue

            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "benign_schema", "strict": True, "schema": schema},
            }

            try:
                sanitized_format, mapping, delex_report = delexicalize_schema_ablation(
                    response_format, delex_mode=delex_mode
                )
            except Exception as e:
                error_count += 1
                record = {"file": fname, "error_type": "delex_error", "error": str(e)}
                with open(out_path, "w") as f:
                    json.dump(record, f, indent=2)
                continue

            schema_modified = len(mapping) > 0
            if schema_modified:
                modified_count += 1

            content = None
            server_dead = False
            for attempt in range(3):
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": USER_PROMPT}],
                        response_format=sanitized_format,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    content = resp.choices[0].message.content
                    break
                except Exception as e:
                    err_str = str(e)
                    if "Could not find" in err_str or "not supported" in err_str:
                        break
                    if endpoint and not server_alive(endpoint):
                        print(f"  SERVER DEAD at schema {idx+1}, exiting", flush=True)
                        server_dead = True
                        break
                    if attempt < 2:
                        time.sleep(2)

            if server_dead:
                sys.exit(3)

            if content is None:
                error_count += 1
                record = {"file": fname, "error_type": "generation_error", "error": "all_attempts_failed"}
                with open(out_path, "w") as f:
                    json.dump(record, f, indent=2)
                continue

            if mapping:
                restored_content = restore_placeholders(content, mapping)
            else:
                restored_content = content

            validation = validate_schema_compliance(restored_content, schema)
            if validation["json_valid"]:
                json_valid_count += 1
            if validation["schema_compliant"]:
                schema_compliant_count += 1

            record = {
                "file": fname,
                "delex_mode": delex_mode,
                "schema_modified": schema_modified,
                "placeholder_count": len(mapping),
                "response": content,
                "restored_response": restored_content if mapping else None,
                **validation,
            }
            with open(out_path, "w") as f:
                json.dump(record, f, indent=2)

            new_processed += 1
            if (idx + 1) % 100 == 0 or new_processed % 50 == 0:
                print(f"  [{idx+1}/{total}] valid={json_valid_count}, compliant={schema_compliant_count}, modified={modified_count}, new={new_processed}")

        non_error = total - error_count
        validity_rate = json_valid_count / non_error if non_error else 0
        compliance_rate = schema_compliant_count / non_error if non_error else 0
        mod_rate = modified_count / non_error if non_error else 0

        all_results[subset] = {
            "total": total, "errors": error_count, "non_error_count": non_error,
            "json_valid_count": json_valid_count, "json_validity_rate": validity_rate,
            "schema_compliant_count": schema_compliant_count, "schema_compliance_rate": compliance_rate,
            "modified_count": modified_count, "modification_rate": mod_rate,
        }

        print(f"  {subset}: {non_error} evaluated, validity={validity_rate*100:.1f}%, compliance={compliance_rate*100:.1f}%, modified={modified_count}")
        grand_total += non_error
        grand_json_valid += json_valid_count
        grand_schema_compliant += schema_compliant_count
        grand_errors += error_count
        grand_modified += modified_count

        if hit_batch_limit:
            break

    overall = {
        "delex_mode": delex_mode,
        "total_schemas": grand_total, "total_errors": grand_errors,
        "overall_json_validity_rate": grand_json_valid / grand_total if grand_total else 0,
        "overall_schema_compliance_rate": grand_schema_compliant / grand_total if grand_total else 0,
        "total_modified": grand_modified,
        "overall_modification_rate": grand_modified / grand_total if grand_total else 0,
        "per_subset": all_results, "hit_batch_limit": hit_batch_limit,
    }

    print(f"\n=== Overall ({delex_mode}) ===")
    if grand_total:
        print(f"JSON valid: {grand_json_valid}/{grand_total} ({grand_json_valid/grand_total*100:.1f}%)")
        print(f"Schema compliant: {grand_schema_compliant}/{grand_total} ({grand_schema_compliant/grand_total*100:.1f}%)")
        print(f"Modified: {grand_modified}/{grand_total} ({grand_modified/grand_total*100:.1f}%)")
    print(f"New processed this batch: {new_processed}")
    return overall


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--data-dir", default=JSONSCHEMABENCH_DATA)
    parser.add_argument("--subsets", nargs="*", default=TARGET_SUBSETS)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--delex-mode", required=True, choices=["strip_only", "delex_all", "heuristic_only"])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    parser.add_argument("--batch-limit", type=int, default=0)
    args = parser.parse_args()

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key, timeout=120)
    results = run_utility_eval(
        client, args.model, args.data_dir, args.subsets,
        args.output_dir, args.delex_mode,
        args.temperature, args.max_tokens,
        batch_limit=args.batch_limit, endpoint=args.endpoint,
    )

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.result_output}")

    if results.get("hit_batch_limit"):
        sys.exit(2)


if __name__ == "__main__":
    main()
