# Measure benign schema modification rate of Selective DeLex-JSON on JSONSchemaBench.
# Reports per-schema and per-literal modification rates with trigger reason breakdown.
# CPU only, no GPU needed.

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.delex import delexicalize_schema, is_suspicious

JSONSCHEMABENCH_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "external", "jsonschemabench", "data",
)

TARGET_SUBSETS = [
    "Glaiveai2K",
    "Github_easy",
    "Github_medium",
    "Github_hard",
    "Kubernetes",
    "Snowplow",
    "JsonSchemaStore",
]


def load_all_schemas(data_dir: str, subsets: list) -> dict:
    result = {}
    for subset in subsets:
        subset_dir = os.path.join(data_dir, subset)
        files = sorted(glob.glob(os.path.join(subset_dir, "*.json")))
        schemas = []
        for fpath in files:
            try:
                with open(fpath) as f:
                    schema = json.load(f)
                schemas.append({"file": os.path.basename(fpath), "schema": schema})
            except Exception as e:
                schemas.append({"file": os.path.basename(fpath), "schema": None, "error": str(e)})
        result[subset] = schemas
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=JSONSCHEMABENCH_DATA)
    parser.add_argument("--output", required=True)
    parser.add_argument("--subsets", nargs="*", default=TARGET_SUBSETS)
    args = parser.parse_args()

    all_schemas = load_all_schemas(args.data_dir, args.subsets)

    per_subset = {}
    all_modifications = []
    grand_total = 0
    grand_modified = 0
    grand_total_literals = 0
    grand_suspicious_literals = 0
    reason_counts = {}

    for subset, schemas in all_schemas.items():
        total = len(schemas)
        modified = 0
        subset_reasons = {}
        subset_modifications = []
        subset_total_literals = 0
        subset_suspicious_literals = 0

        for s in schemas:
            if s.get("schema") is None:
                continue

            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "benign", "strict": True, "schema": s["schema"]},
            }
            sanitized, mapping, report = delexicalize_schema(response_format)

            literal_changes = [r for r in report if r.get("source") in ("enum", "const")]
            schema_was_modified = len(literal_changes) > 0

            if schema_was_modified:
                modified += 1
                for change in literal_changes:
                    subset_suspicious_literals += 1
                    for reason in change["reasons"]:
                        subset_reasons[reason] = subset_reasons.get(reason, 0) + 1
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1
                subset_modifications.append({
                    "file": s["file"],
                    "changes": literal_changes,
                })

        mod_rate = modified / total if total > 0 else 0.0
        per_subset[subset] = {
            "total": total,
            "modified": modified,
            "modification_rate": mod_rate,
            "suspicious_literals": subset_suspicious_literals,
            "reason_counts": subset_reasons,
        }
        all_modifications.extend([{**m, "subset": subset} for m in subset_modifications])
        grand_total += total
        grand_modified += modified
        grand_suspicious_literals += subset_suspicious_literals

        print(f"  {subset}: {modified}/{total} modified ({mod_rate*100:.1f}%)")
        if subset_reasons:
            for r, c in sorted(subset_reasons.items()):
                print(f"    {r}: {c}")

    overall_mod_rate = grand_modified / grand_total if grand_total > 0 else 0.0
    print(f"\n=== Overall ===")
    print(f"Total schemas: {grand_total}")
    print(f"Modified: {grand_modified} ({overall_mod_rate*100:.1f}%)")
    print(f"Total suspicious literals: {grand_suspicious_literals}")
    for r, c in sorted(reason_counts.items()):
        print(f"  {r}: {c}")

    output_data = {
        "overall_modification_rate": overall_mod_rate,
        "total_schemas": grand_total,
        "total_modified": grand_modified,
        "total_suspicious_literals": grand_suspicious_literals,
        "overall_reason_counts": reason_counts,
        "per_subset": per_subset,
        "modified_details": all_modifications,
    }

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
