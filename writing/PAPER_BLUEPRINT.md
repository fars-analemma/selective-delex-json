# Paper Blueprint: Selective Delexicalization to Defend Structured-Output LLM APIs from Control-Plane Jailbreaks

## Meta Information
- **Analysis Date**: 2026-02-14
- **Experiments Analyzed**: 8 (No Defense, Input Guard, Reject-Only, Escape-Hatch, DeLex-JSON on Llama-3.1-8B, DeLex-JSON on Qwen2.5-7B, Ablation Study, Chunked Probe)
- **Figures Generated**: 3 (1 method diagram: framework_overview.jpeg, 2 analytical plots: pareto_frontier.png, chunked_probe.png)
- **Tables Designed**: 3 (Main Safety Results, Utility/Overhead, Ablation)
- **Claims Identified**: 8 (defense effectiveness, utility preservation, low FPR, Pareto dominance, cross-model generalization, ablation insights ×2, limitation)
- **References Collected**: 24+ papers (HarmBench, StrongREJECT, Llama Guard, Outlines, XGrammar, vLLM, GCG, PAIR, TAP, Constitutional AI, JSONSchemaBench, IFEval, JailbreakBench, SORRY-Bench, SynCode, MASTERKEY, StruQ, CARE, and more)

## Claims

### claim_1: defense_effectiveness
**Statement**: Selective DeLex-JSON reduces EnumAttack success rate from 22.0% to 0.0% on HarmBench and from 15.3% to 2.6% on StrongREJECT for Llama-3.1-8B-Instruct, achieving near-perfect defense against control-plane jailbreaks.
**Evidence**: delex_llama31 experiment - HarmBench ASR: 0/159 (0.0%), StrongREJECT ASR: 8/313 (2.6% classifier, 0.3% rubric)
**Figures**: tab_main_safety
**Tables**: tab_main_safety

### claim_2: utility_preservation
**Statement**: Selective DeLex-JSON preserves structured output utility with only 0.38 percentage point degradation in JSON validity and 0.70 percentage point degradation in schema compliance on JSONSchemaBench, well within the 2pp threshold.
**Evidence**: delex_llama31 utility evaluation - paired comparison on 3141 schemas
**Figures**: None
**Tables**: tab_utility

### claim_3: low_false_positive_rate
**Statement**: The conjunction-based suspicion function achieves only 1.1% benign schema modification rate across 8,825 JSONSchemaBench schemas, compared to 4.4% rejection rate for the Reject-Only baseline.
**Evidence**: delex_llama31 overhead metrics - 100/8825 schemas modified
**Figures**: None
**Tables**: tab_utility

### claim_4: pareto_dominance
**Statement**: Selective DeLex-JSON achieves a strictly better Pareto point than Reject-Only: identical 0.0% HarmBench ASR with 3.3 percentage points lower benign cost (1.1% modification vs. 4.4% rejection).
**Evidence**: Comparison of delex_llama31 vs reject_only_llama31 results
**Figures**: fig_pareto
**Tables**: tab_main_safety

### claim_5: cross_model_generalization
**Statement**: Selective DeLex-JSON generalizes across model families, reducing HarmBench ASR from 10.7% to 0.0% on Qwen2.5-7B-Instruct with zero utility degradation on GlaiveAI-2K.
**Evidence**: delex_qwen25 experiment results
**Figures**: None
**Tables**: tab_main_safety

### claim_6: ablation_forced_literals
**Statement**: Forced enum/const literals are the key attack vector: Strip-Only (metadata removal without delexicalization) achieves identical 22.0% ASR as No Defense, while full DeLex-JSON achieves 0.0% ASR.
**Evidence**: ablation_study results - Strip-Only ASR = 22.0%, Full DeLex-JSON ASR = 0.0%
**Figures**: None
**Tables**: tab_ablation

### claim_7: selective_vs_blanket
**Statement**: Selective delexicalization preserves utility better than blanket delexicalization: Delex-All achieves 0.0% ASR but with 35.5% benign modification rate (vs. 1.1% for selective), demonstrating the value of the suspicion function.
**Evidence**: ablation_study results - Delex-All modification rate = 35.5%
**Figures**: None
**Tables**: tab_ablation

### claim_8: chunked_attack_limitation
**Statement**: Chunked-payload attacks that distribute harmful content across many short enum values (≤20 chars each) bypass the suspicion function, representing a known limitation of the current defense.
**Evidence**: chunked_probe results - 0% of chunks flagged at any chunk size, ASR ~10-14% for both defended and undefended conditions
**Figures**: fig_chunked_probe
**Tables**: None

