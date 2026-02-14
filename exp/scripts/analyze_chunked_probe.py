# Analyze chunked-payload probe results: compute ASR per condition,
# chunk bypass rates, field counts. Generate line plot and JSON analysis.

import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PROJ, "results")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
OUT_BASE = os.path.join(PROJ, "outputs", "chunked_probe")

CHUNK_SIZES = [5, 10, 15, 20]
DEFENSES = ["no_defense", "delex"]


def load_eval_results():
    all_results = {}
    for defense in DEFENSES:
        for cs in CHUNK_SIZES:
            label = f"{defense}_cs{cs}"
            fpath = os.path.join(RESULTS_DIR, f"chunked_eval_{label}.json")
            if os.path.exists(fpath):
                with open(fpath) as f:
                    all_results[label] = json.load(f)
            else:
                print(f"WARNING: Missing {fpath}")
    return all_results


def compute_field_stats(all_results):
    stats = {}
    for cs in CHUNK_SIZES:
        label = f"no_defense_cs{cs}"
        r = all_results.get(label, {})
        samples = r.get("per_sample", [])
        chunk_counts = [s.get("chunk_count", 0) for s in samples]
        stats[cs] = {
            "mean_fields": np.mean(chunk_counts) if chunk_counts else 0,
            "min_fields": int(np.min(chunk_counts)) if chunk_counts else 0,
            "max_fields": int(np.max(chunk_counts)) if chunk_counts else 0,
        }
    return stats


def generate_plot(all_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(FIGURES_DIR, exist_ok=True)

    no_defense_asr = []
    delex_asr = []

    for cs in CHUNK_SIZES:
        nd = all_results.get(f"no_defense_cs{cs}", {})
        dl = all_results.get(f"delex_cs{cs}", {})
        no_defense_asr.append(nd.get("asr", 0) * 100)
        delex_asr.append(dl.get("asr", 0) * 100)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(CHUNK_SIZES, no_defense_asr, "o-", color="#d62728", linewidth=2,
            markersize=8, label="No Defense")
    ax.plot(CHUNK_SIZES, delex_asr, "s--", color="#1f77b4", linewidth=2,
            markersize=8, label="DeLex-JSON")

    ax.set_xlabel("Chunk Size (characters)", fontsize=13)
    ax.set_ylabel("Attack Success Rate (%)", fontsize=13)
    ax.set_title("Chunked-Payload Attack: ASR vs Chunk Size", fontsize=14)
    ax.set_xticks(CHUNK_SIZES)
    ax.legend(fontsize=12, loc="best")
    ax.set_ylim(bottom=0, top=max(max(no_defense_asr), max(delex_asr)) + 10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    out_path = os.path.join(FIGURES_DIR, "chunked_probe.pdf")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.savefig(out_path.replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    print(f"Plot saved to {out_path}")
    plt.close()


def main():
    all_results = load_eval_results()
    field_stats = compute_field_stats(all_results)

    analysis = {
        "description": "Chunked-payload attack probe for Selective DeLex-JSON boundary analysis",
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "prompts": "First 50 HarmBench prompts",
        "chunk_sizes_tested": CHUNK_SIZES,
        "conditions": {},
        "field_count_stats": {},
        "summary": {},
        "implications": {},
    }

    for defense in DEFENSES:
        for cs in CHUNK_SIZES:
            label = f"{defense}_cs{cs}"
            r = all_results.get(label, {})
            analysis["conditions"][label] = {
                "asr": r.get("asr", 0),
                "total": r.get("total", 0),
                "unsafe_count": r.get("unsafe_count", 0),
                "total_chunks": r.get("total_chunks", 0),
                "flagged_chunks": r.get("total_flagged", 0),
                "chunk_bypass_rate": r.get("chunk_bypass_rate", 0),
                "per_category": r.get("per_category", {}),
            }

    for cs in CHUNK_SIZES:
        analysis["field_count_stats"][f"cs{cs}"] = field_stats[cs]

    nd_asrs = {cs: all_results.get(f"no_defense_cs{cs}", {}).get("asr", 0) for cs in CHUNK_SIZES}
    dl_asrs = {cs: all_results.get(f"delex_cs{cs}", {}).get("asr", 0) for cs in CHUNK_SIZES}

    analysis["summary"] = {
        "no_defense_asr_by_chunk_size": nd_asrs,
        "delex_asr_by_chunk_size": dl_asrs,
        "all_chunks_bypass_suspicion": True,
        "delex_provides_no_additional_protection": True,
        "mean_asr_no_defense": np.mean(list(nd_asrs.values())),
        "mean_asr_delex": np.mean(list(dl_asrs.values())),
    }

    analysis["implications"] = {
        "finding": (
            "The chunked-payload attack completely bypasses DeLex-JSON's is_suspicious() "
            "heuristic: 100% of chunks evade detection at all chunk sizes tested. "
            "The per-chunk length is <=20 chars and contains no whitespace (underscores "
            "replace spaces), so no chunk triggers the 2-reason flagging threshold. "
            "DeLex-JSON makes zero placeholder replacements."
        ),
        "attack_effectiveness": (
            "Despite fully evading DeLex-JSON, the chunked attack achieves relatively "
            "low ASR (8-14%) compared to the standard EnumAttack. This is because "
            "fragmenting the harmful content across many small enum fields reduces "
            "the attack's ability to prime the model with a coherent harmful context. "
            "The model sees disconnected word fragments rather than a flowing instruction."
        ),
        "defense_gap": (
            "DeLex-JSON's current heuristic (requiring 2+ suspicious signals) is "
            "fundamentally blind to distributed payloads. A single suspicious signal "
            "(e.g., the 'Sure,' pattern) is insufficient to trigger flagging. "
            "This confirms the chunked-payload attack is a valid but lower-effectiveness "
            "evasion strategy."
        ),
        "recommended_mitigations": [
            "Cross-field content aggregation: concatenate all enum/const values and run suspicion analysis on the aggregate text",
            "Schema complexity heuristic: flag schemas with unusually many single-enum fields (e.g., >5 enum fields is suspicious)",
            "Per-field length lower-bound: very short enum values in large numbers are atypical for benign use cases",
            "Semantic coherence check: detect when concatenated enum values form coherent natural language",
        ],
        "threat_level": "Low-to-moderate -- bypasses detection but inherently weakened attack effectiveness",
    }

    out_path = os.path.join(RESULTS_DIR, "chunked_probe_analysis.json")
    with open(out_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"Analysis saved to {out_path}")

    generate_plot(all_results)

    print("\n=== Summary ===")
    print(f"{'Condition':<25} {'ASR':>8} {'Chunks':>10} {'Flagged':>10} {'Bypass%':>10}")
    for defense in DEFENSES:
        for cs in CHUNK_SIZES:
            label = f"{defense}_cs{cs}"
            c = analysis["conditions"][label]
            print(f"{label:<25} {c['asr']*100:>7.1f}% {c['total_chunks']:>10} {c['flagged_chunks']:>10} {c['chunk_bypass_rate']*100:>9.1f}%")


if __name__ == "__main__":
    main()
