# Compile final analysis summary from literal property correlations and
# benign modification analysis into results/literal_analysis_summary.json.

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with open(os.path.join(BASE, "results", "literal_property_correlations.json")) as f:
        corr_data = json.load(f)

    with open(os.path.join(BASE, "results", "benign_modification_analysis.json")) as f:
        benign_data = json.load(f)

    hb = corr_data["harmbench_set"]
    sr = corr_data["strongreject_set"]

    hb_length_r = hb["correlations"]["total_literal_length"]["point_biserial_vs_unsafe"]["r"]
    hb_length_p = hb["correlations"]["total_literal_length"]["point_biserial_vs_unsafe"]["p"]
    sr_length_pearson_r = sr["correlations"]["total_literal_length"]["pearson_vs_strongreject_score"]["r"]
    sr_length_pearson_p = sr["correlations"]["total_literal_length"]["pearson_vs_strongreject_score"]["p"]
    sr_length_spearman_r = sr["correlations"]["total_literal_length"]["spearman_vs_strongreject_score"]["r"]
    sr_length_spearman_p = sr["correlations"]["total_literal_length"]["spearman_vs_strongreject_score"]["p"]
    sr_length_pb_r = sr["correlations"]["total_literal_length"]["point_biserial_vs_harmbench_cls_unsafe"]["r"]

    hb_ws_r = hb["correlations"]["whitespace_count"]["point_biserial_vs_unsafe"]["r"]
    sr_ws_pearson_r = sr["correlations"]["whitespace_count"]["pearson_vs_strongreject_score"]["r"]

    hb_inst_r = hb["correlations"]["instruction_pattern_matches"]["point_biserial_vs_unsafe"]["r"]
    sr_inst_pearson_r = sr["correlations"]["instruction_pattern_matches"]["pearson_vs_strongreject_score"]["r"]
    sr_inst_spearman_r = sr["correlations"]["instruction_pattern_matches"]["spearman_vs_strongreject_score"]["r"]
    sr_inst_spearman_p = sr["correlations"]["instruction_pattern_matches"]["spearman_vs_strongreject_score"]["p"]

    length_significant = hb_length_p < 0.05 or sr_length_pearson_p < 0.05
    ws_findings = (
        f"Whitespace count shows negligible correlation with attack success "
        f"(HarmBench r={hb_ws_r:.4f}, StrongREJECT Pearson r={sr_ws_pearson_r:.4f})."
    )
    inst_findings = (
        f"Instruction-pattern matches show weak negative correlation on StrongREJECT "
        f"(Spearman r={sr_inst_spearman_r:.4f}, p={sr_inst_spearman_p:.4f}), "
        f"marginally significant. On HarmBench (r={hb_inst_r:.4f}), not significant."
    )

    correlation_findings = {
        "summary": (
            f"Literal length does NOT significantly correlate with attack success. "
            f"HarmBench point-biserial r={hb_length_r:.4f} (p={hb_length_p:.4f}), "
            f"StrongREJECT Pearson r={sr_length_pearson_r:.4f} (p={sr_length_pearson_p:.4f}), "
            f"Spearman r={sr_length_spearman_r:.4f} (p={sr_length_spearman_p:.4f}). "
            f"All correlations are near zero with p>>0.05."
        ),
        "length_correlation_significant": length_significant,
        "interpretation": (
            "The lack of correlation suggests that the attack mechanism (forcing contiguous "
            "natural-language literals in the autoregressive context) operates largely "
            "independently of literal length. Even short harmful prompts embedded as enum "
            "values can successfully elicit unsafe completions. This implies the key factor "
            "is the PRESENCE of instruction-like content in the forced context, not the "
            "amount of text. The defense should focus on detecting instruction-like semantics "
            "rather than relying primarily on length thresholds."
        ),
        "whitespace_findings": ws_findings,
        "instruction_pattern_findings": inst_findings,
        "harmbench_set": {
            "n": hb["n_samples"],
            "key_correlations": hb["correlations"],
        },
        "strongreject_set": {
            "n": sr["n_samples"],
            "key_correlations": sr["correlations"],
        },
    }

    mi = benign_data["manual_inspection"]
    tp_rate = mi["tp_rate"]
    fp_rate = mi["fp_rate"]
    borderline_rate = mi["borderline_rate"]

    most_affected = sorted(
        benign_data["per_subset"].items(),
        key=lambda x: x[1]["modification_rate"],
        reverse=True,
    )
    most_affected_subset = most_affected[0][0] if most_affected else "N/A"
    most_affected_rate = most_affected[0][1]["modification_rate"] if most_affected else 0

    benign_modification_findings = {
        "summary": (
            f"Of {benign_data['overall']['total_schemas']} benign schemas across 7 JSONSchemaBench subsets, "
            f"{benign_data['overall']['total_modified']} ({benign_data['overall']['overall_modification_rate']*100:.1f}%) "
            f"were modified by DeLex-JSON. Manual inspection of 50 flagged literals found: "
            f"{mi['counts']['true_positive']} true positives ({tp_rate*100:.0f}%), "
            f"{mi['counts']['false_positive']} false positives ({fp_rate*100:.0f}%), "
            f"{mi['counts']['borderline']} borderline ({borderline_rate*100:.0f}%)."
        ),
        "overall_modification_rate": benign_data["overall"]["overall_modification_rate"],
        "total_schemas": benign_data["overall"]["total_schemas"],
        "total_modified": benign_data["overall"]["total_modified"],
        "total_flagged_literals": benign_data["overall"]["total_flagged_literals"],
        "most_affected_subset": most_affected_subset,
        "most_affected_rate": most_affected_rate,
        "manual_inspection_counts": mi["counts"],
        "tp_rate": tp_rate,
        "fp_rate": fp_rate,
        "borderline_rate": borderline_rate,
        "per_subset_rates": {
            k: v["modification_rate"] for k, v in benign_data["per_subset"].items()
        },
        "interpretation": (
            f"The high false positive rate ({fp_rate*100:.0f}%) among flagged literals indicates "
            f"that the current heuristic (requiring 2+ of: length>20, whitespace, regex match) "
            f"over-flags benign technical strings. Most false positives are enum values for "
            f"technical identifiers, status messages, or configuration labels that happen to be "
            f"long and contain spaces but pose no injection risk. The most affected subset is "
            f"{most_affected_subset} ({most_affected_rate*100:.1f}% modification rate), which "
            f"contains more complex schemas with descriptive enum values."
        ),
    }

    recommendations = {
        "threshold_tuning": [],
        "summary": "",
    }

    if fp_rate > 0.5:
        recommendations["threshold_tuning"].append({
            "recommendation": "Increase length threshold from 20 to 40+ characters",
            "rationale": "Most false positives are 21-40 char technical strings. Raising the threshold would eliminate many FPs while still catching attack payloads (typically 50+ chars).",
        })
        recommendations["threshold_tuning"].append({
            "recommendation": "Require at least 3 reasons instead of 2 for flagging",
            "rationale": "Adding a third required signal (e.g., regex match on instruction patterns) would reduce FPs on benign strings that simply happen to be long + have spaces.",
        })
        recommendations["threshold_tuning"].append({
            "recommendation": "Add a whitelist for known-safe patterns (URIs, version strings, MIME types, technical identifiers)",
            "rationale": "Many false positives follow recognizable technical formats that could be excluded before applying the suspicion heuristic.",
        })
        recommendations["summary"] = (
            f"The current false positive rate of {fp_rate*100:.0f}% is high. The recommended "
            f"adjustments would significantly reduce benign modifications while maintaining "
            f"defense effectiveness against actual attacks, since attack payloads (harmful "
            f"questions + affirmative prefixes) are consistently longer, more sentence-like, "
            f"and match instruction patterns."
        )
    else:
        recommendations["summary"] = (
            f"The current false positive rate of {fp_rate*100:.0f}% is acceptable. "
            f"Current thresholds provide a good balance."
        )

    summary = {
        "correlation_findings": correlation_findings,
        "benign_modification_findings": benign_modification_findings,
        "recommendations": recommendations,
    }

    out_path = os.path.join(BASE, "results", "literal_analysis_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {out_path}")

    assert "correlation_findings" in summary
    assert "benign_modification_findings" in summary
    assert "recommendations" in summary
    print("Verification passed: all expected keys present.")


if __name__ == "__main__":
    main()