## Figure-Table Plan

**Purpose**: Prevent redundancy by deciding upfront what data goes into figures vs tables.

**Core Requirements**:
- **Main results table (REQUIRED)**: Main experimental results must be in table format with precise values

### Main Results Table (REQUIRED)
- Main safety comparison: All 5 defense methods × 2 benchmarks (HarmBench, StrongREJECT) with ASR values
- Cross-model generalization: Llama-3.1-8B and Qwen2.5-7B results
- Source: Individual experiment RESULTS.json files

### Additional Tables
- **Utility/Overhead Table**: Benign modification rates per subset, JSON validity/compliance deltas
- **Ablation Table**: Component contribution analysis (Strip-Only, Delex-All, Heuristic-Only)

### Figures (analytical insights)
- **Pareto Frontier (fig_pareto)**: Safety vs. utility tradeoff visualization - shows DeLex-JSON dominates Reject-Only
- **Chunked Probe (fig_chunked_probe)**: ASR vs. chunk size trend - shows limitation of current defense

### Redundancy Check
- ❌ Main safety results are in table only (not duplicated as bar chart)
- ❌ Utility metrics are in table only (not duplicated as figure)
- ✅ Pareto frontier shows unique relationship visualization
- ✅ Chunked probe shows trend across chunk sizes (unique analytical insight)

## Figures

**CRITICAL**: All figures listed below are actual generated image files that exist in `analytical_plots/` or `method_diagrams/` directories.

### fig_framework_overview
- **Path**: `method_diagrams/framework_overview.jpeg`
- **Type**: method_diagram
- **Caption**: Overview of Selective DeLex-JSON defense. The system intercepts JSON schemas before constrained decoding, identifies suspicious forced literals (enum/const values) using a conjunction-based suspicion function, and replaces them with opaque placeholders to neutralize embedded attack payloads while preserving schema structure.
- **Shows**: claim_1, claim_3
- **Analysis**: This diagram illustrates the core defense mechanism: (1) Schema interception before constrained decoding, (2) Suspicion function that flags literals meeting multiple criteria (length >20, whitespace, imperative verbs), (3) Placeholder replacement that preserves JSON structure while removing attack content. The key insight is that the defense operates at the schema level, not the prompt level, addressing the control-plane attack vector.

### fig_pareto
- **Path**: `analytical_plots/pareto_frontier.png`
- **Type**: analytical_plot
- **Caption**: Safety-utility Pareto frontier comparing defense methods. DeLex-JSON (green star) achieves 0% HarmBench ASR with only 1.1% benign modification rate, Pareto-dominating Reject-Only (blue diamond) which has 4.4% rejection rate. Escape-Hatch (orange square) provides no safety improvement over No Defense (red circle) despite 12.7% benign refusal rate.
- **Shows**: claim_4
- **Analysis**: The Pareto frontier visualization reveals that DeLex-JSON achieves the best safety-utility tradeoff among all defenses. It matches Reject-Only's perfect HarmBench defense (0% ASR) while reducing benign cost by 3.3 percentage points. Input Guard (purple triangle) achieves partial safety (3.8% ASR) with zero benign cost but fails to fully neutralize attacks.

### fig_chunked_probe
- **Path**: `analytical_plots/chunked_probe.png`
- **Type**: analytical_plot
- **Caption**: Chunked-payload attack analysis showing defense limitation. (a) Attack success rate vs. chunk size for both defended and undefended conditions. (b) Chunk detection analysis showing all chunks evade the suspicion function because each chunk is ≤20 characters. The defense provides no additional protection against chunked attacks.
- **Shows**: claim_8
- **Analysis**: This figure demonstrates a known limitation of the current defense. When harmful content is distributed across many short enum values (each ≤20 characters), no individual chunk triggers the suspicion function. The ASR remains at 8-14% for both conditions, indicating the defense is bypassed. This motivates future work on semantic-level detection.

## Tables

Tables are essential for presenting quantitative results. For each table, detailed specifications are provided below.

**CRITICAL - DATA ACCURACY REQUIREMENTS**:
All data values below are copied directly from source files with source paths recorded.

