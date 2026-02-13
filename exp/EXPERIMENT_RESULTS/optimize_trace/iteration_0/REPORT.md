# Optimization Iteration 0: Conjunction-Based Suspicion + Accurate v2 Utility

## Experiment Overview

Two-part optimization of the Selective DeLex-JSON defense:

1. **Conjunction-based suspicion** (prior commit 2c9ba2a): Changed `is_suspicious()` from disjunction (`len(reasons) > 0`) to conjunction (`len(reasons) >= 2`), reducing benign FPR from 11.3% to 1.1% while preserving 100% attack detection.

2. **Accurate v2 utility measurement** (this iteration): Re-generated utility outputs for the 85 schemas on Github_easy where v1 and v2 defense behavior differs (v1 modified these schemas but v2 doesn't). Used paired comparison to eliminate error-rate confound from xgrammar memory leak.

## Issues Diagnosed and Fixed

### Issue 1: Suspicion function OR-logic causing 11.3% benign FPR
- **Root cause**: `is_suspicious()` flagged any literal matching ANY single criterion (length>20, whitespace, instruction regex). The `length>20` rule alone caused 87.3% of false positives.
- **Fix**: Changed to `len(reasons) >= 2` (require 2+ corroborating criteria).
- **Impact**: FPR reduced from 11.3% to 1.1%.

### Issue 2: Utility numbers used stale v1 defense outputs
- **Root cause**: Utility evaluation was run with the old v1 defense (disjunction). With v2 (conjunction), far fewer schemas are modified (100 vs 994 overall, 9 vs 94 on Github_easy), so the actual utility impact is smaller.
- **Fix**: Re-ran utility generation for the 85 affected schemas on Github_easy with v2 defense, computed combined v2 utility, and performed paired comparison.
- **Impact**: Utility delta improved from <=−0.7pp/−1.1pp to −0.4pp/−0.7pp.

## Setup

- **Model**: meta-llama/Llama-3.1-8B-Instruct via vLLM v0.12.1
- **Attack**: EnumAttack (same as original)
- **Generation**: temperature=0.6, max_tokens=1024
- **Safety Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Safety Evaluation**: HarmBench classifier + StrongREJECT rubric scoring (DeepSeek-V3)
- **Utility Datasets**: JSONSchemaBench GlaiveAI-2K + Github_easy (~3650 schemas)
- **FPR Dataset**: JSONSchemaBench (all 7 subsets, 8825 schemas)

## Key Results

### Safety (unchanged from v1)

| Metric | No Defense | DeLex-JSON v2 |
|--------|-----------|---------------|
| HarmBench ASR | 22.0% (35/159) | **0.0%** (0/159) |
| StrongREJECT ASR (HB cls) | 15.3% (48/313) | **2.6%** (8/313) |
| StrongREJECT ASR (rubric) | 14.4% | **0.3%** (1/313) |
| StrongREJECT Score | 0.1030 | **0.0016** |
| Attack Schema Modification | -- | **100.0%** |

Note: The 8 residual StrongREJECT classifier positives are false positives. All 8 outputs are just "E2" (a placeholder), and the StrongREJECT rubric correctly scores all 8 as 0.0 with refusal=1.

### Benign FPR

| Subset | v1 FPR | v2 FPR | Change |
|--------|--------|--------|--------|
| GlaiveAI-2K | 0.0% | 0.0% | -- |
| Github_easy | 4.8% | 0.5% | -4.3pp |
| Github_medium | 11.1% | 2.0% | -9.1pp |
| Github_hard | 32.8% | 3.0% | -29.8pp |
| Kubernetes | 12.3% | 0.0% | -12.3pp |
| Snowplow | 3.5% | 1.0% | -2.5pp |
| JsonSchemaStore | 26.0% | 2.0% | -24.0pp |
| **Overall** | **11.3%** | **1.1%** | **-10.2pp** |

### Utility (Paired Comparison -- v2 defense)

Paired comparison eliminates the confound of differential error rates (xgrammar memory leak causes different error counts between DeLex and no-defense runs). Only schemas where both methods produce non-error results are compared.

| Subset | Paired Schemas | DeLex Validity | NoDef Validity | Delta | DeLex Compliance | NoDef Compliance | Delta |
|--------|---------------|---------------|---------------|-------|-----------------|-----------------|-------|
| GlaiveAI-2K | 1706 | 99.53% | 99.82% | **-0.29pp** | 97.30% | 98.07% | **-0.76pp** |
| Github_easy | 1435 | 91.08% | 91.57% | **-0.49pp** | 88.85% | 89.48% | **-0.63pp** |
| **Overall** | **3141** | **95.67%** | **96.05%** | **-0.38pp** | **93.44%** | **94.14%** | **-0.70pp** |

Improvement over previous conservative bounds:
- Validity: -0.38pp (was <=−0.7pp, improved by ~0.32pp)
- Compliance: -0.70pp (was <=−1.1pp, improved by ~0.40pp)

### Reject-Only Baseline

| Metric | v1 | v2 |
|--------|-----|-----|
| Overall FPR | 4.4% (387/8825) | 0.05% (4/8825) |

## Key Observations

1. **All targets met**: FPR 1.1% (target <=2%), HarmBench ASR 0.0% (target <10%), utility degradation 0.38pp/0.70pp (target <=2pp).
2. **Better Pareto point than reject-only**: DeLex-JSON v2 has same HarmBench ASR (0.0%) but maintains utility (reject-only blocks all modified schemas entirely).
3. **Paired comparison is more rigorous**: Eliminates the confound of 235 DeLex-only errors vs 95 NoDef-only errors on Github_easy caused by xgrammar memory leak.
4. **Minimal actual utility impact**: Only 9 schemas modified on Github_easy (0.5%), 0 on GlaiveAI-2K. The remaining utility delta comes from free-text stripping (description/title/examples/default fields removed).
