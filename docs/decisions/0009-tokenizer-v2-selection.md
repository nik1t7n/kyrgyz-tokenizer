# Decision 0009: Release the 32K 10%-Russian v2 candidate

Date: 2026-08-29

## Context

The controlled v2 experiment evaluated 24 byte-level BPE candidates across four Russian corpus shares, two published category-aware pre-tokenizers, and three nested vocabulary sizes. Selection required exact round trips, at least 90% retention of v1 Kyrgyz compression, at least 20% Russian improvement, and Pareto efficiency over the two languages and vocabulary size.

The candidate `bilingual-gigachat-ru10-32768` reaches 8.916 bytes/token on external Kyrgyz data and 6.477 on external Russian data. Relative to the 32K Kyrgyz v1 baseline, that is a 0.75% Kyrgyz reduction and a 35.33% Russian gain. It improves the narrow real mixed-language diagnostic by 9.64% and has zero round-trip failures.

## Decision

Release `bilingual-gigachat-ru10-32768` as `kyrgyz-russian-byte-bpe-v2`. Keep the vocabulary at 32,768 entries, use 90% Kyrgyz and 10% Russian training bytes, and use the exact released GigaChat-style category-aware pre-tokenizer structure.

Do not rewrite the orchestration layer in Rust. Hugging Face Tokenizers already runs the relevant core in Rust, and each 480 MiB parent condition trained in 18.1-24.4 seconds. There is no measured implementation bottleneck to justify a rewrite.

## Tradeoffs

- A 20% or 30% Russian share compresses Russian more strongly but causes a larger Kyrgyz loss.
- A 40K or 50K vocabulary improves both languages but increases future embedding and output-layer cost; 40K to 50K gives less than 5% additional compression.
- GigaChat-style splitting provides a small consistent gain over the DeepSeek-style alternative at the chosen corpus ratio; the corpus mixture causes most of the improvement.
- This is an intrinsic tokenizer decision. Downstream language-model quality and natural chat code-switching remain unproven.