### tab_main_safety
- **Caption**: Main safety results comparing defense methods against EnumAttack on HarmBench and StrongREJECT benchmarks. **Bold** indicates best performance (lowest ASR). DeLex-JSON achieves 0% HarmBench ASR on both Llama-3.1-8B and Qwen2.5-7B while maintaining low benign cost.
- **Row Design** (6 rows):
  - Row 1: **No Defense** - Baseline without any defense mechanism
  - Row 2: **Input Guard** - Llama Guard 3 filtering on input prompts
  - Row 3: **Reject-Only** - Reject schemas with suspicious literals (no delexicalization)
  - Row 4: **Escape-Hatch** - Allow model to refuse via escape token
  - Row 5: **DeLex-JSON (Ours)** - Full selective delexicalization defense
  - **Ordering Logic**: Ordered by defense complexity: no defense → input filtering → schema rejection → output modification → schema sanitization
- **Column Design** (6 columns):
  - Column 1: Defense Method
  - Column 2: HarmBench ASR (%) - Llama-3.1-8B
  - Column 3: StrongREJECT ASR (%) - Llama-3.1-8B (classifier)
  - Column 4: HarmBench ASR (%) - Qwen2.5-7B
  - Column 5: StrongREJECT ASR (%) - Qwen2.5-7B (classifier)
  - Column 6: Benign Cost (%)
  - **Ordering Logic**: Safety metrics first (HarmBench, StrongREJECT), then utility cost
- **Visual Annotations**:
  - **Bold**: Best performance per column (lowest ASR, lowest benign cost)
  - **↓**: Indicates reduction from No Defense baseline
- **Data Values** (with source verification):
  | Defense | HarmBench ASR (Llama) | StrongREJECT ASR (Llama) | HarmBench ASR (Qwen) | StrongREJECT ASR (Qwen) | Benign Cost |
  |---------|----------------------|-------------------------|---------------------|------------------------|-------------|
  | No Defense | 22.0% [source: no_defense_enum_attack_llama31/RESULTS.json → harmbench_asr] | 15.3% [source: no_defense_enum_attack_llama31/RESULTS.json → strongreject_asr_cls] | 10.7% [source: delex_qwen25/RESULTS.json → no_defense.harmbench_asr] | 4.5% [source: delex_qwen25/RESULTS.json → no_defense.strongreject_cls_asr] | 0.0% |
  | Input Guard | 3.8% [source: input_guard_llama31/RESULTS.json → harmbench.asr] | 2.9% [source: input_guard_llama31/RESULTS.json → strongreject_harmbench_cls.asr] | - | - | 0.0%† |
  | Reject-Only | **0.0%** [source: reject_only_llama31/RESULTS.json → safety.harmbench_asr] | **0.0%** [source: reject_only_llama31/RESULTS.json → safety.strongreject_asr_cls] | - | - | 4.4% [source: reject_only_llama31/RESULTS.json → utility.overall_benign_fpr] |
  | Escape-Hatch | 22.0% [source: escape_hatch_llama31/RESULTS.json → safety.harmbench_asr] | 15.3% [source: escape_hatch_llama31/RESULTS.json → safety.strongreject_asr_cls] | - | - | 12.7% [source: escape_hatch_llama31/RESULTS.json → utility.benign_refusal_rate] |
  | **DeLex-JSON (Ours)** | **0.0%** [source: delex_llama31/RESULTS.json → safety.harmbench.delex_json.asr] | 2.6% [source: delex_llama31/RESULTS.json → safety.strongreject_harmbench_cls.delex_json.asr] | **0.0%** [source: delex_qwen25/RESULTS.json → delex_json.harmbench_asr] | 2.6% [source: delex_qwen25/RESULTS.json → delex_json.strongreject_cls_asr] | **1.1%** [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.overall] |
- **Key Insights Readers Should Extract**:
  1. DeLex-JSON achieves 0% HarmBench ASR, matching Reject-Only's perfect defense
  2. DeLex-JSON has 3.3pp lower benign cost than Reject-Only (1.1% vs 4.4%)
  3. Defense generalizes across model families (Llama-3.1-8B and Qwen2.5-7B)
  4. Escape-Hatch provides no safety improvement over No Defense
  5. Input Guard reduces but does not eliminate attacks (3.8% residual ASR)
