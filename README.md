# Selective DeLex-JSON: Control-Plane Jailbreak Defense for Structured-Output LLM APIs

Inference-only project investigating defenses against control-plane jailbreaks (e.g., EnumAttack) that exploit JSON schema constrained decoding in LLM APIs.

## Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Key packages (pre-installed):
# torch 2.9.1+cu129, vllm 0.12.1.dev, flash_attn 2.8.1
# transformers, datasets, accelerate, pydantic, jsonschema
# outlines, openai, numpy, pandas, scipy, matplotlib, seaborn
# huggingface_hub, tqdm, fire
```

Python 3.12.12. CUDA 12.9. No local GPU -- use TrainService/DeploymentService for all GPU tasks.

## Serving Models with vLLM

vLLM 0.12.x uses the OpenAI-compatible `response_format` API for structured output (NOT `guided_json` in `extra_body`):

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8001/v1", api_key="dummy")

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "..."}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "my_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"field": {"type": "string"}},
                "required": ["field"],
                "additionalProperties": False
            }
        }
    },
    max_tokens=256,
    temperature=0.6
)
```

Server startup script example (`scripts/smoke_test_server.sh`):
```bash
source .venv/bin/activate
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8001 --max-model-len 3072 --gpu-memory-utilization 0.9
```

## Models (in HF cache)

| Model | HuggingFace ID | Purpose |
|-------|---------------|---------|
| Llama-3.1-8B-Instruct | `meta-llama/Llama-3.1-8B-Instruct` | Primary target model |
| Qwen2.5-7B-Instruct | `Qwen/Qwen2.5-7B-Instruct` | Secondary target model |
| HarmBench Classifier | `cais/HarmBench-Llama-2-13b-cls` | Safety evaluation (ASR) |
| Llama Guard 3 8B | `meta-llama/Llama-Guard-3-8B` | Input guard defense |

## Project Structure

```
configs/          # Experiment configuration files
attacks/          # Attack implementations (EnumAttack)
defenses/         # Defense implementations
  delex.py        #   Selective DeLex-JSON schema transformer
  input_guard.py  #   Input guard baseline (Llama Guard)
  reject_only.py  #   Reject-only schema audit baseline
  escape_hatch.py #   Escape-hatch wrapper baseline
evaluation/       # Evaluation scripts
  safety_eval.py  #   ASR via HarmBench classifier
  strongreject_eval.py  # StrongREJECT scoring
  utility_eval.py #   JSONSchemaBench + IFEval utility
  field_extractor.py    # Extract free-text from JSON outputs
schemas/          # Schema utilities and test schemas
scripts/          # Shell scripts for experiments
data/             # Downloaded datasets (IFEval, etc.)
external/         # Cloned repos (HarmBench, JSONSchemaBench, StrongREJECT)
outputs/          # Raw model outputs
results/          # Aggregated evaluation results
```

## External Repositories

Cloned into `external/`:
- `external/HarmBench` -- HarmBench classifier eval protocol and harmful behavior prompts
- `external/jsonschemabench` -- JSON schema benchmark dataset and evaluation harness
- `external/strongreject` -- StrongREJECT safety scoring rubric

## Datasets

- **IFEval**: Downloaded to `data/ifeval/` (541 examples)
- **HarmBench prompts**: `data/harmbench_prompts.json` (159 standard behaviors from test split)
- **StrongREJECT prompts**: `data/strongreject_prompts.json` (313 prompts, 6 categories)
- **JSONSchemaBench**: Available in `external/jsonschemabench/`

## Implemented Attacks

- **EnumAttack** (`attacks/enum_attack.py`): Embeds harmful question + affirmative prefix as forced enum values in JSON schema. Benign user prompt bypasses prompt auditing.

## Evaluation Pipeline

- `evaluation/field_extractor.py`: Extracts free-text (non-forced) fields from JSON model outputs
- `evaluation/safety_eval.py`: ASR via HarmBench classifier (completions API, Llama-2 format)
- `evaluation/strongreject_eval.py`: StrongREJECT rubric scoring via LLM-as-judge (LEMMA MaaS API)
- HarmBench classifier uses `max_model_len=2048` (model limit)

## Key Scripts

