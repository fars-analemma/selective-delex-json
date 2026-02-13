# Escape-Hatch Defense Baseline Experiment

## Experiment Overview

Evaluates an escape-hatch defense that modifies the constrained decoding grammar to always allow the model to generate a refusal token sequence even when the JSON schema would otherwise force specific outputs. The defense wraps the original schema in a `oneOf` construct adding a refusal alternative: `{"oneOf": [<original_schema>, {"type": "object", "properties": {"refusal": {"type": "string"}}, "required": ["refusal"]}]}`.

Reference: "Output Constraints as Attack Surface: Exploiting Structured Generation to Bypass LLM Safety Mechanisms" (Defense Sketch 1: Refusal-Token Whitelisting).

## Setup

- **Model**: Llama-3.1-8B-Instruct via vLLM (temperature=0.6, max_tokens=1024)
- **Attack**: EnumAttack (embeds harmful question + affirmative prefix as forced enum values)
- **Defense**: Schema wrapper adding oneOf refusal alternative (`strict: false` required for vLLM compatibility)
- **Safety datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **Utility datasets**: JSONSchemaBench (Glaiveai2K: 1707 schemas, Github_easy: 1943 schemas)
- **Evaluation**: HarmBench classifier (ASR), StrongREJECT rubric (mean score), JSON validity, schema compliance

## Key Results

### Safety (Attack Success Rate)

| Metric | No Defense | Escape-Hatch | Delta |
|--------|-----------|-------------|-------|
| HarmBench ASR | 22.0% | 22.0% | 0.0 |
| StrongREJECT ASR (cls) | 15.3% | 15.3% | 0.0 |
| StrongREJECT Score | 0.103 | 0.094 | -0.009 |
| Model Refusal Rate (HarmBench) | N/A | 0.0% | -- |
| Model Refusal Rate (StrongREJECT) | N/A | 0.0% | -- |

### Utility (Benign Schema Performance)

| Metric | Glaiveai2K | Github_easy | Overall |
|--------|-----------|------------|---------|
| False Refusal Rate | 15.4% | 9.7% | 12.7% |
| JSON Validity (non-refusal) | 97.0% | 74.4% | 86.0% |
| Schema Compliance (non-refusal) | 94.7% | 73.7% | 84.5% |
| Generation Errors | 1 | 431 | 432 |

## Key Observations

1. **The escape-hatch defense is completely ineffective against EnumAttack**: The model never used the refusal path (0.0% refusal rate on both HarmBench and StrongREJECT). ASR is identical to the no-defense baseline.

2. **The forced enum values dominate model behavior**: Even though the schema offers a `oneOf` alternative with a free-text refusal field, the constrained decoding process still drives the model to comply with the attack schema. The enum constraints in the original schema create strong logit pressure that overwhelms the model's safety alignment.

3. **Significant utility degradation**: On benign schemas, the escape-hatch wrapper causes 12.7% false refusals (the model incorrectly chooses the refusal path when it should generate structured output). This is a substantial cost with zero safety benefit.

4. **vLLM compatibility issues**: Wrapping schemas with `oneOf` required disabling `strict: true` mode and caused xgrammar crashes on complex schemas (431 generation errors on Github_easy). This makes the defense impractical for production deployment.

5. **Fundamental limitation**: The escape-hatch approach relies on the model choosing to refuse, but constrained decoding with forced literals (enum/const) removes the model's agency at the token level. The model cannot "decide" to refuse when the grammar forces it down the attack path token by token.