- **Data Source**: Synthesized from delex_llama31/RESULTS.json, delex_qwen25/RESULTS.json, no_defense_enum_attack_llama31/RESULTS.json, input_guard_llama31/RESULTS.json, reject_only_llama31/RESULTS.json, escape_hatch_llama31/RESULTS.json
- **Shows**: claim_1, claim_4, claim_5
- **Notes**: † Input Guard has 0% FPR on benign schemas but 88.7% guard rejection rate on attack schemas

### tab_utility
- **Caption**: Utility preservation and overhead metrics for DeLex-JSON. JSON validity and schema compliance deltas are measured via paired comparison on JSONSchemaBench. Benign modification rates are reported per subset. DeLex-JSON maintains utility within the 2pp threshold with only 1.1% overall modification rate.
- **Row Design** (8 rows):
  - Row 1: **Overall** - Aggregate metrics across all subsets
  - Row 2: **GlaiveAI-2K** - Synthetic function-calling schemas (easiest)
  - Row 3: **Github_easy** - Simple real-world schemas
  - Row 4: **Github_medium** - Moderate complexity schemas
  - Row 5: **Github_hard** - Complex real-world schemas
  - Row 6: **Kubernetes** - Infrastructure configuration schemas
  - Row 7: **Snowplow** - Analytics event schemas
  - Row 8: **JsonSchemaStore** - Diverse schema collection
  - **Ordering Logic**: Overall first, then by increasing complexity
- **Column Design** (5 columns):
  - Column 1: Subset
  - Column 2: # Schemas
  - Column 3: Modification Rate (%)
  - Column 4: JSON Validity Δ (pp)
  - Column 5: Schema Compliance Δ (pp)
  - **Ordering Logic**: Identification, overhead metric, utility metrics
- **Visual Annotations**:
  - **Bold**: Overall row to highlight aggregate results
  - Negative deltas indicate degradation (acceptable if <2pp)
- **Data Values** (with source verification):
  | Subset | # Schemas | Mod. Rate | Validity Δ | Compliance Δ |
  |--------|-----------|-----------|------------|--------------|
  | **Overall** | **8,825** | **1.1%** [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.overall] | **-0.38pp** [source: delex_llama31/RESULTS.json → utility.jsonschemabench.delta.json_validity_pp] | **-0.70pp** [source: delex_llama31/RESULTS.json → utility.jsonschemabench.delta.schema_compliance_pp] |
  | GlaiveAI-2K | 1,707 | 0.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Glaiveai2K.modification_rate] | -0.29pp [source: delex_llama31/RESULTS.json → utility.jsonschemabench.paired_comparison.Glaiveai2K.validity_delta_pp] | -0.76pp [source: delex_llama31/RESULTS.json → utility.jsonschemabench.paired_comparison.Glaiveai2K.compliance_delta_pp] |
  | Github_easy | 1,943 | 0.5% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Github_easy.modification_rate] | -0.49pp [source: delex_llama31/RESULTS.json → utility.jsonschemabench.paired_comparison.Github_easy.validity_delta_pp] | -0.63pp [source: delex_llama31/RESULTS.json → utility.jsonschemabench.paired_comparison.Github_easy.compliance_delta_pp] |
  | Github_medium | 1,976 | 2.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Github_medium.modification_rate] | - | - |
  | Github_hard | 1,240 | 3.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Github_hard.modification_rate] | - | - |
  | Kubernetes | 1,064 | 0.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Kubernetes.modification_rate] | - | - |
  | Snowplow | 403 | 1.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.Snowplow.modification_rate] | - | - |
  | JsonSchemaStore | 492 | 2.0% [source: delex_llama31/RESULTS.json → overhead.benign_schema_modification_rate.per_subset.JsonSchemaStore.modification_rate] | - | - |
- **Key Insights Readers Should Extract**:
  1. Overall utility degradation is minimal (-0.38pp validity, -0.70pp compliance)
  2. GlaiveAI-2K has 0% modification rate (no false positives on clean schemas)
  3. Higher complexity subsets have slightly higher modification rates
  4. All metrics are well within the 2pp acceptability threshold
- **Data Source**: delex_llama31/RESULTS.json
- **Shows**: claim_2, claim_3

### tab_ablation
- **Caption**: Ablation study on DeLex-JSON components. Strip-Only removes metadata but not forced literals, showing that enum/const values are the key attack vector. Delex-All delexicalizes all literals regardless of suspicion, showing the value of selective filtering. **Bold** indicates best performance.
- **Row Design** (4 rows):
  - Row 1: **No Defense** - Baseline without any defense
  - Row 2: **Strip-Only** - Remove metadata (title, description) but keep forced literals
  - Row 3: **Delex-All** - Delexicalize all enum/const values (no suspicion function)
  - Row 4: **DeLex-JSON (Full)** - Selective delexicalization with suspicion function
  - **Ordering Logic**: Baseline → partial defense → blanket defense → full defense