- `scripts/run_enum_attack.py`: Run EnumAttack against a vLLM endpoint
- `scripts/run_enum_attack_full.sh`: Full pipeline (serve model + run attack on both datasets)
- `scripts/run_harmbench_eval.py`: Run HarmBench classifier on outputs
- `scripts/run_safety_eval.sh`: Full HarmBench eval pipeline (serve classifier + evaluate)
- `scripts/run_strongreject_eval.py`: Run StrongREJECT rubric scoring via API
- `scripts/run_input_guard_experiment.py`: Run EnumAttack with input guard defense
- `scripts/run_input_guard_fpr.py`: Measure false positive rate on benign schemas
- `scripts/run_input_guard_eval.py`: HarmBench eval with guard-refused handling
- `scripts/run_input_guard_strongreject.py`: StrongREJECT eval with guard-refused handling
- `scripts/run_input_guard_full.sh`: Full input guard pipeline (4 GPUs)
- `scripts/run_reject_only_experiment.py`: Run EnumAttack with reject-only schema audit
- `scripts/run_reject_only_fpr.py`: Measure benign rejection rate on JSONSchemaBench (CPU only)
- `scripts/run_reject_only_eval.py`: HarmBench eval with schema-rejected handling
- `scripts/run_reject_only_strongreject.py`: StrongREJECT eval with schema-rejected handling
- `scripts/run_reject_only_full.sh`: Full reject-only pipeline
- `scripts/run_escape_hatch_experiment.py`: Run EnumAttack with escape-hatch defense
- `scripts/run_escape_hatch_utility.py`: Measure benign refusal/validity on JSONSchemaBench
- `scripts/run_escape_hatch_eval.py`: HarmBench eval with model-refused handling
- `scripts/run_escape_hatch_strongreject.py`: StrongREJECT eval with model-refused handling
- `scripts/run_escape_hatch_full.sh`: Full escape-hatch pipeline

- `scripts/run_qwen25_safety.sh`: Full Qwen2.5 safety pipeline (no-defense + DeLex + eval)
- `scripts/run_qwen25_utility.sh`: Qwen2.5 utility pipeline (resilient restart)
- `scripts/aggregate_qwen25_results.py`: Aggregate Qwen2.5 results + cross-model comparison

## Completed Experiments

### EnumAttack (No Defense) on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench ASR | 22.0% (35/159) |
| StrongREJECT ASR (cls) | 15.3% (48/313) |
| StrongREJECT Score | 0.103 |

Outputs: `outputs/no_defense_llama31/`, Results: `results/no_defense_llama31.json`

### Input Guard Defense (Llama Guard 3) on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench Guard Rejection Rate | 88.7% (141/159) |
| HarmBench ASR | 3.8% (6/159) |
| StrongREJECT Guard Rejection Rate | 91.7% (287/313) |
| StrongREJECT ASR (cls) | 2.9% (9/313) |
| StrongREJECT Score | 0.024 |
| False Positive Rate (benign schemas) | 0.0% (0/200) |

Outputs: `outputs/input_guard_llama31/`, Results: `results/input_guard_llama31.json`

### Reject-Only Schema Audit Defense on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench Schema Rejection Rate | 100.0% (159/159) |
| HarmBench ASR | 0.0% (0/159) |
| StrongREJECT Schema Rejection Rate | 100.0% (313/313) |
| StrongREJECT ASR (cls) | 0.0% (0/313) |
| StrongREJECT Score | 0.000 |
| Benign Schema Rejection Rate (JSONSchemaBench) | 4.4% (387/8825) |

Per-subset benign FPR: Glaiveai2K 0.0%, Github_easy 1.4%, Github_medium 3.4%, Github_hard 10.8%, Kubernetes 12.2%, Snowplow 0.7%, JsonSchemaStore 5.1%. Dominant trigger: `length>20`.

Outputs: `outputs/reject_only_llama31/`, Results: `results/reject_only_llama31.json`

### Escape-Hatch Defense on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench Model Refusal Rate | 0.0% (0/159) |
| HarmBench ASR | 22.0% (35/159) |
| StrongREJECT Model Refusal Rate | 0.0% (0/313) |
| StrongREJECT ASR (cls) | 15.3% (48/313) |
| StrongREJECT Score | 0.094 |
| Benign False Refusal Rate (JSONSchemaBench) | 12.7% (408/3218) |
| JSON Validity (non-refusal) | 86.0% |
| Schema Compliance (non-refusal) | 84.5% |

Defense is completely ineffective: 0% model refusal rate, ASR identical to no-defense. Significant utility degradation (12.7% false refusals on benign schemas).

Outputs: `outputs/escape_hatch_llama31/`, Results: `results/escape_hatch_llama31.json`

