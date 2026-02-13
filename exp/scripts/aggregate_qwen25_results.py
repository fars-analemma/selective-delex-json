# Aggregate Qwen2.5-7B results into consolidated JSON files and cross-model comparison.
import json
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(PROJ, "results")


def load(name):
    with open(os.path.join(RESULTS, name)) as f:
        return json.load(f)


def save(name, data):
    with open(os.path.join(RESULTS, name), "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {name}")


def aggregate_no_defense():
    hb = load("no_defense_qwen25_harmbench_asr.json")
    sr = load("no_defense_qwen25_strongreject.json")

    result = {
        "experiment": "EnumAttack (No Defense) on Qwen2.5-7B-Instruct",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "attack": "EnumAttack",
        "defense": "none",
        "temperature": 0.6,
        "max_model_len": 3072,
        "harmbench": {
            "asr": hb["harmbench"]["asr"],
            "total": hb["harmbench"]["total"],
            "unsafe_count": hb["harmbench"]["unsafe_count"],
            "per_category": hb["harmbench"]["per_category"],
        },
        "strongreject_harmbench_cls": {
            "asr": hb["strongreject_harmbench_cls"]["asr"],
            "total": hb["strongreject_harmbench_cls"]["total"],
            "unsafe_count": hb["strongreject_harmbench_cls"]["unsafe_count"],
            "per_category": hb["strongreject_harmbench_cls"]["per_category"],
        },
        "strongreject_rubric": {
            "score_mean": sr["strongreject_score_mean"],
            "asr": sr["strongreject_asr"],
            "total_scored": sr["total_scored"],
            "per_category": sr["per_category"],
        },
    }
    save("no_defense_qwen25.json", result)
    return result


def aggregate_delex():
    hb = load("delex_qwen25_harmbench_asr.json")
    sr = load("delex_qwen25_strongreject.json")

    result = {
        "experiment": "DeLex-JSON Defense on Qwen2.5-7B-Instruct",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "attack": "EnumAttack",
        "defense": "delex_json",
        "temperature": 0.6,
        "max_model_len": 3072,
        "harmbench": {
            "asr": hb["harmbench"]["asr"],
            "total": hb["harmbench"]["total"],
            "unsafe_count": hb["harmbench"]["unsafe_count"],
            "schema_modification_rate": hb["harmbench"]["schema_modification_rate"],
            "per_category": hb["harmbench"]["per_category"],
        },
        "strongreject_harmbench_cls": {
            "asr": hb["strongreject_harmbench_cls"]["asr"],
            "total": hb["strongreject_harmbench_cls"]["total"],
            "unsafe_count": hb["strongreject_harmbench_cls"]["unsafe_count"],
            "schema_modification_rate": hb["strongreject_harmbench_cls"]["schema_modification_rate"],
            "per_category": hb["strongreject_harmbench_cls"]["per_category"],
        },
        "strongreject_rubric": {
            "score_mean": sr["strongreject_score_mean"],
            "asr": sr["strongreject_asr"],
            "total_scored": sr["total_scored"],
            "per_category": sr["per_category"],
        },
    }
    save("delex_qwen25.json", result)
    return result


def aggregate_utility():
    nodef = load("no_defense_qwen25_utility.json")
    delex = load("delex_qwen25_utility.json")

    result = {
        "experiment": "Utility Evaluation on Qwen2.5-7B-Instruct",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "subset": "Glaiveai2K",
        "no_defense": {
            "json_validity_rate": nodef["overall_json_validity_rate"],
            "schema_compliance_rate": nodef["overall_schema_compliance_rate"],
            "total_schemas": nodef["total_schemas"],
            "total_errors": nodef["total_errors"],
        },
        "delex": {
            "json_validity_rate": delex["overall_json_validity_rate"],
            "schema_compliance_rate": delex["overall_schema_compliance_rate"],
            "total_schemas": delex["total_schemas"],
            "total_errors": delex["total_errors"],
            "modification_rate": delex.get("overall_modification_rate", 0.0),
        },
        "delta": {
            "json_validity_delta": delex["overall_json_validity_rate"] - nodef["overall_json_validity_rate"],
            "schema_compliance_delta": delex["overall_schema_compliance_rate"] - nodef["overall_schema_compliance_rate"],
        },
    }
    save("delex_utility_qwen25.json", result)
    return result


