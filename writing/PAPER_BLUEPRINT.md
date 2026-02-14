# Paper Blueprint: Selective Delexicalization to Defend Structured-Output LLM APIs from Control-Plane Jailbreaks

## Meta Information
- **Analysis Date**: 2026-02-14
- **Experiments Analyzed**: 8 (No Defense, Input Guard, Reject-Only, Escape-Hatch, DeLex-JSON on Llama-3.1-8B, DeLex-JSON on Qwen2.5-7B, Ablation Study, Chunked Probe)
- **Figures Generated**: 1 method diagram (framework_overview.jpeg)
- **Tables Planned**: 3 (Main Safety Results, Utility/Overhead, Ablation)

## Claims

### claim_1: defense_effectiveness
**Statement**: Selective DeLex-JSON reduces EnumAttack success rate from 22.0% to 0.0% on HarmBench and from 15.3% to 2.6% on StrongREJECT for Llama-3.1-8B-Instruct, achieving near-perfect defense against control-plane jailbreaks.
**Evidence**: delex_llama31 experiment - HarmBench ASR: 0/159 (0.0%), StrongREJECT ASR: 8/313 (2.6% classifier, 0.3% rubric)
**Figures**: tab_main_safety
**Tables**: tab_main_safety

### claim_2: utility_preservation
**Statement**: Selective DeLex-JSON preserves structured output utility with only 0.38 percentage point degradation in JSON validity and 0.70 percentage point degradation in schema compliance on JSONSchemaBench, well within the 2pp threshold.
**Evidence**: delex_llama31 utility evaluation - paired comparison on 3141 schemas
**Figures**: None
**Tables**: tab_utility

### claim_3: low_false_positive_rate
**Statement**: The conjunction-based suspicion function achieves only 1.1% benign schema modification rate across 8,825 JSONSchemaBench schemas, compared to 4.4% rejection rate for the Reject-Only baseline.
**Evidence**: delex_llama31 overhead metrics - 100/8825 schemas modified
**Figures**: None
**Tables**: tab_utility

### claim_4: pareto_dominance
**Statement**: Selective DeLex-JSON achieves a strictly better Pareto point than Reject-Only: identical 0.0% HarmBench ASR with 3.3 percentage points lower benign cost (1.1% modification vs. 4.4% rejection).
**Evidence**: Comparison of delex_llama31 vs reject_only_llama31 results
**Figures**: fig_pareto
**Tables**: tab_main_safety

### claim_5: cross_model_generalization
**Statement**: Selective DeLex-JSON generalizes across model families, reducing HarmBench ASR from 10.7% to 0.0% on Qwen2.5-7B-Instruct with zero utility degradation on GlaiveAI-2K.
**Evidence**: delex_qwen25 experiment results
**Figures**: None
**Tables**: tab_main_safety

### claim_6: ablation_forced_literals
**Statement**: Forced enum/const literals are the key attack vector: Strip-Only (metadata removal without delexicalization) achieves identical 22.0% ASR as No Defense, while full DeLex-JSON achieves 0.0% ASR.
**Evidence**: ablation_study results - Strip-Only ASR = 22.0%, Full DeLex-JSON ASR = 0.0%
**Figures**: None
**Tables**: tab_ablation

### claim_7: selective_vs_blanket
**Statement**: Selective delexicalization preserves utility better than blanket delexicalization: Delex-All achieves 0.0% ASR but with 35.5% benign modification rate (vs. 1.1% for selective), demonstrating the value of the suspicion function.
**Evidence**: ablation_study results - Delex-All modification rate = 35.5%
**Figures**: None
**Tables**: tab_ablation

### claim_8: chunked_attack_limitation
**Statement**: Chunked-payload attacks that distribute harmful content across many short enum values (≤20 chars each) bypass the suspicion function, representing a known limitation of the current defense.
**Evidence**: chunked_probe results - 0% of chunks flagged at any chunk size, ASR ~10-14% for both defended and undefended conditions
**Figures**: fig_chunked_probe
**Tables**: None

## Figure-Table Plan

**Purpose**: Prevent redundancy by deciding upfront what data goes into figures vs tables.

**Core Requirements**:
- **Main results table (REQUIRED)**: Main experimental results must be in table format with precise values

### Main Results Table (REQUIRED)
- Main safety comparison: All 5 defense methods × 2 benchmarks (HarmBench, StrongREJECT) with ASR values
- Cross-model generalization: Llama-3.1-8B and Qwen2.5-7B results
- Source: Individual experiment RESULTS.json files

### Additional Tables
- **Utility/Overhead Table**: Benign modification rates per subset, JSON validity/compliance deltas
- **Ablation Table**: Component contribution analysis (Strip-Only, Delex-All, Heuristic-Only)

### Figures (analytical insights)
- **Pareto Frontier (fig_pareto)**: Safety vs. utility tradeoff visualization - shows DeLex-JSON dominates Reject-Only
- **Chunked Probe (fig_chunked_probe)**: ASR vs. chunk size trend - shows limitation of current defense

### Redundancy Check
- ❌ Main safety results are in table only (not duplicated as bar chart)
- ❌ Utility metrics are in table only (not duplicated as figure)
- ✅ Pareto frontier shows unique relationship visualization
- ✅ Chunked probe shows trend across chunk sizes (unique analytical insight)