### Selective DeLex-JSON Defense on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench ASR | 0.0% (0/159) |
| StrongREJECT ASR (cls) | 2.6% (8/313) |
| StrongREJECT Score | 0.0016 |
| Attack Schema Modification Rate | 100.0% |
| Benign Schema Modification Rate (JSONSchemaBench) | 1.1% (100/8825) |
| Utility Delta (validity, paired) | -0.38pp |
| Utility Delta (compliance, paired) | -0.70pp |
| IFEval JSON Degradation | 0.0% |

DeLex-JSON achieves 0.0% HarmBench ASR (from 22.0%), matching reject-only safety. Utility impact is minimal (-0.38pp validity, -0.70pp compliance via paired comparison). Benign FPR is 1.1%, well under the 2% target, using conjunction-based suspicion (>= 2 corroborating criteria required).

Outputs: `outputs/delex_v2_llama31/`, Results: `results/delex_v2_llama31_harmbench_asr.json`

### Cross-Defense Comparison (Llama-3.1-8B-Instruct)

| Defense | HarmBench ASR | StrongREJECT ASR | StrongREJECT Score | Benign FPR |
|---------|--------------|-------------------|-------------------|------------|
| No Defense | 22.0% | 15.3% | 0.103 | N/A |
| Input Guard | 3.8% | 2.9% | 0.024 | 0.0% |
| Reject-Only | 0.0% | 0.0% | 0.000 | 0.05% |
| Escape-Hatch | 22.0% | 15.3% | 0.094 | 12.7% |
| **DeLex-JSON** | **0.0%** | **2.6%** | **0.002** | **1.1%** |

### Selective DeLex-JSON on Qwen2.5-7B-Instruct (Cross-Model)

| Metric | No Defense | DeLex-JSON | Reduction |
|--------|-----------|------------|-----------|
| HarmBench ASR | 10.7% (17/159) | 0.0% (0/159) | -10.7pp (100%) |
| StrongREJECT ASR (cls) | 4.5% (14/313) | 2.6% (8/313) | -1.9pp (42.9%) |
| StrongREJECT Score | 0.045 | 0.0016 | -0.044 (96.5%) |
| Utility: JSON Validity (Glaiveai2K) | 86.5% | 86.5% | 0.0% |
| Utility: Schema Compliance (Glaiveai2K) | 83.9% | 83.9% | 0.0% |

DeLex-JSON achieves 0.0% HarmBench ASR on Qwen2.5 (from 10.7%), confirming model-agnostic effectiveness. Utility impact is zero on Glaiveai2K (0% benign schema modification rate).

Outputs: `outputs/no_defense_qwen25/`, `outputs/delex_qwen25/`
Results: `results/no_defense_qwen25.json`, `results/delex_qwen25.json`, `results/delex_utility_qwen25.json`, `results/cross_model_comparison.json`

### Cross-Model Comparison

| Model | No-Def HB ASR | DeLex HB ASR | No-Def SR Score | DeLex SR Score |
|-------|--------------|-------------|----------------|---------------|
| Llama-3.1-8B-Instruct | 22.0% | 0.0% | 0.103 | 0.0016 |
| Qwen2.5-7B-Instruct | 10.7% | 0.0% | 0.045 | 0.0016 |

### Ablation Study: DeLex-JSON Component Contributions (Llama-3.1-8B-Instruct)

| Variant | HarmBench ASR | Benign Mod Rate | JSON Validity | Schema Compliance |
|---------|:---:|:---:|:---:|:---:|
| No Defense | 22.0% | 0.0% | 95.9% | 94.1% |
| **Full DeLex-JSON** | **0.0%** | **1.1%** | **95.4%** | **93.1%** |
| Strip-Only | 22.0% | 0.0% | 95.2% | 93.4% |
| Delex-All | 0.0% | 35.5% | 94.5% | 92.1% |
| Heuristic-Only | 0.0% | 1.1% | 95.4% | 93.1% |

Key findings: (1) Strip-Only has same ASR as no defense, proving forced literals are the attack vector. (2) Delex-All achieves 0% ASR but 35.5% benign modification rate (vs 1.1%), confirming selective delexicalization preserves utility. (3) Heuristic-Only is identical to full method, confirming rule-based heuristic suffices.
Results: `results/ablation_summary.json`, `results/ablation_utility.json`, `EXPERIMENT_RESULTS/ablation_study/`