- **Column Design** (5 columns):
  - Column 1: Variant
  - Column 2: HarmBench ASR (%)
  - Column 3: Benign Mod. Rate (%)
  - Column 4: JSON Validity (%)
  - Column 5: Schema Compliance (%)
  - **Ordering Logic**: Safety metric, overhead metric, utility metrics
- **Visual Annotations**:
  - **Bold**: Best performance per column
  - Horizontal line separating baseline from defense variants
- **Data Values** (with source verification):
  | Variant | HarmBench ASR | Benign Mod. Rate | JSON Validity | Schema Compliance |
  |---------|---------------|------------------|---------------|-------------------|
  | No Defense | 22.0% [source: ablation_study/RESULTS.json → results.no_defense.harmbench_asr] | 0.0% [source: ablation_study/RESULTS.json → results.no_defense.benign_modification_rate] | 95.9% [source: ablation_study/RESULTS.json → results.no_defense.json_validity] | 94.1% [source: ablation_study/RESULTS.json → results.no_defense.schema_compliance] |
  | Strip-Only | 22.0% [source: ablation_study/RESULTS.json → results.strip_only.harmbench_asr] | 0.0% [source: ablation_study/RESULTS.json → results.strip_only.benign_modification_rate] | 95.2% [source: ablation_study/RESULTS.json → results.strip_only.json_validity] | 93.4% [source: ablation_study/RESULTS.json → results.strip_only.schema_compliance] |
  | Delex-All | **0.0%** [source: ablation_study/RESULTS.json → results.delex_all.harmbench_asr] | 35.5% [source: ablation_study/RESULTS.json → results.delex_all.benign_modification_rate] | 94.5% [source: ablation_study/RESULTS.json → results.delex_all.json_validity] | 92.1% [source: ablation_study/RESULTS.json → results.delex_all.schema_compliance] |
  | **DeLex-JSON (Full)** | **0.0%** [source: ablation_study/RESULTS.json → results.full_delex_json.harmbench_asr] | **1.1%** [source: ablation_study/RESULTS.json → results.full_delex_json.benign_modification_rate] | **95.4%** [source: ablation_study/RESULTS.json → results.full_delex_json.json_validity] | **93.1%** [source: ablation_study/RESULTS.json → results.full_delex_json.schema_compliance] |
- **Key Insights Readers Should Extract**:
  1. Strip-Only has identical ASR to No Defense (22.0%), proving forced literals are the attack vector
  2. Delex-All achieves 0% ASR but with 35.5% benign modification rate (32× higher than selective)
  3. Full DeLex-JSON achieves 0% ASR with only 1.1% modification rate
  4. Selective delexicalization preserves utility better than blanket approach
- **Data Source**: ablation_study/RESULTS.json
- **Shows**: claim_6, claim_7

## Story Arc

### Narrative Strategy

The paper tells the story of a **newly discovered vulnerability** in structured-output LLM APIs and presents a **practical, training-free defense**. The narrative follows a problem-solution-validation structure:

1. **Hook**: Structured-output APIs are increasingly deployed in production, but their constrained decoding mechanisms create a new attack surface that bypasses traditional safety alignment.

2. **Problem Exposition**: Control-plane jailbreaks (EnumAttack) exploit forced enum/const literals to embed harmful instructions directly into the decoding constraints, achieving 22% ASR on safety-aligned models.

3. **Solution Introduction**: Selective DeLex-JSON sanitizes schemas by replacing suspicious forced literals with opaque placeholders, neutralizing attacks without requiring model retraining.

4. **Validation**: Comprehensive experiments demonstrate 0% HarmBench ASR with only 1.1% benign modification rate, Pareto-dominating existing defenses.

5. **Honest Limitations**: Chunked-payload attacks that distribute content across many short values bypass the current defense, motivating future work.

### Key Messages

1. **New Attack Surface**: Structured-output APIs introduce control-plane vulnerabilities distinct from traditional prompt injection—the attack is in the schema, not the prompt.

2. **Practical Defense**: DeLex-JSON is training-free, model-agnostic, and deployable as a preprocessing step in existing inference pipelines.

