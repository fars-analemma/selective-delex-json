Llama
In this section, we present t-SNE visualizations of the representation space changes in the steered model (Llama-3-8B-Instruct) across all layers for both STEER-COMPLIANCE and STEER-JSON. In Figure 15, the representation space of the original Llama-3-8B-Instruct shows a clear separation between harmful queries (red) and harmless queries (blue), even at the initial embedding level. As the layers progress, this separation signal becomes stronger. This trend is further corroborated by the linear classification accuracy plotted in Figure 18. However, when STEER-COMPLIANCE and STEER-JSON are applied, the landscape changes. As seen in Figure 16 (STEER-COMPLIANCE) and Figure 17 (STEER-JSON), a portion of the harmful queries shifts toward the harmless region. This implies that applying benign activation steering causes harmful embeddings to merge with harmless ones, rendering them inseparable. Consequently, the target model fails to recognize the harm, leading to the generation of harmful responses. We emphasize that t-SNE is a qualitative projection and the 2D boundary is only an illustrative diagnostic. Nevertheless, the consistent displacement of steered harmful representations toward harmless regions under both steering aligns with the refusal-gate hypothesis and helps explain why benign steering can amplify jailbreak success rates.

[IMAGE START]Figure 6 .. Figure 6. Per-token KL Divergence between Original and JSON Steered Model on Llama-3-8B-Instruct. Red lines indicate the KL Divergence on Harmbench responses, blue lines are the KL Divergence on Alpaca (Benign) responses.[IMAGE END]


[IMAGE START]Figure 15 . Figure 15. Layerwise t-SNE visualization of harmful vs harmless prompts across layers (Meta-Llama-3-8B-Instruct).[IMAGE END]


[IMAGE START]Figure 17 . Figure 17. Layerwise t-SNE visualization including JSON steered harmful prompts. Steered harmful representations shift toward the harmless cluster across layers.[IMAGE END]


[IMAGE START]Figure 18 . Figure 18. Linear separability (classification accuracy) of harmful vs harmless prompt regressions observed on HarmBench latent representations across layers.[IMAGE END]
