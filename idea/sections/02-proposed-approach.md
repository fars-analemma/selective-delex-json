## Proposed Approach

### Overview

**Selective DeLex-JSON** is a schema-to-schema transformation applied *before* constrained decoding:

1. **Strip free-text fields** that can carry hidden payloads but are not needed for decoding (e.g., `description`, `title`, `examples`, `default`).
2. **Selective delexicalization of forced literals**: for every string literal that will be forced into the generation stream (primarily `enum` and `const`, optionally other forcing constructs depending on the decoding engine), replace suspicious literals with placeholders `E_i`.
3. Run constrained decoding on the sanitized schema.
4. (Optional for downstream compatibility) Postprocess placeholders back to original literals for API consumers, while ensuring **safety evaluation only judges model-generated free-text fields**, not forced literals.

### Method Details

**Threat model.** The attacker controls the schema and aims to cause the model to generate harmful content in a free-text field (e.g., `answer`). The defender is the API provider who can transform schemas and enforce constrained decoding.

**Schema parsing and target set.** Extract a set of forced string literals:
- JSON Schema `enum` string values
- JSON Schema `const` string values
- (v1 scope) do **not** delexicalize property names; we treat property-name injection as out-of-scope or as a small diagnostic probe.

**Suspicion function (pre-registered).** A literal is delexicalized if ANY of:
- length > 20 characters
- contains whitespace (spaces/newlines/tabs)
- matches simple instruction-like regexes (e.g., “Sure,” “Step 1”, “here’s how”, imperative verbs + punctuation-heavy patterns)
- optional guard-model flag: a lightweight safety classifier (e.g., Llama Guard) marks it unsafe

These thresholds/rules will be **frozen before evaluation on HarmBench/StrongREJECT** to avoid leakage.

**Placeholder scheme.** Replace flagged literals with unique opaque IDs `E0`, `E1`, … and record a mapping table.

**Safety evaluation protocol (critical).** Since forced literals may contain attacker-supplied harmful text, we compute ASR/StrongREJECT only on model-generated free-text fields (e.g., extract `answer` string), masking or removing forced literals prior to scoring.

### Key Innovations

- **Delexicalization as a security primitive for structured-output APIs**: blocks control-plane natural-language injection without full token-provenance infrastructure.
- **Selective, not blanket, transformation**: preserves short semantic enums (tool IDs, class labels) while neutralizing long natural-language payloads.
- **Evaluation protocol that separates forced vs model-generated content**, reducing judge contamination.

---