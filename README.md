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

## Completed Experiments

### EnumAttack (No Defense) on Llama-3.1-8B-Instruct

| Metric | Value |
|--------|-------|
| HarmBench ASR | 22.0% (35/159) |
| StrongREJECT ASR (cls) | 15.3% (48/313) |
| StrongREJECT Score | 0.103 |

Outputs: `outputs/no_defense_llama31/`, Results: `results/no_defense_llama31.json`
