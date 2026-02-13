# Input Guard Baseline: Llama Guard 3 against EnumAttack

## Experiment Overview

Evaluates input-side auditing as a defense against EnumAttack. Uses Llama Guard 3 (8B) to classify the combined (user prompt + serialized JSON schema) before allowing constrained decoding on Llama-3.1-8B-Instruct. If the guard flags the input as unsafe, the request is rejected outright.

## Setup

- **Target Model**: meta-llama/Llama-3.1-8B-Instruct (vLLM, temperature=0.6, max_model_len=3072)
- **Guard Model**: meta-llama/Llama-Guard-3-8B (vLLM, temperature=0.0)
- **Attack**: EnumAttack (embeds harmful question + affirmative prefix as enum values)
- **Datasets**: HarmBench (159 prompts), StrongREJECT (313 prompts)
- **False Positive Evaluation**: 200 randomly sampled benign schemas from JSONSchemaBench (seed=42)
- **Infrastructure**: 4 GPUs via TrainService (1 for guard, 1 for target, 1 for HarmBench classifier, 1 spare)

## Key Results

| Metric | HarmBench | StrongREJECT |
|--------|-----------|--------------|
| Guard Rejection Rate | 88.7% (141/159) | 91.7% (287/313) |
| ASR (HarmBench cls) | 3.8% (6/159) | 2.9% (9/313) |
| ASR (StrongREJECT rubric) | -- | 3.2% |
| StrongREJECT Score | -- | 0.024 |
| False Positive Rate | 0.0% (0/200) | -- |

### Comparison with No Defense Baseline

| Metric | No Defense | Input Guard | Reduction |
|--------|-----------|-------------|-----------|
| HarmBench ASR | 22.0% | 3.8% | -18.2pp |
| StrongREJECT ASR (cls) | 15.3% | 2.9% | -12.4pp |
| StrongREJECT Score | 0.103 | 0.024 | -0.079 |

## Key Observations

1. **High detection rate**: Llama Guard catches ~90% of EnumAttack schemas by detecting the harmful content serialized in enum fields. The guard correctly identifies that the schema contains dangerous instructions even though the user prompt itself is benign ("Please fill in the following JSON fields.").

2. **Residual ASR is low but non-zero**: ~3-4% of attacks still pass through. These tend to be in categories like "misinformation/disinformation" where the harmful content may be more ambiguous or where Llama Guard's safety taxonomy has less coverage.

3. **Zero false positives on benign schemas**: All 200 sampled JSONSchemaBench schemas were correctly classified as safe. This suggests the guard is well-calibrated for typical API usage -- benign schemas with technical enum values are not flagged.

4. **Validates the CDA paper's hypothesis**: The input guard can detect most EnumAttack payloads because the harmful content is explicitly present in the schema text. However, this defense has a fundamental limitation: it requires the guard model to detect harm in structured/technical contexts, and more sophisticated obfuscation could evade it.

5. **Per-category analysis**: Categories like chemical_biological (100% rejection), harassment_bullying (100% rejection), and cybercrime_intrusion (97% rejection) are nearly fully caught. Misinformation (63% rejection) and harmful (76% rejection) have lower catch rates, suggesting these categories contain more subtle or ambiguous harmful content.
