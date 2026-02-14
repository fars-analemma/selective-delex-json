# Ablation Study: Selective DeLex-JSON Component Analysis

## Experiment Overview

This ablation study isolates the contribution of each component of Selective DeLex-JSON by comparing three ablation variants against the full method and no-defense baseline on Llama-3.1-8B-Instruct.

**Variants:**
1. **Strip-Only**: Remove free-text schema fields (description, title, examples, default) but do NOT replace any enum/const string literals.
2. **Delex-All**: Replace ALL enum/const string literals with placeholders unconditionally, regardless of the suspicion function.
3. **Heuristic-Only**: Use only the rule-based suspicion function (length>20, whitespace, regex patterns) without an optional guard model.

## Setup

- **Model**: meta-llama/Llama-3.1-8B-Instruct
- **Safety Evaluation**: EnumAttack on HarmBench (159 prompts), ASR measured by HarmBench classifier (cais/HarmBench-Llama-2-13b-cls)
- **Utility Evaluation**: JSONSchemaBench (GlaiveAI-2K + Github_easy, ~3592 schemas), measuring JSON validity and schema compliance
- **FPR Evaluation**: All 7 JSONSchemaBench subsets (8825 schemas), measuring benign schema modification rate
- **Infrastructure**: 3 parallel 1-GPU TrainService jobs for safety+utility, 1 GPU for classifier eval
- **Constrained Decoding**: vLLM with xgrammar backend, batch-restart pattern for memory management

## Key Results

| Variant | ASR (HarmBench) | Benign Mod Rate | JSON Validity | Schema Compliance |
|---------|:-----------:|:----------:|:----------:|:----------:|
| No Defense | 22.0% | 0.0% | 95.9% | 94.1% |
| **Full DeLex-JSON** | **0.0%** | **1.1%** | **95.4%** | **93.1%** |
| Strip-Only | 22.0% | 0.0% | 95.2% | 93.4% |
| Delex-All | 0.0% | 35.5% | 94.5% | 92.1% |
| Heuristic-Only | 0.0% | 1.1% | 95.4% | 93.1% |

## Key Observations

### 1. Strip-Only vs Full: Forced Literals Are the Key Attack Vector

Strip-Only achieves the same ASR as No Defense (22.0%), demonstrating that removing free-text metadata (description, title, examples, default) has **zero impact on safety**. The attack payload is entirely carried by forced enum/const string literals, not by auxiliary schema metadata. Stripping metadata alone is insufficient as a defense.

Utility is nearly identical to No Defense (validity 95.2% vs 95.9%, compliance 93.4% vs 94.1%), with no benign schema modification (0.0% FPR), confirming that metadata stripping is non-destructive.

### 2. Delex-All vs Full: Selective Delexicalization Preserves More Utility

Delex-All achieves the same perfect safety (0.0% ASR) as the full method, but at a significant utility cost:
- **35.5% benign modification rate** vs 1.1% for Full DeLex-JSON (32x higher false positive rate)
- **-0.9pp JSON validity** (94.5% vs 95.4%) and **-1.0pp schema compliance** (92.1% vs 93.1%)

This proves that the suspicion function is critical for maintaining utility. Blanket delexicalization unnecessarily modifies benign schemas containing short identifiers (e.g., 'GET', 'POST', 'active', 'pending') that are never used as attack vectors.

### 3. Heuristic-Only vs Full: Rule-Based Heuristic Alone Is Sufficient

Heuristic-Only produces results **identical** to Full DeLex-JSON across all metrics. This is expected because the full method never actually used an optional guard model (Llama Guard) -- both rely solely on the conjunction-based suspicion function (requires >= 2 of: length>20, whitespace, regex patterns). The rule-based heuristic alone is sufficient for the current threat model.

### Summary

The ablation confirms that:
- **Literal delexicalization** (not metadata stripping) is the essential safety mechanism
- **Selective** delexicalization via the suspicion function is critical for utility preservation
- The **rule-based heuristic** alone is sufficient; no guard model is needed
