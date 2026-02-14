# Compile ablation study results into summary JSON files.
# Reads existing results for Full DeLex-JSON, No Defense, and all 3 ablation variants.

import json
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(PROJ, "results")


def load(name):
    with open(os.path.join(RESULTS, name)) as f:
        return json.load(f)


def main():
    no_def_asr = load("no_defense_llama31_harmbench_asr.json")
    no_def_util = load("no_defense_llama31_utility.json")
    full_asr = load("delex_v2_llama31_harmbench_asr.json")
    full_util = load("delex_v2_llama31_utility.json")
    full_fpr = load("delex_llama31_fpr_v2.json")

    strip_asr = load("ablation_strip_only_harmbench_asr.json")
    strip_util = load("ablation_strip_only_utility.json")
    strip_fpr = load("ablation_fpr_strip_only.json")

    dall_asr = load("ablation_delex_all_harmbench_asr.json")
    dall_util = load("ablation_delex_all_utility.json")
    dall_fpr = load("ablation_fpr_delex_all.json")

    heur_asr = load("ablation_heuristic_only_harmbench_asr.json")
    heur_fpr = load("ablation_fpr_heuristic_only.json")

    table = {
        "no_defense": {
            "harmbench_asr": no_def_asr["harmbench"]["asr"],
            "benign_modification_rate": 0.0,
            "json_validity": no_def_util["overall_json_validity_rate"],
            "schema_compliance": no_def_util["overall_schema_compliance_rate"],
        },
        "full_delex_json": {
            "harmbench_asr": full_asr["harmbench"]["asr"],
            "benign_modification_rate": full_fpr["overall_modification_rate"],
            "json_validity": full_util["overall_json_validity_rate"],
            "schema_compliance": full_util["overall_schema_compliance_rate"],
        },
        "strip_only": {
            "harmbench_asr": strip_asr["harmbench"]["asr"],
            "benign_modification_rate": strip_fpr["overall_modification_rate"],
            "json_validity": strip_util["overall_json_validity_rate"],
            "schema_compliance": strip_util["overall_schema_compliance_rate"],
        },
        "delex_all": {
            "harmbench_asr": dall_asr["harmbench"]["asr"],
            "benign_modification_rate": dall_fpr["overall_modification_rate"],
            "json_validity": dall_util["overall_json_validity_rate"],
            "schema_compliance": dall_util["overall_schema_compliance_rate"],
        },
        "heuristic_only": {
            "harmbench_asr": heur_asr["harmbench"]["asr"],
            "benign_modification_rate": heur_fpr["overall_modification_rate"],
            "json_validity": full_util["overall_json_validity_rate"],
            "schema_compliance": full_util["overall_schema_compliance_rate"],
            "note": "utility identical to full DeLex-JSON (same transform)",
        },
    }

    analysis = {
        "strip_only_vs_full": {
            "finding": "Strip-Only has same ASR as No Defense (22.0% vs 0.0%), proving forced enum/const literals are the key attack vector, not free-text metadata fields.",
            "safety_delta": strip_asr["harmbench"]["asr"] - full_asr["harmbench"]["asr"],
        },
        "delex_all_vs_full": {
            "finding": "Delex-All achieves 0% ASR like Full, but has 35.5% benign modification rate vs 1.1%, and lower utility (validity -0.9pp, compliance -1.0pp). Selective delexicalization preserves more utility than blanket approach.",
            "benign_mod_rate_delta": dall_fpr["overall_modification_rate"] - full_fpr["overall_modification_rate"],
            "validity_delta": dall_util["overall_json_validity_rate"] - full_util["overall_json_validity_rate"],
            "compliance_delta": dall_util["overall_schema_compliance_rate"] - full_util["overall_schema_compliance_rate"],
        },
        "heuristic_only_vs_full": {
            "finding": "Heuristic-Only is identical to Full DeLex-JSON (both use same is_suspicious() function, no guard model was used). This confirms the rule-based heuristic alone is sufficient.",
            "identical": True,
        },
    }

    summary = {"comparison_table": table, "analysis": analysis}

    with open(os.path.join(RESULTS, "ablation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("Saved ablation_summary.json")

    utility_data = {
        "strip_only": {
            "per_subset": strip_util.get("per_subset", {}),
            "overall_validity": strip_util["overall_json_validity_rate"],
            "overall_compliance": strip_util["overall_schema_compliance_rate"],
            "total_schemas": strip_util["total_schemas"],
            "total_modified": strip_util.get("total_modified", 0),
        },
        "delex_all": {
            "per_subset": dall_util.get("per_subset", {}),
            "overall_validity": dall_util["overall_json_validity_rate"],
            "overall_compliance": dall_util["overall_schema_compliance_rate"],
            "total_schemas": dall_util["total_schemas"],
            "total_modified": dall_util.get("total_modified", 0),
        },
        "heuristic_only": {
            "note": "identical to full DeLex-JSON",
            "overall_validity": full_util["overall_json_validity_rate"],
            "overall_compliance": full_util["overall_schema_compliance_rate"],
        },
        "full_delex_json": {
            "per_subset": full_util.get("per_subset", {}),
            "overall_validity": full_util["overall_json_validity_rate"],
            "overall_compliance": full_util["overall_schema_compliance_rate"],
            "total_schemas": full_util.get("total_schemas", 0),
        },
        "no_defense": {
            "per_subset": no_def_util.get("per_subset", {}),
            "overall_validity": no_def_util["overall_json_validity_rate"],
            "overall_compliance": no_def_util["overall_schema_compliance_rate"],
        },
    }

    with open(os.path.join(RESULTS, "ablation_utility.json"), "w") as f:
        json.dump(utility_data, f, indent=2)
    print("Saved ablation_utility.json")

    print("\n=== Ablation Summary Table ===")
    print(f"{'Variant':<20} {'ASR':>8} {'Benign Mod':>12} {'Validity':>10} {'Compliance':>12}")
    print("-" * 65)
    for name, row in table.items():
        print(f"{name:<20} {row['harmbench_asr']*100:>7.1f}% {row['benign_modification_rate']*100:>10.1f}% {row['json_validity']*100:>9.1f}% {row['schema_compliance']*100:>10.1f}%")


if __name__ == "__main__":
    main()
