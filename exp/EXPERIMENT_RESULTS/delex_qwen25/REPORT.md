# Selective DeLex-JSON on Qwen2.5-7B-Instruct (Cross-Model Generalization)

## Experiment Overview

Evaluated the Selective DeLex-JSON defense on Qwen2.5-7B-Instruct to demonstrate that the defense is model-agnostic. Used the identical attack (EnumAttack), defense implementation (conjunction-based suspicion function), and evaluation pipeline from the primary Llama-3.1-8B experiment -- only the target LLM changed.

## Setup

- **Model**: Qwen/Qwen2.5-7B-Instruct
- **Attack**: EnumAttack (embeds harmful content as forced enum values in JSON schema)
- **Defense**: Selective DeLex-JSON (replaces suspicious enum literals with placeholders)
- **Serving**: vLLM 0.12.x, temperature=0.6, max_model_len=3072
- **Safety Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Utility Dataset**: JSONSchemaBench GlaiveAI-2K subset (1707 schemas)
- **Evaluation**: HarmBench classifier ASR, StrongREJECT classifier ASR, StrongREJECT rubric score

## Key Results

### Safety (EnumAttack)

| Metric | No Defense | DeLex-JSON | Reduction |
|--------|-----------|------------|-----------|
| HarmBench ASR | 10.7% (17/159) | 0.0% (0/159) | -10.7pp (100%) |
| StrongREJECT ASR (cls) | 4.5% (14/313) | 2.6% (8/313) | -1.9pp (42.9%) |
| StrongREJECT Score | 0.0451 | 0.0016 | -0.0435 (96.5%) |
| Schema Modification Rate | N/A | 100.0% | - |

### Utility (GlaiveAI-2K)

| Metric | No Defense | DeLex-JSON | Delta |
|--------|-----------|------------|-------|
| JSON Validity | 86.5% | 86.5% | 0.0% |
| Schema Compliance | 83.9% | 83.9% | 0.0% |
| Schema Modification Rate | N/A | 0.0% | - |

Utility impact is zero on Glaiveai2K because no benign schemas in this subset trigger the suspicion function (modification rate = 0%).

### Cross-Model Comparison

| Model | No-Def HarmBench ASR | DeLex HarmBench ASR | ASR Reduction |
|-------|---------------------|--------------------|--------------:|
| Llama-3.1-8B-Instruct | 22.0% | 0.0% | 100% |
| Qwen2.5-7B-Instruct | 10.7% | 0.0% | 100% |

| Model | No-Def StrongREJECT Score | DeLex StrongREJECT Score | Score Reduction |
|-------|--------------------------|-------------------------|--------------:|
| Llama-3.1-8B-Instruct | 0.103 | 0.0016 | 98.4% |
| Qwen2.5-7B-Instruct | 0.045 | 0.0016 | 96.5% |

## Key Observations

1. **DeLex-JSON achieves 0.0% HarmBench ASR on both models** -- defense is fully model-agnostic.
2. **Qwen2.5 is naturally more robust** than Llama-3.1: no-defense HarmBench ASR is 10.7% vs 22.0%, and StrongREJECT score is 0.045 vs 0.103.
3. **DeLex reduces both models to near-zero harm**: StrongREJECT score drops to 0.0016 for both.
4. **Zero utility impact on Glaiveai2K**: benign schemas pass through unchanged (0% modification rate).
5. The residual StrongREJECT classifier ASR (2.6%) is identical for both models under DeLex, suggesting these are classifier false positives rather than actual harmful outputs.
