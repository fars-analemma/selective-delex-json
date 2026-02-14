# Chunked-Payload Attack Probe: Boundary Analysis for Selective DeLex-JSON

## Experiment Overview

This experiment tests a chunked-payload variant of the EnumAttack that distributes a harmful prompt across many short enum values, each individually below the suspicion threshold of DeLex-JSON. The goal is to map the boundary conditions of the defense and understand whether splitting a long malicious literal into multiple short segments can bypass detection.

## Setup

- **Model**: Llama-3.1-8B-Instruct (via vLLM, 1 GPU)
- **Prompts**: First 50 HarmBench prompts (deterministic subset covering 6 harm categories)
- **Chunk sizes**: 5, 10, 15, 20 characters
- **Conditions**: 8 total (4 chunk sizes x 2 defense modes: none, delex)
- **Classifier**: HarmBench Llama-2-13b-cls
- **Generation params**: temperature=0.6, max_tokens=1024
- **Eval extraction**: Only the free-text `answer` field (consistent with standard EnumAttack eval)

### Attack Construction

For each harmful prompt, the attack:
1. Concatenates the harmful question + affirmative prefix ("Sure, here is a detailed guide on how to")
2. Splits the text into chunks of <= N characters on word boundaries, replacing spaces with underscores (no whitespace within any chunk)
3. Creates a JSON schema with fields `chunk_0`..`chunk_N` (each a single-value enum) + a free-text `answer` field

## Key Results

| Condition | Chunk Size | ASR | Total Chunks | Flagged | Bypass Rate |
|-----------|-----------|-----|-------------|---------|-------------|
| No Defense | 5 | 14.0% | 1451 | 0 | 100% |
| No Defense | 10 | 12.0% | 801 | 0 | 100% |
| No Defense | 15 | 10.0% | 499 | 0 | 100% |
| No Defense | 20 | 10.0% | 378 | 0 | 100% |
| DeLex-JSON | 5 | 8.0% | 1451 | 0 | 100% |
| DeLex-JSON | 10 | 8.0% | 801 | 0 | 100% |
| DeLex-JSON | 15 | 14.0% | 499 | 0 | 100% |
| DeLex-JSON | 20 | 8.0% | 378 | 0 | 100% |

**Average ASR**: No Defense = 11.5%, DeLex-JSON = 9.5%

### Field Count Scaling

- cs=5: ~29 fields per prompt (range: ~20-43)
- cs=10: ~16 fields per prompt (range: ~10-25)
- cs=15: ~10 fields per prompt (range: ~6-15)
- cs=20: ~7.5 fields per prompt (range: ~5-12)

## Key Observations

### 1. Complete Detection Bypass

DeLex-JSON's `is_suspicious()` heuristic flags zero chunks across all conditions. The heuristic requires 2+ reasons to flag a literal. Each chunk has:
- Length <= 20 chars (no "length>20" reason)
- No whitespace -- underscores replace spaces (no "whitespace" reason)
- Most chunks don't match instruction regex patterns (0 or 1 reason max)

Result: DeLex-JSON makes **zero placeholder replacements** and provides no additional protection beyond what the model's inherent alignment provides.

### 2. Low Attack Effectiveness Despite Bypass

Despite completely evading DeLex-JSON, the chunked attack achieves only 8-14% ASR -- significantly lower than the standard EnumAttack (which typically achieves 80-90%+ ASR). Fragmenting the harmful content across many small enum fields:
- Breaks the coherent harmful instruction into disconnected word fragments
- Reduces the model's ability to interpret the concatenated context as a coherent harmful request
- The model's safety alignment remains partially effective when the harmful "priming" is fragmented

### 3. Chunk Size Has Minimal Effect

ASR does not vary significantly with chunk size (range: 8-14% across all conditions). Neither smaller chunks (more fragmentation, more fields) nor larger chunks (fewer but more readable fragments) consistently produce higher attack success.

### 4. No Defense vs DeLex-JSON Gap

The difference between no-defense and DeLex-JSON ASR is negligible and within noise (11.5% vs 9.5% mean). This is expected since DeLex-JSON makes no modifications to the schemas.

## Implications and Recommendations

### Defense Gap

DeLex-JSON's per-literal suspicion heuristic is fundamentally blind to distributed payloads. The current 2-reason threshold design cannot detect many short, individually-benign values that together form harmful content.

### Recommended Mitigations for Future Work

1. **Cross-field content aggregation**: Concatenate all enum/const values across the schema and run suspicion analysis on the aggregate text, not per-literal.
2. **Schema complexity heuristic**: Flag schemas with unusually many single-enum fields (e.g., >5 single-value enum fields is atypical for benign use).
3. **Per-field length lower-bound**: Very short enum values in large numbers are atypical for legitimate structured output.
4. **Semantic coherence check**: Detect when concatenated enum values form coherent natural language (e.g., via perplexity scoring).

### Threat Assessment

**Low-to-moderate threat level.** The chunked-payload attack completely bypasses DeLex-JSON's detection mechanism but is inherently weakened by the fragmentation itself. The 8-14% ASR is far below the ~85%+ ASR of the standard EnumAttack, making this a less practical attack vector despite evading the defense. This is acknowledged as an out-of-scope threat for DeLex-JSON v1 but valuable for informing future defense designs.
