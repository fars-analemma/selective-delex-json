Addressing coverage bias.
Addressing coverage bias.
 The efficiency metrics are meaningful only for instances that a grammar engine can process. Different engines exhibit varying levels of schema coverage with some engines handling a wider range of schemas than others. Engines with lower coverage often process simpler shorter schemas which naturally compile and generate faster. As a result averaging efficiency metrics across covered instances can introduce bias favoring engines with lower coverage. For a more detailed discussion on coverage see Section 5[ref_id]S5. To ensure fairness we calculate efficiency metrics on the intersection of covered instances across all engines.
 Dataset Framework GCT (s) TTFT (s) TPOT (ms)
 GlaiveAI LM only NA 0.10 15.40
 Guidance 0.00 0.24 6.37
 Llamacpp 0.05 0.20 29.98
 Outlines 3.48 3.65 30.33
 GitHub Easy LM only NA 0.10 15.83
 Guidance 0.00 0.34 7.44
 Llamacpp 0.05 0.18 27.22
 Outlines 3.71 3.97 39.78
 Snowplow LM only NA 0.11 16.23
 Guidance 0.00 0.28 6.55
 Llamacpp 0.05 0.20 28.90
 Outlines 3.91 4.14 42.66
 GitHub Medium LM only NA 0.20 16.68
 Guidance 0.01 0.54 7.57
 Llamacpp 0.06 0.30 29.08
 Outlines 8.05 8.38 46.57
 Kubernetes LM only NA 0.16 15.32
 Guidance 0.01 0.45 9.47
 Llamacpp 0.05 0.28 28.04
 Outlines 5.29 5.55 46.10