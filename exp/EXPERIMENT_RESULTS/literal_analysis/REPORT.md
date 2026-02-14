# Literal Property & Benign Modification Analysis

## Experiment Overview

Two complementary analyses examining the DeLex-JSON defense mechanism:
1. **Forced Literal Property Analysis**: Correlation between attack success and properties of forced enum literals (length, whitespace, instruction patterns).
2. **Benign Schema Modification Distribution**: Characterizing what types of benign schemas are affected by DeLex-JSON and why.

## Setup

- **Model**: Llama-3.1-8B-Instruct (No Defense EnumAttack results)
- **Safety Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Benign Dataset**: JSONSchemaBench (8,825 schemas across 7 subsets)
- **Metrics**: Point-biserial, Pearson, Spearman correlations; modification rates; TP/FP categorization

## Key Results

### Correlation Analysis

Literal length does NOT significantly correlate with attack success:
- HarmBench point-biserial r=0.056 (p=0.485)
- StrongREJECT Pearson r=-0.012 (p=0.826)
- StrongREJECT Spearman r=0.013 (p=0.818)

Whitespace count: negligible correlation (HarmBench r=0.054, StrongREJECT r=-0.025).

Instruction pattern matches: weak negative trend on StrongREJECT (Spearman r=-0.095, p=0.094), not significant on HarmBench (r=-0.045).

### Benign Modification Analysis

- Overall modification rate: 1.1% (100/8,825 schemas modified)
- Per-subset rates: Glaiveai2K 0%, Github_easy 0.5%, Github_medium 2.0%, Github_hard 3.0%, Kubernetes 0%, Snowplow 1.0%, JsonSchemaStore 2.0%
- Most affected: Github_hard (3.0%)

Manual inspection of 50 flagged literals:
- True Positive: 2 (4%) - contained actual instruction-like content
- False Positive: 38 (76%) - technical strings, identifiers, status messages
- Borderline: 10 (20%) - descriptive phrases not clearly malicious

### Threshold Tuning Recommendations

1. Increase length threshold from 20 to 40+ characters
2. Require 3 reasons instead of 2 for flagging
3. Add whitelist for known-safe patterns (URIs, MIME types, version strings)

## Key Observations

1. The attack mechanism operates independently of literal length -- the PRESENCE of instruction-like content matters, not the amount of text.
2. The current suspicion heuristic has a high false positive rate (76%) on benign schemas, but the overall schema modification rate remains low (1.1%).
3. Github_hard subset is most affected due to complex schemas with descriptive enum values.
4. The defense remains effective against attacks because attack payloads (harmful questions + affirmative prefixes) are consistently long, sentence-like, and match instruction patterns -- all three conditions together.

## Artifacts

- `results/literal_property_correlations.json`: Per-feature correlation data
- `results/benign_modification_analysis.json`: Benign modification stats + categorized samples
- `results/literal_analysis_summary.json`: Compiled summary
- `results/figures/literal_property_scatter.pdf`: Scatter plot (length vs StrongREJECT score)
- `results/figures/benign_modification_distribution.pdf`: Bar chart, histogram, pie chart