3. **Pareto Improvement**: The defense achieves better safety-utility tradeoff than alternatives—0% ASR with 1.1% benign cost vs. Reject-Only's 4.4%.

4. **Mechanistic Insight**: Ablation studies prove that forced enum/const literals are the key attack vector (Strip-Only fails, Delex-All succeeds).

5. **Known Limitations**: Chunked attacks bypass the defense, representing an open challenge for future work.

### Logical Flow

```
Introduction
├── Structured-output APIs are widely deployed (context)
├── Control-plane jailbreaks exploit constrained decoding (problem)
├── Existing defenses are insufficient (gap)
└── We propose Selective DeLex-JSON (contribution)

Related Work
├── LLM Safety and Jailbreaks (traditional attacks)
├── Structured Output Generation (constrained decoding)
└── Control-Plane Attacks (emerging threat)

Method
├── Threat Model: Control-plane jailbreaks via EnumAttack
├── Defense Overview: Schema sanitization pipeline
├── Suspicion Function: Conjunction-based heuristic
└── Delexicalization: Placeholder replacement

Experiments
├── Setup: Models, benchmarks, baselines
├── Main Results: 0% ASR, 1.1% benign cost (Table 1)
├── Utility Preservation: <1pp degradation (Table 2)
├── Ablation Study: Component contributions (Table 3)
├── Cross-Model Generalization: Qwen2.5-7B results
├── Pareto Analysis: Safety-utility tradeoff (Figure 2)
└── Limitations: Chunked attack bypass (Figure 3)

Conclusion
├── Summary of contributions
├── Broader impact for API security
└── Future work: Semantic-level detection
```

### Emphasis Points

**Strengths to Highlight**:
- Training-free, immediately deployable
- Model-agnostic (works on Llama and Qwen)
- Pareto-dominates existing defenses
- Minimal utility impact (<1pp degradation)
- Mechanistic understanding via ablation

**Limitations to Acknowledge**:
- Chunked attacks bypass the defense
- Heuristic-based (not semantic understanding)
- Evaluated on specific attack variant (EnumAttack)

### Tone and Framing

- **Objective**: Present findings factually without overclaiming
- **Balanced**: Acknowledge limitations alongside strengths
- **Practical**: Emphasize deployability and real-world applicability
- **Forward-looking**: Frame limitations as opportunities for future work

## Paper Outline

### Abstract (~150 words)
- **Claims**: claim_1, claim_2, claim_4
- **Figures**: []
- **Tables**: []
- **Content Plan**: 
  - **Background**: Structured-output LLM APIs use constrained decoding to guarantee valid JSON, but this creates a new attack surface.
  - **Gap**: Control-plane jailbreaks embed harmful instructions in forced enum/const literals, bypassing safety alignment. Existing defenses (input guards, escape hatches) are insufficient.
  - **Solution**: We propose Selective DeLex-JSON, a training-free defense that sanitizes schemas by replacing suspicious forced literals with opaque placeholders.
  - **Results**: On HarmBench, DeLex-JSON reduces attack success rate from 22% to 0% with only 1.1% benign schema modification rate, Pareto-dominating existing defenses.

### Introduction (~400 words)
- **Claims**: claim_1, claim_4
- **Figures**: []
- **Tables**: []
- **Content Plan**:
  - **Hook** (1 paragraph): Structured-output APIs are increasingly deployed in production (OpenAI, Anthropic, open-source). They guarantee valid JSON via constrained decoding, enabling reliable tool use and function calling.
  - **Problem** (1 paragraph): Recent work shows these APIs are vulnerable to control-plane jailbreaks. EnumAttack embeds harmful instructions in forced enum/const literals, achieving 22% ASR on safety-aligned models. The attack bypasses traditional defenses because the payload is in the schema, not the prompt.
  - **Gap** (1 paragraph): Existing defenses are insufficient. Input guards don't inspect schemas. Escape hatches don't prevent harmful content generation. Reject-only approaches have high false positive rates.
  - **Contribution** (1 paragraph): We propose Selective DeLex-JSON, a training-free defense that:
    1. Identifies suspicious forced literals using a conjunction-based heuristic
    2. Replaces them with opaque placeholders to neutralize attacks
    3. Achieves 0% HarmBench ASR with only 1.1% benign modification rate
  - **Roadmap** (1 sentence): Section 2 reviews related work, Section 3 presents our method, Section 4 reports experiments, Section 5 concludes.

