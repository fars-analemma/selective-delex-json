# Measure benign schema modification rate of ablation DeLex-JSON variants on JSONSchemaBench.
# Supports --delex-mode: strip_only, delex_all, heuristic_only.
# CPU only, no GPU needed. Reports per-subset modification rates.

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from defenses.delex import delexicalize_schema_ablation

JSONSCHEMABENCH_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "external", "jsonschemabench", "data",
)

TARGET_SUBSETS = [
    "Glaiveai2K", "Github_easy", "Github_medium", "Github_hard",
    "Kubernetes", "Snowplow", "JsonSchemaStore",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=JSONSCHEMABENCH_DATA)
    parser.add_argument("--output", required=True)
    parser.add_argument("--delex-mode", required=True, choices=["strip_only", "delex_all", "heuristic_only"])
    parser.add_argument("--subsets", nargs="*", default=TARGET_SUBSETS)
    args = parser.parse_args()

    per_subset = {}
    all_modifications = []
    grand_total = 0
    grand_modified = 0
    grand_total_literals = 0
    reason_counts = {}

    for subset in args.subsets:
        subset_dir = os.path.join(args.data_dir, subset)
        files = sorted(glob.glob(os.path.join(subset_dir, "*.json")))
        total = len(files)
        modified = 0
        subset_reasons = {}
        subset_modifications = []
        subset_suspicious = 0

        for fpath in files:
            try:
                with open(fpath) as f:
                    schema = json.load(f)
            except Exception:
                continue

            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "benign", "strict": True, "schema": schema},
            }
            _, mapping, report = delexicalize_schema_ablation(response_format, delex_mode=args.delex_mode)
            literal_changes = [r for r in report if r.get("source") in ("enum", "const")]
            schema_was_modified = len(literal_changes) > 0

            if schema_was_modified:
                modified += 1
                for change in literal_changes:
                    subset_suspicious += 1
                    for reason in change["reasons"]:
                        subset_reasons[reason] = subset_reasons.get(reason, 0) + 1
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1
                subset_modifications.append({"file": os.path.basename(fpath), "changes": literal_changes})

        mod_rate = modified / total if total > 0 else 0.0
        per_subset[subset] = {
            "total": total,
            "modified": modified,
            "modification_rate": mod_rate,
            "suspicious_literals": subset_suspicious,
            "reason_counts": subset_reasons,
        }
        all_modifications.extend([{**m, "subset": subset} for m in subset_modifications])
        grand_total += total
        grand_modified += modified
        grand_total_literals += subset_suspicious

        print(f"  {subset}: {modified}/{total} modified ({mod_rate*100:.1f}%)")

    overall_rate = grand_modified / grand_total if grand_total > 0 else 0.0
    print(f"\n=== Overall ({args.delex_mode}) ===")
    print(f"Total schemas: {grand_total}")
    print(f"Modified: {grand_modified} ({overall_rate*100:.1f}%)")
    print(f"Total replaced literals: {grand_total_literals}")

    output_data = {
        "delex_mode": args.delex_mode,
        "overall_modification_rate": overall_rate,
        "total_schemas": grand_total,
        "total_modified": grand_modified,
        "total_replaced_literals": grand_total_literals,
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
