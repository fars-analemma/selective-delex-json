# Reject-Only Schema Audit Defense Baseline

## Experiment Overview

Evaluates a reject-only schema filtering defense that inspects JSON schemas for suspicious forced literals (enum/const values) and rejects the entire schema if any are found. Unlike the proposed Selective DeLex-JSON which replaces suspicious literals with placeholders, this baseline simply refuses to process schemas containing suspicious content.

**Defense mechanism**: Parse schema, extract all forced string literals (single-value enum, const), apply suspicion function. If ANY literal is flagged, reject the entire schema.

**Suspicion criteria** (same as Selective DeLex-JSON for fair comparison):
- Length > 20 characters
- Contains whitespace (spaces/newlines/tabs)
- Matches instruction-like regex: `(?i)^sure[,.]`, `(?i)step\s+\d`, `(?i)here's\s+how`, `(?i)^(make|create|write|explain|describe|tell)\b`

## Setup

- **Target model**: meta-llama/Llama-3.1-8B-Instruct
- **Attack**: EnumAttack (embeds harmful question + affirmative prefix as forced enum values)
- **Safety benchmarks**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Utility benchmark**: JSONSchemaBench (7 subsets, 8,825 schemas total)
- **Evaluation**: HarmBench classifier ASR, StrongREJECT rubric scoring, benign rejection rate

## Key Results

### Safety (Attack Rejection)

| Metric | Value |
|--------|-------|
| HarmBench Schema Rejection Rate | **100.0%** (159/159) |
| HarmBench ASR | **0.0%** (0/159) |
| StrongREJECT Schema Rejection Rate | **100.0%** (313/313) |
| StrongREJECT ASR (cls) | **0.0%** (0/313) |
| StrongREJECT Score | **0.000** |

All EnumAttack schemas contain forced literals that exceed the length threshold and contain whitespace, triggering 100% rejection. No GPU-based constrained decoding was needed since all schemas were rejected before reaching the model.

### Utility (Benign Schema Rejection / False Positive Rate)

| JSONSchemaBench Subset | Total | Rejected | FPR | Primary Trigger |
|------------------------|-------|----------|-----|-----------------|
| Glaiveai2K | 1,707 | 0 | 0.0% | -- |
| Github_easy | 1,943 | 28 | 1.4% | length>20 |
| Github_medium | 1,976 | 67 | 3.4% | length>20 |
| Github_hard | 1,240 | 134 | 10.8% | length>20 |
| Kubernetes | 1,064 | 130 | 12.2% | length>20 |
| Snowplow | 403 | 3 | 0.7% | length>20 |
| JsonSchemaStore | 492 | 25 | 5.1% | length>20 |
| **Overall** | **8,825** | **387** | **4.4%** | length>20 |

Rejection trigger breakdown (across all rejected schemas):
- `length>20`: 2,243 triggers (dominant)
- `whitespace`: 25 triggers
- `regex:(?i)^(make|create|write|explain|describe|tell)\b`: 1 trigger

## Key Observations

1. **Perfect safety**: The reject-only defense achieves 0% ASR on both benchmarks -- complete protection against EnumAttack. This is because every EnumAttack schema embeds long (>20 char) forced strings with whitespace, easily caught by the suspicion heuristic.

2. **Non-trivial utility cost**: 4.4% of benign schemas are incorrectly rejected. The cost is concentrated in complex schemas (Kubernetes: 12.2%, Github_hard: 10.8%) that legitimately use long enum/const values (e.g., error messages, documentation strings, Kubernetes API descriptions).

3. **Safety-utility tradeoff**: The reject-only approach is an extreme point on the tradeoff curve: perfect safety but with collateral damage to benign schemas. This motivates the Selective DeLex-JSON approach which can achieve similar safety while preserving benign schemas (by replacing suspicious literals with placeholders rather than rejecting the entire schema).

4. **Length is the dominant trigger**: The `length>20` check is responsible for nearly all false positives. Many real-world schemas contain enum values or const strings longer than 20 characters for legitimate purposes (e.g., status codes, description fields, URIs).
