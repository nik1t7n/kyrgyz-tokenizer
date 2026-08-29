# Kyrgyz-Russian tokenizer v2 evaluation

Date: 2026-08-29

## Decision

Release `bilingual-gigachat-ru10-32768` as the current Kyrgyz-Russian tokenizer candidate. It uses a 32,768-entry byte-level BPE vocabulary, 90% Kyrgyz and 10% Russian training bytes, the released GigaChat-style category-aware pre-tokenizer, no normalizer, and no special tokens.

Against the Kyrgyz-only 32K v1 baseline on pinned external data, v2 retains 99.25% of Kyrgyz compression and raises Russian compression by 35.33%. It also improves the narrow real mixed-language diagnostic by 9.64%, keeps the same vocabulary size, and has zero byte round-trip failures.

## Controlled setup

Each condition used the same target of 503,316,480 training bytes. The Kyrgyz share preserved the actual corpus-v1 source proportions; the Russian share came from the separately built FineWeb2 `rus_Cyrl` supplement. Validation and external benchmarks never entered BPE training.

The matrix contained:

- Russian shares of 0%, 10%, 20%, and 30%;
- DeepSeek-V3-style and GigaChat-style category-aware pre-tokenizers;
- nested 32K, 40K, and 50K vocabularies derived from one 50K merge history per mixture/pre-tokenizer condition.

This produced eight real parent training runs and 24 comparable candidate tokenizers. Parent training took 18.1-24.4 seconds per 480 MiB condition because Hugging Face Tokenizers executes the BPE core in Rust.

The method transfers published practices without pretending to reproduce unpublished recipes. [DeepSeek-V3](https://arxiv.org/abs/2412.19437) publishes its tokenizer artifact and high-level multilingual compression changes but not its exact tokenizer corpus. [GigaChat Family](https://aclanthology.org/2025.acl-demo.10/) reports more than 100 tokenizer candidates over 30B-300B characters and varied language/code proportions, but not the exact winning mixture. The Russian supplement uses the official [FineWeb2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) release.

## Primary result

Higher bytes/token means the same text uses fewer tokens.

| Tokenizer | Vocabulary | Kyrgyz external | Russian external | Mixed held-out | Code diagnostic |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kyrgyz v1 | 32,768 | 8.983 | 4.786 | 6.505 | 1.594 |
| **Kyrgyz-Russian v2** | **32,768** | **8.916** | **6.477** | **7.132** | **1.604** |
| GigaChat 3 | 128,000 | 4.772 | 7.980 | 4.887 | 4.058 |
| OpenAI o200k | 200,019 | 5.480 | 6.632 | 5.271 | 4.163 |

V2 nearly matches o200k on the Russian benchmark while using about one sixth of its vocabulary, and remains substantially more efficient on Kyrgyz. GigaChat remains better on Russian and code, but uses four times the vocabulary and is much less efficient on Kyrgyz. Those comparisons measure tokenization efficiency only, not model quality.

## What the ablations showed

### Corpus ratio

The preregistered forecast expected 20% Russian to be necessary. The result was better: the 10% condition already crossed the required 20% Russian gain while losing less than 1% on Kyrgyz. At 32K with the GigaChat pre-tokenizer:

| Russian share | Kyrgyz | Russian | Mixed |
| ---: | ---: | ---: | ---: |
| 10% | 8.916 | 6.477 | 7.132 |
| 20% | 8.794 | 6.886 | 7.169 |
| 30% | 8.647 | 7.102 | 7.158 |

Twenty and thirty percent buy additional Russian compression but create a larger Kyrgyz penalty. The 10% condition is the smallest observed intervention that satisfies the published bilingual constraints.

### Pre-tokenizer

At 10% Russian and 32K, GigaChat-style splitting improved Kyrgyz by 0.75% and Russian by 0.19% relative to the DeepSeek-style condition. The effect is small but consistent with the forecast; it is not presented as the main source of the gain.

### Vocabulary size

For the selected 10%/GigaChat condition, increasing 40K to 50K improved Kyrgyz by 2.70%, Russian by 3.61%, and mixed compression by 2.77%. All are below the forecasted 5% threshold, while the embedding table grows by 22.1%. The 32K tokenizer therefore remains the better fit for a future small model under the explicit smallest-vocabulary selection rule.

## Raw failure reading

All candidates decoded every evaluated record exactly. The largest Kyrgyz percentage regressions were short sentences where one or two extra tokens dominate the ratio, for example `Эмнеге болбойт?` (3 to 4 tokens), `Сак болуңуз!` (3 to 4), and `“Тазалык” жумушчуларды издейт.` (7 to 9). A longer SIB-200 example containing `Жолжоболорду` moved from 11 to 14 tokens. These cases show that the small aggregate Kyrgyz loss is real and concentrated in particular whole-word or suffix merges displaced by Russian merges.

Russian improvements are broad rather than confined to long records: `Что происходит?` moved from 7 to 3 tokens, `Что невозможно для человека?` from 12 to 5, and `Это тоже вызывает много вопросов.` from 15 to 6. A few isolated words still regressed by one token, including `Квалификация.` and some names.

On the 21 real mixed records, 20 improved and one changed from 277 to 278 tokens. The strongest gains occurred in Kyrgyz documents containing Russian paragraphs, quotations, titles, or bibliographies. This is useful evidence for local bilingual documents, but it is not a representative chat benchmark.

## Selection rule and evidence boundary

A candidate had to satisfy all of the following before selection:

1. zero round-trip failures;
2. at least 90% of v1 external Kyrgyz bytes/token;
3. at least a 20% improvement over v1 external Russian bytes/token;
4. no Pareto domination over vocabulary size, Kyrgyz compression, and Russian compression.

The smallest remaining vocabulary won; worst-language relative retention only broke ties. Code did not affect selection because the intended market is Kyrgyz-Russian language use, not a code model.

This result establishes a strong intrinsic tokenizer candidate. It does not prove downstream language-model quality: controlled research has shown that fertility alone is not a reliable proxy for downstream performance ([Tokenizer Choice for LLM Training](https://aclanthology.org/2024.findings-naacl.247/)). Training two matched language models remains the extrinsic test, but it is deliberately deferred because it costs much more compute and is unnecessary for choosing the next tokenizer artifact.

The mixed benchmark is also narrow: it is derived from 21 held-out corpus documents detected as containing both high-confidence Kyrgyz and Russian spans. It is dominated by encyclopedic and publication-style material, not natural messaging. A future application study should add consented, licensed Kyrgyz-Russian chat, search, public-service, and business text before claiming market-wide representativeness.

## Reproducibility

- Experiment config SHA-256: `87cdd78c3e652243c11654c7e054a316c50fb649f3c64136947514e8845f8a03`.
- Selected tokenizer metadata and artifact are tracked under `models/kyrgyz-russian-byte-bpe-v2/`.
- The full 24-candidate table and machine-readable evaluation remain under `artifacts/tokenizer-v2/` locally.
- Benchmark manifests pin all external revisions and record output hashes.