def cross_model_comparison():
    llama_nodef = load("no_defense_llama31.json")
    qwen_nodef = load("no_defense_qwen25.json")

    llama_hb_asr = load("delex_v2_llama31_harmbench_asr.json")
    llama_sr = load("delex_v2_llama31_strongreject.json") if os.path.exists(os.path.join(RESULTS, "delex_v2_llama31_strongreject.json")) else None
    qwen_delex = load("delex_qwen25.json")

    def model_entry(name, nodef, delex_hb, delex_sr_cls_asr, delex_sr_score):
        nodef_hb_asr = nodef["harmbench"]["asr"]
        nodef_sr_cls_asr = nodef["strongreject_harmbench_cls"]["asr"]
        sr_rubric = nodef["strongreject_rubric"]
        nodef_sr_score = sr_rubric.get("score_mean", sr_rubric.get("mean_score", 0.0))

        delex_hb_asr = delex_hb["harmbench"]["asr"]

        return {
            "model": name,
            "no_defense": {
                "harmbench_asr": nodef_hb_asr,
                "strongreject_cls_asr": nodef_sr_cls_asr,
                "strongreject_score": nodef_sr_score,
            },
            "delex_json": {
                "harmbench_asr": delex_hb_asr,
                "strongreject_cls_asr": delex_sr_cls_asr,
                "strongreject_score": delex_sr_score,
            },
            "reduction": {
                "harmbench_asr_abs": nodef_hb_asr - delex_hb_asr,
                "harmbench_asr_rel": (nodef_hb_asr - delex_hb_asr) / nodef_hb_asr if nodef_hb_asr > 0 else 0.0,
                "strongreject_cls_asr_abs": nodef_sr_cls_asr - delex_sr_cls_asr,
                "strongreject_cls_asr_rel": (nodef_sr_cls_asr - delex_sr_cls_asr) / nodef_sr_cls_asr if nodef_sr_cls_asr > 0 else 0.0,
                "strongreject_score_abs": nodef_sr_score - delex_sr_score,
                "strongreject_score_rel": (nodef_sr_score - delex_sr_score) / nodef_sr_score if nodef_sr_score > 0 else 0.0,
            },
        }

    llama_sr_data = load("delex_v2_llama31_strongreject.json")

    llama_entry = model_entry(
        "meta-llama/Llama-3.1-8B-Instruct",
        llama_nodef,
        llama_hb_asr,
        llama_hb_asr["strongreject_harmbench_cls"]["asr"],
        llama_sr_data["strongreject_score_mean"],
    )

    qwen_entry = model_entry(
        "Qwen/Qwen2.5-7B-Instruct",
        qwen_nodef,
        {"harmbench": qwen_delex["harmbench"]},
        qwen_delex["strongreject_harmbench_cls"]["asr"],
        qwen_delex["strongreject_rubric"]["score_mean"],
    )

    comparison = {
        "description": "Cross-model comparison of DeLex-JSON defense effectiveness",
        "models": [llama_entry, qwen_entry],
    }

    save("cross_model_comparison.json", comparison)
    return comparison


if __name__ == "__main__":
    print("=== Aggregating No-Defense Qwen2.5 ===")
    nd = aggregate_no_defense()
    print(f"  HarmBench ASR: {nd['harmbench']['asr']*100:.1f}%")
    print(f"  StrongREJECT ASR (cls): {nd['strongreject_harmbench_cls']['asr']*100:.1f}%")
    print(f"  StrongREJECT Score: {nd['strongreject_rubric']['score_mean']:.4f}")

    print("\n=== Aggregating DeLex Qwen2.5 ===")
    dx = aggregate_delex()
    print(f"  HarmBench ASR: {dx['harmbench']['asr']*100:.1f}%")
    print(f"  StrongREJECT ASR (cls): {dx['strongreject_harmbench_cls']['asr']*100:.1f}%")
    print(f"  StrongREJECT Score: {dx['strongreject_rubric']['score_mean']:.4f}")

    print("\n=== Aggregating Utility Qwen2.5 ===")
    ut = aggregate_utility()
    print(f"  No-def validity: {ut['no_defense']['json_validity_rate']*100:.1f}%")
    print(f"  DeLex validity: {ut['delex']['json_validity_rate']*100:.1f}%")
    print(f"  Delta validity: {ut['delta']['json_validity_delta']*100:.1f}%")
    print(f"  Delta compliance: {ut['delta']['schema_compliance_delta']*100:.1f}%")

    print("\n=== Cross-Model Comparison ===")
    cm = cross_model_comparison()
    for m in cm["models"]:
        print(f"\n  {m['model']}:")
        print(f"    No-def HarmBench ASR: {m['no_defense']['harmbench_asr']*100:.1f}%")
        print(f"    DeLex HarmBench ASR: {m['delex_json']['harmbench_asr']*100:.1f}%")
        print(f"    HarmBench ASR reduction: {m['reduction']['harmbench_asr_abs']*100:.1f}pp ({m['reduction']['harmbench_asr_rel']*100:.1f}%)")
        print(f"    No-def StrongREJECT Score: {m['no_defense']['strongreject_score']:.4f}")
        print(f"    DeLex StrongREJECT Score: {m['delex_json']['strongreject_score']:.4f}")
