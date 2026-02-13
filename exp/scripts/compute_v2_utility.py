# Compute combined v2 utility from v1 outputs + v2 delta outputs.
# For schemas NOT modified by v1: use v1 output (identical to v2).
# For schemas modified by BOTH v1 and v2: use v1 output (same modification).
# For schemas modified by v1 ONLY: use v2 delta output (re-generated without enum replacement).

import argparse
import json
import os
import glob


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fpr-v1", required=True)
    parser.add_argument("--fpr-v2", required=True)
    parser.add_argument("--v1-output-dir", required=True)
    parser.add_argument("--v2-delta-dir", required=True)
    parser.add_argument("--nodef-output-dir", required=True)
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--subsets", nargs="*", default=["Glaiveai2K", "Github_easy"])
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
    v1_only = v1_modified - v2_modified

    all_results = {}
    grand_total = 0
    grand_valid = 0
    grand_compliant = 0
    grand_errors = 0
    grand_modified = 0

    for subset in args.subsets:
        v1_sub = os.path.join(args.v1_output_dir, subset)
        delta_sub = os.path.join(args.v2_delta_dir, subset)
        nodef_sub = os.path.join(args.nodef_output_dir, subset)

        files = sorted(glob.glob(os.path.join(v1_sub, "*.json")))
        total = len(files)
        valid = 0
        compliant = 0
        errors = 0
        modified = 0
        delta_used = 0

        for fpath in files:
            fname = os.path.basename(fpath)
            key = (subset, fname)

            if key in v1_only:
                delta_path = os.path.join(delta_sub, fname)
                if os.path.exists(delta_path):
                    with open(delta_path) as f:
                        data = json.load(f)
                    delta_used += 1
                else:
                    with open(fpath) as f:
                        data = json.load(f)
            else:
                with open(fpath) as f:
                    data = json.load(f)

            if data.get("error_type"):
                errors += 1
                continue

            if data.get("json_valid"):
                valid += 1
            if data.get("schema_compliant"):
                compliant += 1
            if data.get("schema_modified"):
                modified += 1

        non_error = total - errors
        all_results[subset] = {
            "total": total,
            "errors": errors,
            "non_error_count": non_error,
            "json_valid_count": valid,
            "json_validity_rate": valid / non_error if non_error else 0,
            "schema_compliant_count": compliant,
            "schema_compliance_rate": compliant / non_error if non_error else 0,
            "modified_count": modified,
            "modification_rate": modified / non_error if non_error else 0,
            "delta_outputs_used": delta_used,
        }

        grand_total += non_error
        grand_valid += valid
        grand_compliant += compliant
        grand_errors += errors
        grand_modified += modified

        print(f"{subset}: {non_error} schemas, validity={valid/non_error*100:.2f}%, "
              f"compliance={compliant/non_error*100:.2f}%, modified={modified}, delta_used={delta_used}")

    # Also compute paired comparison with no-defense
    paired_results = {}
    for subset in args.subsets:
        v1_sub = os.path.join(args.v1_output_dir, subset)
        delta_sub = os.path.join(args.v2_delta_dir, subset)
        nodef_sub = os.path.join(args.nodef_output_dir, subset)

        paired = 0
        dv = dc = nv = nc = 0

        for fpath in sorted(glob.glob(os.path.join(v1_sub, "*.json"))):
            fname = os.path.basename(fpath)
            key = (subset, fname)

            if key in v1_only:
                delta_path = os.path.join(delta_sub, fname)
                if os.path.exists(delta_path):
                    with open(delta_path) as f:
                        d_data = json.load(f)
                else:
                    with open(fpath) as f:
                        d_data = json.load(f)
            else:
                with open(fpath) as f:
                    d_data = json.load(f)

            nodef_path = os.path.join(nodef_sub, fname)
            if not os.path.exists(nodef_path):
                continue
            with open(nodef_path) as f:
                n_data = json.load(f)

            if d_data.get("error_type") or n_data.get("error_type"):
                continue

            paired += 1
            if d_data.get("json_valid"): dv += 1
            if d_data.get("schema_compliant"): dc += 1
            if n_data.get("json_valid"): nv += 1
            if n_data.get("schema_compliant"): nc += 1

        paired_results[subset] = {
            "paired_schemas": paired,
            "delex_validity": dv / paired * 100 if paired else 0,
            "nodef_validity": nv / paired * 100 if paired else 0,
            "validity_delta_pp": (dv - nv) / paired * 100 if paired else 0,
            "delex_compliance": dc / paired * 100 if paired else 0,
            "nodef_compliance": nc / paired * 100 if paired else 0,
            "compliance_delta_pp": (dc - nc) / paired * 100 if paired else 0,
        }

    overall = {
        "total_schemas": grand_total,
        "total_errors": grand_errors,
        "overall_json_validity_rate": grand_valid / grand_total if grand_total else 0,
        "overall_schema_compliance_rate": grand_compliant / grand_total if grand_total else 0,
        "total_modified": grand_modified,
        "overall_modification_rate": grand_modified / grand_total if grand_total else 0,
        "per_subset": all_results,
        "paired_comparison": paired_results,
    }

    print(f"\nOverall: {grand_total} schemas, validity={grand_valid/grand_total*100:.2f}%, "
          f"compliance={grand_compliant/grand_total*100:.2f}%")

    for subset, pr in paired_results.items():
        print(f"\n{subset} paired ({pr['paired_schemas']} schemas):")
        print(f"  Validity: DeLex={pr['delex_validity']:.2f}% NoDef={pr['nodef_validity']:.2f}% delta={pr['validity_delta_pp']:+.2f}pp")
        print(f"  Compliance: DeLex={pr['delex_compliance']:.2f}% NoDef={pr['nodef_compliance']:.2f}% delta={pr['compliance_delta_pp']:+.2f}pp")

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(overall, f, indent=2)
    print(f"\nResults saved to {args.result_output}")


if __name__ == "__main__":
    main()
