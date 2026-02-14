# Analyze correlation between forced literal properties and attack success.
# Operates on two separate sample sets: HarmBench (159) and StrongREJECT (313).
# Produces correlation JSON and scatter plot PDF.

import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import pearsonr, pointbiserialr, spearmanr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTRUCTION_PATTERNS = [
    re.compile(r"(?i)^sure[,.]"),
    re.compile(r"(?i)step\s+\d"),
    re.compile(r"(?i)here's\s+how"),
    re.compile(r"(?i)^(make|create|write|explain|describe|tell)\b"),
    re.compile(r"(?i)^(yes|ok|absolutely|certainly)[,!.]"),
]

PREFIX = "Sure, here is a detailed guide on how to"
PREFIX_LEN = len(PREFIX)


def compute_properties(behavior: str) -> dict:
    qlen = len(behavior)
    ws = sum(1 for c in behavior if c.isspace())
    pat_matches = sum(1 for p in INSTRUCTION_PATTERNS if p.search(behavior))
    return {
        "question_length": qlen,
        "prefix_length": PREFIX_LEN,
        "total_literal_length": qlen + PREFIX_LEN,
        "whitespace_count": ws,
        "instruction_pattern_matches": pat_matches,
    }


def safe_corr(func, x, y):
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return {"r": 0.0, "p": 1.0, "note": "zero variance"}
    r, p = func(x_arr, y_arr)
    return {"r": float(r), "p": float(p)}


def main():
    with open(os.path.join(BASE, "data", "harmbench_prompts.json")) as f:
        hb_prompts = {p["id"]: p["behavior"] for p in json.load(f)}

    with open(os.path.join(BASE, "data", "strongreject_prompts.json")) as f:
        sr_prompts = {p["id"]: p["behavior"] for p in json.load(f)}

    with open(os.path.join(BASE, "results", "no_defense_llama31_harmbench_asr.json")) as f:
        hb_asr = json.load(f)

    with open(os.path.join(BASE, "results", "no_defense_llama31_strongreject.json")) as f:
        sr_scores = json.load(f)

    hb_labels = {s["id"]: s["unsafe"] for s in hb_asr["harmbench"]["per_sample"]}
    sr_cls_labels = {s["id"]: s["unsafe"] for s in hb_asr["strongreject_harmbench_cls"]["per_sample"]}
    sr_score_map = {s["id"]: s["score"] for s in sr_scores["per_sample"]}

    hb_data = []
    for pid, behavior in hb_prompts.items():
        if pid not in hb_labels:
            continue
        props = compute_properties(behavior)
        props["id"] = pid
        props["unsafe"] = hb_labels[pid]
        hb_data.append(props)

    sr_data = []
    for pid, behavior in sr_prompts.items():
        if pid not in sr_cls_labels or pid not in sr_score_map:
            continue
        props = compute_properties(behavior)
        props["id"] = pid
        props["unsafe_cls"] = sr_cls_labels[pid]
        props["strongreject_score"] = sr_score_map[pid]
        sr_data.append(props)

    print(f"HarmBench samples: {len(hb_data)}, StrongREJECT samples: {len(sr_data)}")

    features = ["total_literal_length", "whitespace_count", "instruction_pattern_matches"]

    hb_correlations = {}
    for feat in features:
        x = [d[feat] for d in hb_data]
        y = [int(d["unsafe"]) for d in hb_data]
        hb_correlations[feat] = {
            "point_biserial_vs_unsafe": safe_corr(pointbiserialr, y, x),
        }

    sr_correlations = {}
    for feat in features:
        x = [d[feat] for d in sr_data]
        y_binary = [int(d["unsafe_cls"]) for d in sr_data]
        y_score = [d["strongreject_score"] for d in sr_data]
        sr_correlations[feat] = {
            "point_biserial_vs_harmbench_cls_unsafe": safe_corr(pointbiserialr, y_binary, x),
            "pearson_vs_strongreject_score": safe_corr(pearsonr, x, y_score),
            "spearman_vs_strongreject_score": safe_corr(spearmanr, x, y_score),
        }

    hb_stats = {
        "total_literal_length": {
            "mean": float(np.mean([d["total_literal_length"] for d in hb_data])),
            "std": float(np.std([d["total_literal_length"] for d in hb_data])),
            "min": int(min(d["total_literal_length"] for d in hb_data)),
            "max": int(max(d["total_literal_length"] for d in hb_data)),
        },
        "whitespace_count": {
            "mean": float(np.mean([d["whitespace_count"] for d in hb_data])),
            "std": float(np.std([d["whitespace_count"] for d in hb_data])),
        },
    }
    sr_stats = {
        "total_literal_length": {
            "mean": float(np.mean([d["total_literal_length"] for d in sr_data])),
            "std": float(np.std([d["total_literal_length"] for d in sr_data])),
            "min": int(min(d["total_literal_length"] for d in sr_data)),
            "max": int(max(d["total_literal_length"] for d in sr_data)),
        },
        "whitespace_count": {
            "mean": float(np.mean([d["whitespace_count"] for d in sr_data])),
            "std": float(np.std([d["whitespace_count"] for d in sr_data])),
        },
    }

    results = {
        "harmbench_set": {
            "n_samples": len(hb_data),
            "correlations": hb_correlations,
            "descriptive_stats": hb_stats,
        },
        "strongreject_set": {
            "n_samples": len(sr_data),
            "correlations": sr_correlations,
            "descriptive_stats": sr_stats,
        },
    }

    out_path = os.path.join(BASE, "results", "literal_property_correlations.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved correlations to {out_path}")

    fig_dir = os.path.join(BASE, "results", "figures")
    os.makedirs(fig_dir, exist_ok=True)

    lengths = [d["total_literal_length"] for d in sr_data]
    scores = [d["strongreject_score"] for d in sr_data]
    labels = [d["unsafe_cls"] for d in sr_data]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#2196F3" if not lbl else "#F44336" for lbl in labels]
    ax.scatter(lengths, scores, c=colors, alpha=0.6, s=30, edgecolors="none")

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#F44336',
               markersize=8, label='Unsafe (HarmBench cls)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2196F3',
               markersize=8, label='Safe (HarmBench cls)'),
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    r_p = sr_correlations["total_literal_length"]["pearson_vs_strongreject_score"]
    ax.set_xlabel("Total Forced Literal Length (chars)", fontsize=12)
    ax.set_ylabel("StrongREJECT Score", fontsize=12)
    ax.set_title(f"Literal Length vs Attack Success (N={len(sr_data)}, "
                 f"Pearson r={r_p['r']:.3f}, p={r_p['p']:.3f})", fontsize=12)
    ax.grid(True, alpha=0.3)

    fig_path = os.path.join(fig_dir, "literal_property_scatter.pdf")
    fig.savefig(fig_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"Saved scatter plot to {fig_path}")

    print("\n=== HarmBench Correlations ===")
    for feat, corrs in hb_correlations.items():
        for cname, cval in corrs.items():
            print(f"  {feat} | {cname}: r={cval['r']:.4f}, p={cval['p']:.4f}")

    print("\n=== StrongREJECT Correlations ===")
    for feat, corrs in sr_correlations.items():
        for cname, cval in corrs.items():
            print(f"  {feat} | {cname}: r={cval['r']:.4f}, p={cval['p']:.4f}")


if __name__ == "__main__":
    main()
