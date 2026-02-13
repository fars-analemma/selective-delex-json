Time per output token.
Time per output token.
 While Outlines and Llamacpp demonstrate substantially lower throughput than the LM-only approach Guidance achieves even higher efficiency which it accomplishes by skipping certain generation steps with its guidance acceleration ~\cite{bib.bib16}. Comparing Guidance and XGrammar with the HF Transformers backend shows that Guidance has a significantly better TPOT.
 Dataset Framework GCT (s) TTFT (s) TPOT (ms)
 GlaiveAI Guidance 0.01 0.36 36.92
 XGrammar 0.12 0.30 66.78
 GitHub Easy Guidance 0.01 0.37 42.03
 XGrammar 0.11 0.33 65.57
 GitHub Medium Guidance 0.01 0.55 44.21
 XGrammar 0.20 0.48 65.51
 GitHub Hard Guidance 0.01 0.73 35.88
 XGrammar 0.30 0.65 65.20


## Section References
[bib.bib16] GuidanceAI (2024b) GuidanceAI. Guidance acceleration tutorial. https://guidance.readthedocs.io/en/stable/example_notebooks/tutorials/guidance_acceleration.html 2024b. Accessed: 2025-01-16.