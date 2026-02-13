## Experiments

### Experimental Setup

**Base Models:**

| Model | Size | Download Link | Notes |
|-------|------|---------------|-------|
| Llama-3.1-Instruct | 8B | https://huggingface.co/meta-llama | **Primary model** (pre-registered) |
| Qwen2.5-Instruct | 7B | https://huggingface.co/Qwen | Secondary model for generalization |

**Training Data (if applicable):**

No training data needed - inference only.

**Other Resources (if applicable):**
- Safety classifier / guard: Llama Guard or HarmBench classifier (open weights).
- Constrained decoding library: Outlines or equivalent grammar-guided decoding stack (fixed version).

**Resource Estimate**:
- **Compute budget**: Inference-heavy. Rough order: O(#prompts × #conditions × #models). Target ≤100 A100 GPU-hours total (including guard-model inference). Hard cap 768 GPU-hours.
- **GPU memory**: 8B-class models + constrained decoding should fit on a single A100-80GB; optional tensor parallel if needed.
- **API usage**: None required for primary metrics (ASR via HarmBench classifier). Optional: GPT-based StrongREJECT scoring if available.

**Infrastructure constraints** (proposals requiring these are infeasible):
- Search engine APIs (Google, Bing) — NOT available
- Web browsers / desktop GUIs / mobile environments — NOT available
- Complex game engines or heavy simulation environments — NOT available

### Benchmarks and Metrics

| Benchmark | Description | Metrics | Split | Download Link | Evaluation Script |
|-----------|-------------|---------|-------|---------------|-------------------|
| HarmBench | Harmful prompts for automated red-teaming | ASR (unsafe rate) | test | https://arxiv.org/abs/2402.04249 | HarmBench official eval (classifier) |
| StrongREJECT | Harmful prompt set + scoring | ASR + (optional) StrongREJECT score | test | https://openreview.net/forum?id=al303JJkGO | StrongREJECT eval; if judge refuses, use extracted-field scoring |
| JSONSchemaBench | Real-world JSON schema constrained generation | JSON validity, schema compliance, task accuracy (where applicable), schema-modification rate | provided | https://github.com/guidance-ai/jsonschemabench | JSONSchemaBench repo |
| IFEval (JSON subset) | Instruction-following under JSON constraints | JSON correctness | test | https://arxiv.org/abs/2311.07911 | IFEval scripts |

**Evaluation Scripts:**
- For attack ASR: follow HarmBench classifier protocol.
- For safety evaluation: **extract only model-generated free-text fields** (e.g., `answer`) before scoring; mask forced literals.
- For utility: run JSONSchemaBench harness and report (i) validity, (ii) compliance, (iii) any task accuracy, and (iv) delex modification rate.

### Main Results

#### Comparability Rules (CRITICAL)

All comparisons are within the same model + decoding stack; the only change is schema preprocessing/defense.

#### Results Table

| Method | Base Model | Benchmark | Metric 1 | Metric 2 | Source | Notes |
|--------|------------|-----------|----------|----------|--------|-------|
| EnumAttack (reported) | Llama-3.1-8B | AdvBench (520) | ASR **99.2%** | SR **95.1%** | [CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt) (Table 3) | Uses vLLM structured output; evidence of severity |
| EnumAttack (reported) | Phi-3.5-MoE | HarmBench (100) | ASR **98.0%** | SR **74.6%** | [CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt) (Table 4) | Cross-benchmark evidence; open-weight “best aligned” model |
| Direct prompting baseline (reported) | Phi-3.5-MoE | HarmBench (100) | ASR **31.0%** | SR **27.3%** | [CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt) (Table 4) | Shows large delta vs CDA |
| JSON steering (reported) | Llama-3-8B-Instruct | HarmBench (400) | ASR **2.00%→20.00%** | - | [Steering Externalities Table 10](./references/Steering-Externalities-Benign-Activation-Steering-Unintentionally-Increases-Jailbreak-Risk-for-Large-Language-Models/sections/K.%20Numerical%20value%20of%20Intrinsic%20and%20Synergistic%20Vulnerabilities.md) | Different mechanism; motivation for structured-output safety |
| No defense | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | **TBD** | - | Needs re-run under our decoding stack |
| Input guard (prompt+schema) | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | **TBD** | - | Needs re-run |
| Reject-only schema audit | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | benign reject% **TBD** | - | Needs re-run |
| Escape-hatch wrapper | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | **TBD** | - | Needs re-run |
| **Selective DeLex-JSON (Ours)** | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | benign modify% **TBD** | - | To be verified |
| **Ours + escape hatch** | Llama-3.1-8B | HarmBench/StrongREJECT | **TBD** | **TBD** | - | Optional |
| **Selective DeLex-JSON (Ours)** | Llama-3.1-8B | JSONSchemaBench | JSON validity **TBD** | compliance/acc **TBD** | - | Utility evaluation |

### Ablation Studies

| Variant | What’s changed | Expected finding |
|---------|----------------|------------------|
| Ours (full) | Strip free-text + selective enum/const delex | Best ASR–utility tradeoff |
| Strip-only | Remove schema free-text, no delex | Small improvement if payload in free-text matters; likely insufficient |
| Delex-all | Replace all enum/const strings with placeholders | More secure but harms semantic-enum utility |
| No guard model | Heuristic-only suspicion test | Similar security if heuristics capture the key mechanism |
| Chunked-payload probe | Attack with many short enum values | Identifies boundary condition / potential bypass |

### Analysis (Optional)

- Measure correlation between attack success and presence/length of forced literal strings.
- Report distribution of benign schema modifications (what got delexed and why).

---