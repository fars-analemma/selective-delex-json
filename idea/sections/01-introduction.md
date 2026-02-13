# Selective Delexicalization to Defend Structured-Output LLM APIs from Control-Plane Jailbreaks

## Scope and Constraints

- **Paper Type**: Short paper
- **Target Venues**: NeurIPS, ICML, ICLR, ACL, EMNLP (or similar top AI conferences)

## Introduction

### Context and Motivation

Structured-output APIs (JSON Schema / grammar-constrained decoding) are becoming the default interface for tool-using agents and production LLM systems.

Modern LLM applications increasingly require **machine-consumable structured outputs** (JSON objects, function-call arguments, typed fields) to integrate with downstream software. Constrained decoding frameworks (e.g., grammar-guided decoding) provide high JSON validity and schema compliance, enabling reliable tool use.

### The Problem

However, constrained decoding introduces a new **control-plane attack surface**: an attacker can supply a schema whose forced literals (e.g., enum strings) inject malicious content into the model’s output prefix, bypassing both prompt auditing and shallow refusal behaviors. Constrained Decoding Attacks (CDA) can hide harmful intent inside forced JSON-schema literals (e.g., `enum`/`const` strings) and achieve near-100% attack success rates (ASR) with a single query on multiple safety benchmarks (**[CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt)**). The CDA / EnumAttack results show this can jailbreak both proprietary and open-weight models at near-100% ASR, and even produce highly harmful content measured by StrongREJECT.

- **Control-plane jailbreaks (CDA/EnumAttack).** The CDA paper (**[CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt)**) demonstrates that JSON-schema constraints can force models into harmful continuations. They sketch defenses like refusal-token whitelists, token provenance tracking, and safety signaling, but do not provide an operational, low-overhead implementation with a utility/safety Pareto analysis.
- **Developer-side safety regressions under “benign” structured-output steering.** Even non-adversarial deployment interventions can raise jailbreak risk: Steering Externalities reports that on 400 HarmBench prompts, Llama-3-8B-Instruct ASR rises from **2.00%** to **20.00%** under **STEER-JSON** and to **38.50%** under **STEER-COMPLIANCE** (**[Steering Externalities](./references/Steering-Externalities-Benign-Activation-Steering-Unintentionally-Increases-Jailbreak-Risk-for-Large-Language-Models/sections/K.%20Numerical%20value%20of%20Intrinsic%20and%20Synergistic%20Vulnerabilities.md)**, Table 10). This strengthens the case that structured-output reliability features and safety can interact non-trivially.
- **Decoding-time safety interventions.** CARE proposes rollback + introspection to reduce harmful responses during decoding (**[CARE](./references/CARE-Decoding-Time-Safety-Alignment-via-Rollback-and-Introspection-Intervention/meta/meta_info.txt)**), but it targets data-plane harmful prompts rather than control-plane schema payloads.

In 2026, practitioners want to keep structured-output interfaces (for agents and tool use) but need **cheap, deployment-ready mitigations** against control-plane jailbreaks. Naively rejecting all schemas with unusual strings is brittle and may cause high false positives; comprehensive output auditing is expensive and often disabled for latency. The CDA paper’s suggested defenses (provenance tracking; deeper integration) may be costly to deploy in common constrained-decoding libraries.

### Key Insight and Hypothesis

We propose a simple, training-free defense primitive: **Selective Delexicalization (Selective DeLex-JSON)**. Before compiling a user-provided JSON schema into a constrained-decoding grammar, we (1) strip non-semantic free-text schema fields, and (2) replace **suspicious forced literals** (long / whitespace-rich / instruction-like `enum`/`const` strings) with short opaque placeholders (e.g., `E7`). This prevents natural-language payloads from entering the model’s autoregressive context—the hypothesized mechanism that makes CDA effective—while preserving typical benign schemas whose enums are short identifiers (tool names, class labels).

CDA/EnumAttack succeeds largely because it injects **contiguous natural-language priming strings** into the autoregressive context via forced literals (e.g., long `enum`/`const` strings). If we prevent these strings from ever appearing during model generation—by replacing them with opaque placeholders—then the model cannot be steered into harmful continuations by control-plane literal injection, while most benign schemas (whose enums are short IDs) remain usable.

If, on a primary open-weight model (pre-registered) under a fixed constrained-decoding stack, CDA-style attacks have baseline ASR ≥30% on HarmBench/StrongREJECT, then **Selective DeLex-JSON must reduce ASR to <10% absolute** while keeping benign structured-output utility within ~2 percentage points of the no-defense baseline on JSONSchemaBench/IFEval-style tasks, and keeping benign schema rejection+modification rate low (≤2%). Otherwise we refute (or narrow scope).

---