4 Efficiency
Naïve implementations of constrained decoding add overhead to the standard LM inference process including a per-step mask computation and an optional one-time grammar compilation. However several optimizations can significantly reduce this overhead. For instance mask computation can run in parallel with the LM’s forward pass and grammar compilation can be performed concurrently with pre-filling computations~\cite{bib.bib14 bib.bib8}. Other optimizations such as grammar caching and constraint-based speculative decoding~\cite{bib.bib16 bib.bib5 bib.bib20} can further reduce overhead.


## Section References
[bib.bib14] Guidance AI (2023) Guidance AI. Guidance: A language model programming framework 2023. URL https://github.com/guidance-ai/guidance. Accessed: 2024-12-18.
[bib.bib8] Dong et al. (2024) Yixin Dong Charlie F. Ruan Yaxing Cai Ruihang Lai Ziyi Xu Yilong Zhao and Tianqi Chen. XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models November 2024. URL http://arxiv.org/abs/2411.15100. arXiv:2411.15100 [cs].
[bib.bib16] GuidanceAI (2024b) GuidanceAI. Guidance acceleration tutorial. https://guidance.readthedocs.io/en/stable/example_notebooks/tutorials/guidance_acceleration.html 2024b. Accessed: 2025-01-16.
[bib.bib5] Beurer-Kellner et al. (2023) Luca Beurer-Kellner Marc Fischer and Martin Vechev. Prompting Is Programming: A Query Language for Large Language Models. Proceedings of the ACM on Programming Languages 7(PLDI):1946–1969 June 2023. ISSN 2475-1421. doi: 10.1145/3591300. URL http://arxiv.org/abs/2212.06094. arXiv:2212.06094 [cs].
[bib.bib20] Kurt (2024a) Will Kurt. Coalescence: Making llm inference 5x faster. https://blog.dottxt.co/coalescence.html 2024a. Accessed: 2024-12-21.