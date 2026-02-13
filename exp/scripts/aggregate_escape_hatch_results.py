# Aggregate all escape-hatch defense results into a single JSON file.

import json
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(PROJ, "results", "escape_hatch_llama31_harmbench_asr.json")) as f:
    hb_data = json.load(f)

with open(os.path.join(PROJ, "results", "escape_hatch_llama31_strongreject.json")) as f:
    sr_data = json.load(f)

with open(os.path.join(PROJ, "results", "escape_hatch_llama31_utility.json")) as f:
    util_data = json.load(f)

hb = hb_data["harmbench"]
sr_cls = hb_data["strongreject_harmbench_cls"]

hb_summary = {
    "asr": hb["asr"],
    "total": hb["total"],
    "unsafe_count": hb["unsafe_count"],
    "model_refused_count": hb["model_refused_count"],
    "model_refusal_rate": hb["model_refusal_rate"],
    "per_category": {k: {kk: vv for kk, vv in v.items() if kk != "per_sample"} for k, v in hb["per_category"].items()},
}

sr_cls_summary = {
    "asr": sr_cls["asr"],
    "total": sr_cls["total"],
    "unsafe_count": sr_cls["unsafe_count"],
    "model_refused_count": sr_cls["model_refused_count"],
    "model_refusal_rate": sr_cls["model_refusal_rate"],
    "per_category": {k: {kk: vv for kk, vv in v.items() if kk != "per_sample"} for k, v in sr_cls["per_category"].items()},
}

sr_rubric_summary = {
    "mean_score": sr_data["strongreject_score_mean"],
    "asr": sr_data["strongreject_asr"],
    "total_scored": sr_data["total_scored"],
    "model_refused_count": sr_data["model_refused_count"],
    "model_refusal_rate": sr_data["model_refusal_rate"],
    "per_category": sr_data["per_category"],
}

util_summary = {
    "total_schemas": util_data["total_schemas"],
    "total_errors": util_data["total_errors"],
    "total_refusals": util_data["total_refusals"],
    "overall_refusal_rate": util_data["overall_refusal_rate"],
    "total_non_refusal": util_data["total_non_refusal"],
    "total_json_valid": util_data["total_json_valid"],
    "overall_json_validity_rate": util_data["overall_json_validity_rate"],
    "total_schema_compliant": util_data["total_schema_compliant"],
    "overall_schema_compliance_rate": util_data["overall_schema_compliance_rate"],
    "per_subset": util_data["per_subset"],
}

combined = {
    "experiment": "Escape-Hatch Defense against EnumAttack on Llama-3.1-8B-Instruct",
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "attack": "EnumAttack",
    "defense": "escape_hatch",
    "defense_description": "Wraps JSON schema with oneOf adding a refusal alternative, allowing model to generate {\"refusal\": \"...\"} instead of the attack schema.",
    "harmbench": hb_summary,
    "strongreject_harmbench_cls": sr_cls_summary,
    "strongreject_rubric": sr_rubric_summary,
    "benign_utility": util_summary,
}

out_path = os.path.join(PROJ, "results", "escape_hatch_llama31.json")
with open(out_path, "w") as f:
    json.dump(combined, f, indent=2)
print(f"Results saved to {out_path}")

print("\n=== Summary ===")
print(f"HarmBench ASR: {hb_summary['asr']*100:.1f}% ({hb_summary['unsafe_count']}/{hb_summary['total']})")
print(f"HarmBench Refusal Rate: {hb_summary['model_refusal_rate']*100:.1f}%")
print(f"StrongREJECT ASR (cls): {sr_cls_summary['asr']*100:.1f}% ({sr_cls_summary['unsafe_count']}/{sr_cls_summary['total']})")
print(f"StrongREJECT Score: {sr_rubric_summary['mean_score']:.3f}")
print(f"StrongREJECT Refusal Rate: {sr_rubric_summary['model_refusal_rate']*100:.1f}%")
print(f"Benign Refusal Rate: {util_summary['overall_refusal_rate']*100:.1f}%")
print(f"JSON Validity: {util_summary['overall_json_validity_rate']*100:.1f}%")
print(f"Schema Compliance: {util_summary['overall_schema_compliance_rate']*100:.1f}%")
