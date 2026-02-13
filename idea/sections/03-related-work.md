## Related Work

### Field Overview

LLM safety research has largely focused on data-plane prompt-based jailbreaking and defenses, with standardized benchmarks such as HarmBench and StrongREJECT. In parallel, structured output reliability research has developed constrained decoding frameworks and benchmarks (e.g., JSONSchemaBench). Control-plane jailbreaks (CDA) connect these threads: structured-output constraints can override refusal behavior and bypass prompt auditing, suggesting that “safety alignment is only a few tokens deep” in practice.

Defenses span (i) prompt/input auditing, (ii) output auditing / guard models, (iii) decoding-time interventions, and (iv) training-time alignment. Our proposal targets a distinct mechanism: **literal injection via forced schema strings** (best matched by EnumAttack-style CDAs). We note that more sophisticated CDAs that decouple payloads across many short literals and/or across turns (sometimes framed as **DictAttack / space–time decoupling** in follow-up work) may bypass single-plane schema sanitization; we treat these as *out-of-scope for v1* and as a likely boundary condition, and we include a simplified “chunked payload” probe to map the boundary.

### Related Papers

- **[CDA / Output Constraints as Attack Surface](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt)**: Introduces control-plane CDA/EnumAttack achieving near-100% ASR by embedding harmful payloads in structured-output constraints.
- **[Steering Externalities](./references/Steering-Externalities-Benign-Activation-Steering-Unintentionally-Increases-Jailbreak-Risk-for-Large-Language-Models/meta/meta_info.txt)**: Shows benign JSON/compliance activation steering increases HarmBench ASR, motivating structured-output safety auditing.
- **[StrongREJECT](https://openreview.net/forum?id=al303JJkGO)**: Provides a benchmark and scoring rubric for harmfulness beyond binary ASR.
- **[HarmBench](https://arxiv.org/abs/2402.04249)**: Standardized automated red-teaming benchmark with classifier-based ASR evaluation.
- **[JailbreakBench](https://openreview.net/forum?id=urjPCYZt0I)**: Benchmark for jailbreaking robustness across diverse harm categories.
- **[AdvBench / GCG paper](https://arxiv.org/abs/2307.15043)**: Universal adversarial suffix attack benchmark and methodology for black-box jailbreaks.
- **[SORRY-Bench](https://openreview.net/forum?id=YfKNaRktan)**: Systematic evaluation of refusal behavior across many harm categories.
- **[MASTERKEY](https://www.ndss-symposium.org/ndss-paper/masterkey-automated-jailbreaking-of-large-language-model-chatbots/)**: Template-based automated jailbreaking for chat models.
- **[PAIR](https://arxiv.org/abs/2310.08419)**: Prompt Automatic Iterative Refinement, a black-box iterative jailbreak method.
- **[TAP](https://openreview.net/forum?id=SoM3vngOH5)**: Tree-of-attacks search method for black-box jailbreaking.
- **[CoP](https://arxiv.org/abs/2506.00781)**: Agentic red-teaming by composing jailbreak principles.
- **[Enforced Decoding (EnDec)](https://aclanthology.org/2024.acl-long.299/)**: Shows jailbreaking open LLMs by controlling logits / enforced decoding.
- **[APT / Prefix-tree structured-output jailbreaking](https://arxiv.org/abs/2502.13527)**: Exploits structured-output interfaces via prefix-tree search to bypass refusals.
- **[CARE](./references/CARE-Decoding-Time-Safety-Alignment-via-Rollback-and-Introspection-Intervention/meta/meta_info.txt)**: Decoding-time rollback+introspection intervention for safety–quality tradeoffs.
- **[Llama Guard](https://arxiv.org/abs/2312.06674)**: Guard model for safety classification of prompts/outputs.
- **[Constitutional AI](https://arxiv.org/abs/2212.08073)**: RLAIF framework for principled harmlessness.
- **[StruQ](./references/StruQ-Defending-Against-Prompt-Injection-with-Structured-Queries/meta/meta_info.txt)**: Uses structured queries and training to defend prompt-injection in LLM-integrated apps.
- **[JSONSchemaBench](./references/Generating-Structured-Outputs-from-Language-Models-Benchmark-and-Studies/meta/meta_info.txt)**: Benchmark for structured generation frameworks (coverage, compliance, efficiency, and quality).
- **[Outlines](https://arxiv.org/abs/2307.09702)**: Finite-state guided generation framework supporting regex/grammar/JSON constraints.
- **[XGrammar](https://arxiv.org/abs/2403.05196)**: Efficient grammar-constrained decoding engine.
- **[SynCode](https://arxiv.org/abs/2401.05767)**: Grammar-guided code generation with constrained decoding.
- **[Safety Alignment Should be More Than a Few Tokens Deep](https://openreview.net/forum?id=6Mxhg9PtDE)**: Argues safety concentrated in early tokens is brittle, motivating control-plane defenses.

### Taxonomy

| Family / cluster | Core idea | Representative papers | Benchmarks / evaluation | Known limitations |
|---|---|---|---|---|
| Control-plane structured-output attacks | Inject harmful intent via constrained decoding rules | CDA/EnumAttack, APT | HarmBench, StrongREJECT, AdvBench | Requires structured-output interface; attack surface varies by decoder |
| Prompt-based jailbreaks (data-plane) | Optimize or search prompts to elicit harm | GCG, PAIR, TAP, MASTERKEY, CoP | AdvBench, JailbreakBench, HarmBench | Often needs multiple queries; mitigations exist via prompting/guards |
| Decoding-time defenses | Intervene during generation to avoid unsafe trajectories | CARE, SafeDecoding-style work | BeaverTails, HarmBench | Can add latency; typically targets data-plane harmful prompts |
| Input/output auditing | Classify harmfulness of prompts/outputs | Llama Guard, output scouting | HarmBench, SORRY-Bench | Expensive; false positives/negatives; may miss control-plane payloads |
| Structured generation reliability | Ensure schema compliance and measure it | JSONSchemaBench, Outlines, XGrammar | JSONSchemaBench, IFEval | Typically ignores safety; can introduce new attack surfaces |

### Closest Prior Work

1. **CDA / Output Constraints as Attack Surface** (**[CDA paper](./references/Output-Constraints-as-Attack-Surface-Exploiting-Structured-Generation-to-Bypass-LLM-Safety-Mechanisms/meta/meta_info.txt)**)
   - **What it does**: Defines CDA/EnumAttack and demonstrates high ASR across models and benchmarks; sketches mitigations like refusal whitelists and token provenance.
   - **Key limitation**: Does not provide a low-overhead, library-compatible mitigation with quantified safety–utility tradeoff.
   - **Why ours differs**: We propose and test **delexicalization of forced literals** as a mitigation primitive, and provide a structured evaluation protocol separating forced vs model-generated content.

2. **Steering Externalities** (**[Steering Externalities](./references/Steering-Externalities-Benign-Activation-Steering-Unintentionally-Increases-Jailbreak-Risk-for-Large-Language-Models/meta/meta_info.txt)**)
   - **What it does**: Shows benign JSON/compliance activation steering can increase ASR.
   - **Key limitation**: Not about constrained decoding or schema payload injection.
   - **Why ours differs**: We defend structured-output interfaces by transforming schemas (no activation steering assumed).

3. **CARE** (**[CARE](./references/CARE-Decoding-Time-Safety-Alignment-via-Rollback-and-Introspection-Intervention/meta/meta_info.txt)**)
   - **What it does**: Applies targeted rollback + introspection when unsafe content detected during decoding.
   - **Key limitation**: Requires continuous guard monitoring and targets data-plane unsafe prompts.
   - **Why ours differs**: We target **control-plane literal injection** with a preprocessing step, aiming for near-zero runtime overhead.

### Comparison Table

| Related work | What it does (1 sentence) | Key limitation / gap | What we change | Why ours should win (hypothesis + evidence) |
|---|---|---|---|---|
| CDA/EnumAttack | Shows control-plane JSON-schema literal injection jailbreaks models | Defenses not operationalized; no low-overhead mitigation | Transform schema to remove natural-language literals from generation stream | If CDA relies on literal priming, removing literals should break the mechanism |
| Input/output guard models | Classify harmful prompts/outputs | Can be bypassed; expensive; schema payloads may not be audited | Audit/transform schema *before* decoding | Prevent attack mechanism rather than detect after the fact |
| CARE | Decoding-time rollback/introspection on unsafe tokens | Runtime overhead; targets data-plane | Static preprocessing (delex) | Blocks priming with minimal runtime cost |
| Reject-only schema filtering | Reject risky schemas | High false positives; reduces utility | Delex instead of reject | Should preserve more benign schemas while neutralizing payload |

---