# Analyze benign schema modifications from DeLex-JSON on JSONSchemaBench.
# Computes per-subset stats, categorizes ~50 flagged literals as TP/FP/borderline,
# and produces visualizations.

import json
import os
import random
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TECHNICAL_PATTERNS = [
    re.compile(r"^https?://", re.IGNORECASE),
    re.compile(r"^[a-zA-Z]:\\"),
    re.compile(r"^/[a-z]+/", re.IGNORECASE),
    re.compile(r"\.(json|xml|yaml|yml|txt|csv|html|css|js|py|go|rs|java|sh|bat)$", re.IGNORECASE),
    re.compile(r"^\d+\.\d+\.\d+"),
    re.compile(r"^v\d+", re.IGNORECASE),
    re.compile(r"^[A-Z_]{3,}$"),
    re.compile(r"^[a-z]+[A-Z][a-zA-Z]*$"),
    re.compile(r"^[a-z]+[-_][a-z]+[-_]", re.IGNORECASE),
    re.compile(r"^\{[%{]"),
    re.compile(r"^urn:", re.IGNORECASE),
    re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}", re.IGNORECASE),
    re.compile(r"^application/|^text/|^image/", re.IGNORECASE),
]

INSTRUCTION_VERBS = re.compile(
    r"\b(make|create|write|explain|describe|tell|give|show|provide|list|help|"
    r"generate|build|design|develop|implement|configure|set up|install|run|"
    r"execute|deploy|start|stop|remove|delete|update|modify|change|fix|"
    r"solve|answer|respond|reply|say|ask|request|command|instruct|guide|"
    r"teach|learn|read|open|close|send|receive|download|upload)\b",
    re.IGNORECASE,
)

SENTENCE_PATTERN = re.compile(r"[A-Z][a-z].*\s.*[.!?]$")


def categorize_literal(original: str) -> str:
    for pat in TECHNICAL_PATTERNS:
        if pat.search(original):
            return "false_positive"

    has_verb = bool(INSTRUCTION_VERBS.search(original))
    is_sentence = bool(SENTENCE_PATTERN.search(original))
    word_count = len(original.split())

    if is_sentence and has_verb and word_count >= 5:
        return "true_positive"
    if has_verb and word_count >= 6:
        return "true_positive"

    if word_count <= 3 and not has_verb:
        return "false_positive"

    if not has_verb and word_count <= 5:
        return "false_positive"

    return "borderline"


