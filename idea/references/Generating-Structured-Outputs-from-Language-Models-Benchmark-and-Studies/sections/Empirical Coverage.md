Empirical Coverage
Empirical Coverage
 Guidance shows the highest empirical coverage on six out of the eight datasets with Llamacpp taking the lead on the remaining two: the domain-specific Washington Post and notably hard JSON Schema Store. On the other hand closed-source grammar engines consistently have the lowest coverage; they came in last on all but one dataset. LM-only4The Llama 3.1 models have been specifically fine-tuned to adhere to JSON schemas~\cite{bib.bib13} approaches achieve acceptable coverage on easy-to-medium datasets but show significant performance drops on harder datasets such as Github Hard and JSON Schema Store as well as domain-specific datasets like Washington Post. We note that while empirical coverage is a reasonable indicator of a framework’s real-world performance it is influenced by factors such as the LM being used and the sampling methods employed.
 Dataset Framework Declared Empirical Compliance Rate
 GlaiveAI LM only 1.00 0.90 0.90
 Guidance 0.98 0.96 0.98
 Llamacpp 0.98 0.95 0.97
 Outlines 0.99 0.95 0.96
 XGrammar 1.00 0.93 0.93
 OpenAI 0.89 0.89 1.00
 Gemini 0.86 0.86 1.00
 GitHub Easy LM only 1.00 0.65 0.65
 Guidance 0.90 0.86 0.96
 Llamacpp 0.85 0.75 0.88
 Outlines 0.86 0.59 0.83
 XGrammar 0.91 0.79 0.87
 OpenAI 0.30 0.29 0.97
 Gemini 0.08 0.07 0.88
 Snowplow LM only 1.00 0.46 0.46
 Guidance 0.87 0.82 0.94
 Llamacpp 0.92 0.74 0.81
 Outlines 0.95 0.36 0.61
 XGrammar NA NA NA
 OpenAI 0.21 0.21 1.00
 GitHub Medium LM only 1.00 0.38 0.38
 Guidance 0.79 0.69 0.87
 Llamacpp 0.77 0.57 0.74
 Outlines 0.72 0.29 0.40
 XGrammar 0.79 0.52 0.66
 OpenAI 0.13 0.12 0.92
 Kubernetes LM only 1.00 0.56 0.56
 Guidance 0.98 0.91 0.92
 Llamacpp 0.98 0.76 0.78
 Outlines 0.98 0.57 0.58
 XGrammar 0.12 0.07 0.58
 OpenAI 0.21 0.21 1.00
 Washington Post LM only 1.00 0.40 0.40
 Guidance 0.86 0.86 1.00
 Llamacpp 0.97 0.94 0.97
 Outlines 0.97 0.22 0.23
 XGrammar 0.85 0.64 0.75
 OpenAI 0.13 0.13 1.00
 GitHub Hard LM only 1.00 0.13 0.13
 Guidance 0.60 0.41 0.69
 Llamacpp 0.61 0.39 0.63
 Outlines 0.47 0.03 0.06
 XGrammar 0.69 0.28 0.41
 OpenAI 0.09 0.09 1.00
 JsonSchemaStore LM only 1.00 0.21 0.21
 Guidance 0.35 0.30 0.88
 Llamacpp 0.54 0.38 0.69
 Outlines 0.38 0.09 0.24
 XGrammar 0.76 0.33 0.43
 OpenAI 0.06 0.06 1.00


## Section References
[bib.bib13] Grattafiori et al. (2024) Aaron Grattafiori Abhimanyu Dubey Abhinav Jauhri Abhinav Pandey Abhishek Kadian Ahmad Al-Dahle Aiesha Letman Akhil Mathur Alan Schelten and Alex Vaughan et al. The llama 3 herd of models 2024. URL https://arxiv.org/abs/2407.21783.