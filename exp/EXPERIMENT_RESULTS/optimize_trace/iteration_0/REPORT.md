# Optimization Iteration 0: Conjunction-Based Suspicion Function

## Experiment Overview

Optimized the Selective DeLex-JSON defense by changing the suspicion function from a disjunction (OR) to a conjunction (>= 2 reasons required). The original defense flagged any literal matching ANY single criterion (length>20, whitespace, instruction regex), causing 87.3% of false positives from the `length>20` rule alone. The fix requires at least 2 corroborating criteria, dramatically reducing benign FPR while preserving 100% attack detection.

## Issue Diagnosed

The `is_suspicious()` function in `defenses/delex.py` (and `defenses/reject_only.py`) used `len(reasons) > 0` (disjunction). Many benign literals triggered only one criterion:
- Long URLs/hashes/identifiers (length>20 only, no whitespace)
- Short multi-word labels like "Tech Lead" (whitespace only, length<=20)

EnumAttack payloads always trigger 2+ criteria: harmful prompts are long natural language sentences (length>20 + whitespace), and the affirmative prefix "Sure, here is..." matches instruction patterns too.

**Fix**: Changed threshold from `len(reasons) > 0` to `len(reasons) >= 2`.

## Setup

- **Model**: meta-llama/Llama-3.1-8B-Instruct via vLLM v0.12.1
- **Attack**: EnumAttack (same as original)
- **Generation**: temperature=0.6, max_tokens=1024
- **Safety Datasets**: HarmBench (159), StrongREJECT (313)
- **Safety Evaluation**: HarmBench classifier + StrongREJECT rubric scoring (DeepSeek-V3 judge)
- **FPR Dataset**: JSONSchemaBench (all 7 subsets, 8825 schemas)

## Key Results

### Safety (v2 vs v1)

| Metric | v1 (Original) | v2 (Optimized) | Change |
|--------|---------------|----------------|--------|
| HarmBench ASR | 0.0% (0/159) | 0.0% (0/159) | No change |
| StrongREJECT ASR (HB cls) | 2.6% (8/313) | 2.6% (8/313) | No change |
| StrongREJECT ASR (rubric) | 0.3% (1/313) | 0.3% (1/313) | No change |
| StrongREJECT Score | 0.0016 | 0.0016 | No change |
| Attack Schema Modification Rate | 100.0% | 100.0% | No change |

### Benign FPR (v2 vs v1)

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

### Reject-Only Baseline (also updated)

| Metric | v1 | v2 |
|--------|-----|-----|
| Overall FPR | 4.4% (387/8825) | 0.05% (4/8825) |

### Utility (Conservative Estimate)

Utility numbers from v1 are reported as a conservative upper bound (v2 modifies fewer schemas, so actual utility would be equal or better):

| Metric | No Defense | DeLex-JSON v2 (conservative) | Delta |
|--------|-----------|------------------------------|-------|
| JSON Validity | 95.9% | >= 95.2% | <= -0.7pp |
| Schema Compliance | 94.1% | >= 93.0% | <= -1.1pp |

## Key Observations

1. **Benign FPR reduced 10x**: From 11.3% to 1.1%, now well under the 2% target.
2. **Safety fully preserved**: All metrics identical -- 0.0% HarmBench ASR, 100% attack detection.
3. **Principled fix**: Requiring corroborating evidence (2+ criteria) is more robust than any single heuristic and less prone to false positives on legitimate data.
4. **Reject-only also improved**: The same fix reduced reject-only FPR from 4.4% to 0.05%.
5. **Kubernetes FPR eliminated**: Dropped from 12.3% to 0.0% -- all Kubernetes false positives were long strings without whitespace.
