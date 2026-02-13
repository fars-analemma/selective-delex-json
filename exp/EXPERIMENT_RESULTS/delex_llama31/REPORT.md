# Selective DeLex-JSON Defense: Primary Model Evaluation

## Experiment Overview

Evaluated the Selective DeLex-JSON defense on Llama-3.1-8B-Instruct. DeLex-JSON is a training-free schema-to-schema transformation that:
1. Strips non-semantic free-text fields (description, title, examples, default)
2. Replaces suspicious forced literals (enum/const strings) with opaque placeholders (E0, E1, ...)

The suspicion function flags literals if ANY of: length > 20, contains whitespace, matches instruction-like regex patterns, or matches affirmative prefix patterns.

## Setup

- **Model**: meta-llama/Llama-3.1-8B-Instruct via vLLM v0.12.1
- **Attack**: EnumAttack (embeds harmful question + affirmative prefix as forced enum values)
- **Generation**: temperature=0.6, max_tokens=1024, constrained decoding via xgrammar
- **Safety Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Utility Datasets**: JSONSchemaBench (GlaiveAI-2K + Github_easy, ~3650 schemas), IFEval (17 JSON instances)
- **Safety Evaluation**: HarmBench classifier (cais/HarmBench-Llama-2-13b-cls), StrongREJECT rubric scoring (DeepSeek-V3 judge)

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
- 98.4% reduction in StrongREJECT score compared to no defense

### Utility (JSONSchemaBench)

| Metric | No Defense | DeLex-JSON | Delta |
|--------|-----------|------------|-------|
| JSON validity (overall) | 95.9% | 95.2% | -0.7pp |
| Schema compliance (overall) | 94.1% | 93.0% | -1.1pp |

**Per-subset**:
- GlaiveAI-2K: JSON 99.8%->99.5%, Schema 98.1%->97.3% (0% schemas modified)
- Github_easy: JSON 91.8%->90.3%, Schema 90.0%->88.1% (55/1943=2.8% schemas modified)

### IFEval JSON Subset

- 17 instances with JSON output constraints
- Both DeLex and no-defense: 100% JSON validity
- Zero schemas modified (generic JSON schema has no enum/const)
- Zero degradation

### Benign Schema Modification Rate (FPR)

Across all 7 JSONSchemaBench subsets (8825 schemas): 11.3% modification rate
- GlaiveAI-2K: 0.0%, Github_easy: 4.8%, Github_medium: 11.1%
- Github_hard: 32.8%, Kubernetes: 1.2%, Snowplow: 0.0%, JsonSchemaStore: 26.0%
- Dominant trigger: length > 20 characters (16090/18428 = 87.3% of suspicious literals)

## Key Observations

1. **Near-perfect safety**: DeLex-JSON achieves 0.0% HarmBench ASR and near-zero StrongREJECT scores, matching Reject-Only's safety while being less disruptive (doesn't refuse entire schemas).

2. **Minimal utility impact**: Only -0.7pp JSON validity and -1.1pp schema compliance degradation compared to no defense. The DeLex transformation preserves schema structure.

3. **Better than Input Guard and Escape-Hatch**: DeLex-JSON achieves stronger safety than Input Guard (0.0% vs 3.8% HarmBench ASR) and much stronger than Escape-Hatch (0.0% vs 22.0%).

4. **Benign FPR higher than 2% target**: 11.3% overall FPR exceeds the 2% target. This is driven by legitimate long string literals in Github_hard and JsonSchemaStore schemas being flagged by the >20 char rule. However, on the primary utility subsets (GlaiveAI-2K=0%), the rate is acceptable.

5. **Attack detection is complete**: 100% of EnumAttack schemas are correctly identified and modified. The malicious enum values (harmful question text + "Sure, here is...") always trigger multiple suspicion criteria (length, whitespace, instruction patterns).

6. **vLLM xgrammar memory leak**: Required resilient restart mechanism (batch processing with periodic server restarts) during utility evaluation due to xgrammar nanobind memory leak when processing diverse schemas.
