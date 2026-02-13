# Selective DeLex-JSON Defense: Primary Model Evaluation

## Experiment Overview

Evaluated the Selective DeLex-JSON defense on Llama-3.1-8B-Instruct. DeLex-JSON is a training-free schema-to-schema transformation that:
1. Strips non-semantic free-text fields (description, title, examples, default)
2. Replaces suspicious forced literals (enum/const strings) with opaque placeholders (E0, E1, ...)

The suspicion function flags literals that match at least 2 of: length > 20, contains whitespace, matches instruction-like regex patterns, or matches affirmative prefix patterns. Requiring corroborating evidence (conjunction) minimizes false positives on benign schemas while catching all known attack payloads.

## Setup

- **Model**: meta-llama/Llama-3.1-8B-Instruct via vLLM v0.12.1
- **Attack**: EnumAttack (embeds harmful question + affirmative prefix as forced enum values)
- **Generation**: temperature=0.6, max_tokens=1024, constrained decoding via xgrammar
- **Safety Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Utility Datasets**: JSONSchemaBench (GlaiveAI-2K + Github_easy, ~3650 schemas), IFEval (17 JSON instances)
- **Safety Evaluation**: HarmBench classifier (cais/HarmBench-Llama-2-13b-cls), StrongREJECT rubric scoring (DeepSeek-V3 judge)
- **Utility Method**: Paired comparison -- only schemas where both DeLex and no-defense produce non-error results are compared, eliminating the confound of differential error rates from xgrammar memory leak

## Key Results

### Safety (EnumAttack with DeLex-JSON Defense)

| Metric | No Defense | Input Guard | Reject-Only | Escape-Hatch | **DeLex-JSON** |
|--------|-----------|-------------|-------------|--------------|----------------|
| HarmBench ASR | 22.0% | 3.8% | 0.0% | 22.0% | **0.0%** |
| StrongREJECT ASR (HB cls) | 15.3% | 2.9% | 0.0% | 15.3% | **2.6%** |
| StrongREJECT ASR (rubric) | 14.4% | 3.2% | 0.0% | 13.7% | **0.3%** |
| StrongREJECT score | 0.1030 | 0.0244 | 0.0000 | 0.0938 | **0.0016** |

- 100% of EnumAttack schemas were modified by the defense (all malicious enum literals detected)
- HarmBench ASR reduced from 22.0% to 0.0% (perfect defense, matches Reject-Only)
- StrongREJECT rubric score near zero (0.0016), only 1 out of 313 outputs scored > 0
- The 8 residual StrongREJECT classifier positives are false positives (all outputs are just "E2", StrongREJECT rubric correctly scores all 8 as 0.0 with refusal=1)

### Utility (JSONSchemaBench, Paired Comparison)

| Subset | Paired Schemas | DeLex Validity | NoDef Validity | Delta | DeLex Compliance | NoDef Compliance | Delta |
|--------|---------------|---------------|---------------|-------|-----------------|-----------------|-------|
| GlaiveAI-2K | 1706 | 99.53% | 99.82% | **-0.29pp** | 97.30% | 98.07% | **-0.76pp** |
| Github_easy | 1435 | 91.08% | 91.57% | **-0.49pp** | 88.85% | 89.48% | **-0.63pp** |
| **Overall** | **3141** | **95.67%** | **96.05%** | **-0.38pp** | **93.44%** | **94.14%** | **-0.70pp** |

### IFEval JSON Subset

- 17 instances with JSON output constraints
- Both DeLex and no-defense: 100% JSON validity
- Zero schemas modified (generic JSON schema has no enum/const)
- Zero degradation

### Benign Schema Modification Rate (FPR)

Across all 7 JSONSchemaBench subsets (8825 schemas): **1.1% modification rate** (100/8825)
- GlaiveAI-2K: 0.0%, Github_easy: 0.5%, Github_medium: 2.0%
- Github_hard: 3.0%, Kubernetes: 0.0%, Snowplow: 1.0%, JsonSchemaStore: 2.0%
- All flagged literals have 2+ corroborating reasons (length + whitespace)

## Key Observations

1. **Near-perfect safety**: DeLex-JSON achieves 0.0% HarmBench ASR and near-zero StrongREJECT scores, matching Reject-Only's safety while being less disruptive (doesn't refuse entire schemas).

2. **Minimal utility impact**: -0.38pp JSON validity and -0.70pp schema compliance degradation vs no defense (paired comparison). Well within the 2pp target.

3. **Better than Input Guard and Escape-Hatch**: DeLex-JSON achieves stronger safety than Input Guard (0.0% vs 3.8% HarmBench ASR) and much stronger than Escape-Hatch (0.0% vs 22.0%).

4. **Benign FPR well under 2% target**: 1.1% overall FPR, using conjunction-based suspicion (>= 2 corroborating criteria).

5. **Attack detection is complete**: 100% of EnumAttack schemas are correctly identified and modified. Malicious payloads (natural language sentences) always trigger multiple criteria simultaneously.

6. **Best Pareto point**: DeLex-JSON v2 achieves the best safety-utility tradeoff: near-perfect safety (0.0% HarmBench ASR), low FPR (1.1%), and minimal utility degradation (<1pp).