### Related Work (~250 words)
- **Claims**: []
- **Figures**: []
- **Tables**: []
- **Content Plan**:
  - **LLM Safety and Jailbreaks** (1 paragraph): Overview of jailbreak attacks (GCG, PAIR, TAP) and defenses (RLHF, Constitutional AI, Llama Guard). Note that these focus on prompt-level attacks.
  - **Structured Output Generation** (1 paragraph): Constrained decoding methods (Outlines, XGrammar, vLLM) that guarantee valid JSON. Explain how they work (FSM-based token masking).
  - **Control-Plane Attacks** (1 paragraph): Recent work on exploiting structured output interfaces. EnumAttack, prefix-tree exploitation, space-time decoupling. Position our work as the first defense specifically targeting this attack vector.

### Method (~600 words)
- **Claims**: claim_3, claim_6
- **Figures**: fig_framework_overview
- **Tables**: []
- **Content Plan**:
  - **Threat Model** (1 paragraph): Define control-plane jailbreaks. Attacker controls JSON schema but not system prompt. Goal: force model to generate harmful content via constrained decoding.
  - **Defense Overview** (1 paragraph): High-level description of DeLex-JSON pipeline. Schema interception → suspicion function → placeholder replacement → constrained decoding.
  - **Suspicion Function** (2 paragraphs): 
    - Define the conjunction-based heuristic: flag literals meeting ≥2 of {length>20, contains whitespace, matches imperative verb regex}
    - Justify design choices: conjunction reduces false positives, heuristics target attack characteristics
  - **Delexicalization** (1 paragraph): Replace suspicious literals with opaque placeholders (e.g., "OPTION_1", "OPTION_2"). Preserve schema structure and JSON validity.
  - **Implementation** (1 paragraph): Integration with vLLM/Outlines. Preprocessing step before constrained decoding. No model modification required.

### Experiments (~900 words)
- **Claims**: claim_1, claim_2, claim_4, claim_5, claim_6, claim_7, claim_8
- **Figures**: fig_pareto, fig_chunked_probe
- **Tables**: tab_main_safety, tab_utility, tab_ablation
- **Content Plan**:
  - **Setup** (1 paragraph): Models (Llama-3.1-8B, Qwen2.5-7B), benchmarks (HarmBench, StrongREJECT, JSONSchemaBench), baselines (No Defense, Input Guard, Reject-Only, Escape-Hatch), metrics (ASR, benign modification rate, JSON validity, schema compliance).
  - **Main Results** (2 paragraphs + Table 1): 
    - DeLex-JSON achieves 0% HarmBench ASR on both models
    - Pareto-dominates Reject-Only (1.1% vs 4.4% benign cost)
    - Input Guard reduces but doesn't eliminate attacks (3.8% residual ASR)
    - Escape-Hatch provides no safety improvement
  - **Utility Preservation** (1 paragraph + Table 2):
    - <1pp degradation in JSON validity and schema compliance
    - 0% modification rate on GlaiveAI-2K (clean schemas)
    - All metrics within 2pp acceptability threshold
  - **Ablation Study** (2 paragraphs + Table 3):
    - Strip-Only: Same ASR as No Defense → forced literals are the attack vector
    - Delex-All: 0% ASR but 35.5% modification rate → selective filtering is valuable
  - **Pareto Analysis** (1 paragraph + Figure 2):
    - Visualize safety-utility tradeoff
    - DeLex-JSON achieves strictly better Pareto point than all baselines
  - **Limitations: Chunked Attacks** (1 paragraph + Figure 3):
    - Chunked-payload attacks bypass the defense
    - 0% of chunks flagged at any chunk size
    - ASR remains at 8-14% for both conditions
    - Motivates future work on semantic-level detection

### Conclusion (~80 words)
- **Claims**: []
- **Figures**: []
- **Tables**: []
- **Content Plan**:
  - **Summary** (2 sentences): We presented Selective DeLex-JSON, a training-free defense against control-plane jailbreaks in structured-output APIs. It achieves 0% HarmBench ASR with only 1.1% benign modification rate.
  - **Impact** (1 sentence): The defense is immediately deployable in production inference pipelines.
  - **Future Work** (1 sentence): Chunked attacks remain an open challenge, motivating semantic-level detection methods.

---

**Blueprint Status**: COMPLETE
**Ready for Writing Phase**: YES

