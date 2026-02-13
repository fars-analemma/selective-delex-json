# Measure false positive (benign rejection) rate of reject-only schema auditor
# on JSONSchemaBench. Runs on ALL schemas in each specified subset (no GPU needed).
# Reports per-subset and per-trigger-reason rejection rates.

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.reject_only import audit_schema, extract_forced_literals, is_suspicious

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
    all_rejections = []
    grand_total = 0
    grand_rejected = 0
    reason_counts = {}

    for subset, schemas in all_schemas.items():
        total = len(schemas)
        rejected = 0
        subset_reasons = {}
        subset_rejections = []

        for s in schemas:
            if s.get("schema") is None:
                continue

            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "benign", "strict": True, "schema": s["schema"]},
            }
            audit = audit_schema(response_format)

            if audit["rejected"]:
                rejected += 1
                for trigger in audit["triggers"]:
                    for r in trigger["reasons"]:
                        subset_reasons[r] = subset_reasons.get(r, 0) + 1
                        reason_counts[r] = reason_counts.get(r, 0) + 1
                subset_rejections.append({
                    "file": s["file"],
                    "triggers": audit["triggers"],
                })

        fpr = rejected / total if total > 0 else 0.0
        per_subset[subset] = {
            "total": total,
            "rejected": rejected,
            "fpr": fpr,
            "reason_counts": subset_reasons,
        }
        all_rejections.extend([{**r, "subset": subset} for r in subset_rejections])
        grand_total += total
        grand_rejected += rejected

        print(f"  {subset}: {rejected}/{total} rejected ({fpr*100:.1f}%)")
        if subset_reasons:
            for r, c in sorted(subset_reasons.items()):
                print(f"    {r}: {c}")

    overall_fpr = grand_rejected / grand_total if grand_total > 0 else 0.0
    print(f"\n=== Overall ===")
    print(f"Total schemas: {grand_total}")
    print(f"Rejected: {grand_rejected} ({overall_fpr*100:.1f}%)")
    for r, c in sorted(reason_counts.items()):
        print(f"  {r}: {c}")

    output_data = {
        "overall_fpr": overall_fpr,
        "total_schemas": grand_total,
        "total_rejected": grand_rejected,
        "overall_reason_counts": reason_counts,
        "per_subset": per_subset,
        "rejected_details": all_rejections,
    }

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
