# Aggregate all DeLex-JSON results into a summary JSON file.
# Compiles safety, utility, and overhead metrics, and compares vs all baselines.

import json
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(PROJ, "results")


def load_json(path):
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found")
        return None
    with open(path) as f:
        return json.load(f)


def main():
    harmbench_asr = load_json(os.path.join(RESULTS, "delex_llama31_harmbench_asr.json"))
    strongreject = load_json(os.path.join(RESULTS, "delex_llama31_strongreject.json"))
    utility = load_json(os.path.join(RESULTS, "delex_llama31_utility.json"))
    no_defense_utility = load_json(os.path.join(RESULTS, "no_defense_llama31_utility.json"))
    fpr = load_json(os.path.join(RESULTS, "delex_llama31_fpr.json"))
    ifeval = load_json(os.path.join(RESULTS, "delex_ifeval_llama31.json"))

    no_defense = load_json(os.path.join(RESULTS, "no_defense_llama31.json"))
    input_guard = load_json(os.path.join(RESULTS, "input_guard_llama31.json"))
    reject_only = load_json(os.path.join(RESULTS, "reject_only_llama31.json"))
    escape_hatch = load_json(os.path.join(RESULTS, "escape_hatch_llama31.json"))

    summary = {
        "experiment": "Selective DeLex-JSON Defense on Llama-3.1-8B-Instruct",
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "attack": "EnumAttack",
        "defense": "delex_json",
    }

    if harmbench_asr:
        hb = harmbench_asr.get("harmbench", {})
        sr_cls = harmbench_asr.get("strongreject_harmbench_cls", {})
        summary["safety"] = {
            "harmbench_asr": hb.get("asr"),
            "harmbench_total": hb.get("total"),
            "harmbench_unsafe": hb.get("unsafe_count"),
            "harmbench_schema_modification_rate": hb.get("schema_modification_rate"),
            "strongreject_cls_asr": sr_cls.get("asr"),
            "strongreject_cls_total": sr_cls.get("total"),
            "strongreject_cls_unsafe": sr_cls.get("unsafe_count"),
        }

    if strongreject:
        summary["strongreject"] = {
            "score_mean": strongreject.get("strongreject_score_mean"),
            "asr": strongreject.get("strongreject_asr"),
            "total_scored": strongreject.get("total_scored"),
        }

    if utility:
        summary["utility_delex"] = {
            "json_validity_rate": utility.get("overall_json_validity_rate"),
            "schema_compliance_rate": utility.get("overall_schema_compliance_rate"),
            "modification_rate": utility.get("overall_modification_rate"),
            "total_schemas": utility.get("total_schemas"),
            "per_subset": utility.get("per_subset"),
        }

    if no_defense_utility:
        summary["utility_no_defense"] = {
            "json_validity_rate": no_defense_utility.get("overall_json_validity_rate"),
            "schema_compliance_rate": no_defense_utility.get("overall_schema_compliance_rate"),
            "total_schemas": no_defense_utility.get("total_schemas"),
            "per_subset": no_defense_utility.get("per_subset"),
        }

    if utility and no_defense_utility:
        summary["utility_delta"] = {
            "json_validity_delta": (
                utility.get("overall_json_validity_rate", 0) -
                no_defense_utility.get("overall_json_validity_rate", 0)
            ),
            "schema_compliance_delta": (
                utility.get("overall_schema_compliance_rate", 0) -
                no_defense_utility.get("overall_schema_compliance_rate", 0)
            ),
        }

    if fpr:
        summary["benign_modification"] = {
            "overall_rate": fpr.get("overall_modification_rate"),
            "total_schemas": fpr.get("total_schemas"),
            "total_modified": fpr.get("total_modified"),
            "total_suspicious_literals": fpr.get("total_suspicious_literals"),
            "per_subset": {
                k: {"modification_rate": v.get("modification_rate"), "total": v.get("total")}
                for k, v in (fpr.get("per_subset", {})).items()
            },
        }

    if ifeval:
        summary["ifeval"] = {
            "total_instances": ifeval.get("total_instances"),
            "no_defense_json_valid_rate": ifeval.get("no_defense_json_valid_rate"),
            "delex_json_valid_rate": ifeval.get("delex_json_valid_rate"),
            "json_valid_delta": ifeval.get("json_valid_delta"),
            "delex_schema_modified_rate": ifeval.get("delex_schema_modified_rate"),
        }

    def extract_baseline(data, name):
        if not data:
            return {"name": name, "available": False}
        result = {"name": name, "available": True}
        if "harmbench" in data:
            result["harmbench_asr"] = data["harmbench"].get("asr")
        if "strongreject" in data:
            result["strongreject_score_mean"] = data["strongreject"].get("strongreject_score_mean")
            result["strongreject_asr"] = data["strongreject"].get("strongreject_asr")
        elif "strongreject_score_mean" in data:
            result["strongreject_score_mean"] = data.get("strongreject_score_mean")
            result["strongreject_asr"] = data.get("strongreject_asr")
        return result

    summary["baselines"] = {
        "no_defense": extract_baseline(no_defense, "No Defense"),
        "input_guard": extract_baseline(input_guard, "Input Guard (Llama Guard)"),
        "reject_only": extract_baseline(reject_only, "Reject-Only Schema Audit"),
        "escape_hatch": extract_baseline(escape_hatch, "Escape-Hatch Wrapper"),
    }

    output_path = os.path.join(RESULTS, "delex_llama31_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("=== DeLex-JSON Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