def main():
    with open(os.path.join(BASE, "results", "delex_llama31_fpr_v2.json")) as f:
        fpr_data = json.load(f)

    per_subset_raw = fpr_data.get("per_subset", {})
    modified_details = fpr_data.get("modified_details", [])

    all_changes = []
    for entry in modified_details:
        subset = entry.get("subset", "unknown")
        fname = entry.get("file", "")
        for ch in entry.get("changes", []):
            ch_copy = dict(ch)
            ch_copy["subset"] = subset
            ch_copy["file"] = fname
            all_changes.append(ch_copy)

    print(f"Total schemas modified: {len(modified_details)}")
    print(f"Total individual literals flagged: {len(all_changes)}")

    per_subset_stats = {}
    for subset, info in per_subset_raw.items():
        per_subset_stats[subset] = {
            "total_schemas": info["total"],
            "modified_schemas": info["modified"],
            "modification_rate": info["modification_rate"],
            "suspicious_literals": info.get("suspicious_literals", 0),
            "reason_counts": info.get("reason_counts", {}),
        }

    literal_lengths = [len(ch["original"]) for ch in all_changes]

    reason_totals = {}
    for ch in all_changes:
        for r in ch.get("reasons", []):
            reason_totals[r] = reason_totals.get(r, 0) + 1

    random.seed(42)
    sample_size = min(50, len(all_changes))
    sampled = random.sample(all_changes, sample_size)

    categorized_samples = []
    counts = {"true_positive": 0, "false_positive": 0, "borderline": 0}
    for s in sampled:
        cat = categorize_literal(s["original"])
        counts[cat] += 1
        categorized_samples.append({
            "original": s["original"],
            "subset": s["subset"],
            "file": s["file"],
            "reasons": s.get("reasons", []),
            "category": cat,
        })

    print(f"\nManual inspection of {sample_size} literals:")
    print(f"  True Positive:  {counts['true_positive']}")
    print(f"  False Positive: {counts['false_positive']}")
    print(f"  Borderline:     {counts['borderline']}")

    results = {
        "overall": {
            "total_schemas": fpr_data.get("total_schemas", 0),
            "total_modified": fpr_data.get("total_modified", 0),
            "overall_modification_rate": fpr_data.get("overall_modification_rate", 0),
            "total_flagged_literals": len(all_changes),
            "reason_totals": reason_totals,
        },
        "per_subset": per_subset_stats,
        "literal_length_stats": {
            "mean": float(np.mean(literal_lengths)) if literal_lengths else 0,
            "std": float(np.std(literal_lengths)) if literal_lengths else 0,
            "median": float(np.median(literal_lengths)) if literal_lengths else 0,
            "min": int(min(literal_lengths)) if literal_lengths else 0,
            "max": int(max(literal_lengths)) if literal_lengths else 0,
        },
        "manual_inspection": {
            "sample_size": sample_size,
            "counts": counts,
            "tp_rate": counts["true_positive"] / sample_size if sample_size > 0 else 0,
            "fp_rate": counts["false_positive"] / sample_size if sample_size > 0 else 0,
            "borderline_rate": counts["borderline"] / sample_size if sample_size > 0 else 0,
            "samples": categorized_samples,
        },
    }

    out_path = os.path.join(BASE, "results", "benign_modification_analysis.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved analysis to {out_path}")

    fig_dir = os.path.join(BASE, "results", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    pdf_path = os.path.join(fig_dir, "benign_modification_distribution.pdf")

    with PdfPages(pdf_path) as pdf:
        subsets_ordered = ["Glaiveai2K", "Github_easy", "Github_medium", "Github_hard",
                           "Kubernetes", "Snowplow", "JsonSchemaStore"]
        rates = [per_subset_stats.get(s, {}).get("modification_rate", 0) for s in subsets_ordered]

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(range(len(subsets_ordered)), [r * 100 for r in rates],
                      color="#42A5F5", edgecolor="white")
        ax.set_xticks(range(len(subsets_ordered)))
        ax.set_xticklabels(subsets_ordered, rotation=30, ha="right", fontsize=10)
        ax.set_ylabel("Schema Modification Rate (%)", fontsize=12)
        ax.set_title("DeLex-JSON Benign Schema Modification Rate by Subset", fontsize=13)
        ax.grid(axis="y", alpha=0.3)
        for bar, rate in zip(bars, rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                        f"{rate*100:.1f}%", ha="center", va="bottom", fontsize=9)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 5))
        if literal_lengths:
            ax.hist(literal_lengths, bins=30, color="#66BB6A", edgecolor="white", alpha=0.8)
        ax.set_xlabel("Flagged Literal Length (characters)", fontsize=12)
        ax.set_ylabel("Count", fontsize=12)
        ax.set_title(f"Distribution of Flagged Literal Lengths (N={len(literal_lengths)})", fontsize=13)
        ax.axvline(x=20, color="red", linestyle="--", alpha=0.7, label="Threshold (20 chars)")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 6))
        if reason_totals:
            labels_clean = []
            for k in reason_totals:
                if k.startswith("regex:"):
                    labels_clean.append("Regex match")
                elif k == "length>20":
                    labels_clean.append("Length > 20")
                elif k == "whitespace":
                    labels_clean.append("Contains whitespace")
                else:
                    labels_clean.append(k)
            merged = {}
            for lbl, k in zip(labels_clean, reason_totals):
                merged[lbl] = merged.get(lbl, 0) + reason_totals[k]
            colors_pie = ["#42A5F5", "#66BB6A", "#FFA726", "#AB47BC", "#EF5350"]
            ax.pie(list(merged.values()), labels=list(merged.keys()),
                   autopct="%1.1f%%", colors=colors_pie[:len(merged)],
                   startangle=90, textprops={"fontsize": 11})
            ax.set_title("Trigger Reason Distribution for Flagged Literals", fontsize=13)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    print(f"Saved visualizations to {pdf_path}")


if __name__ == "__main__":
    main()
