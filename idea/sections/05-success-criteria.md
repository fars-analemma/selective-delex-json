## Success Criteria

**Criterion 1: CDA robustness under constrained decoding**
- Hypothesis: Removing contiguous natural-language literals from the constrained-decoding context blocks CDA-style priming.
- Validation: If baseline attack ASR ≥30% on HarmBench/StrongREJECT, Selective DeLex-JSON reduces ASR to <10% absolute on the primary model.

**Criterion 2: Utility preservation for structured outputs**
- Hypothesis: Most benign structured-output schemas use short semantic enums and do not require long natural-language literals.
- Validation: On JSONSchemaBench + IFEval(JSON), JSON validity and task scores do not degrade by more than ~2pp vs no defense, and benign schema reject+modify rate stays low (≤2%).

**Criterion 3: Better Pareto point than reject-only filtering**
- Hypothesis: Delexicalization retains more benign schemas than audit-reject, while still blocking attacks.
- Validation: For similar ASR reduction, DeLex-JSON has lower benign rejection/modification costs than reject-only baselines.

---