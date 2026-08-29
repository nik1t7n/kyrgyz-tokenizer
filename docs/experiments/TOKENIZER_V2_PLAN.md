# Kyrgyz-Russian tokenizer v2 experiment

Date: 2026-08-29

Status: completed. The preregistered matrix selected `bilingual-gigachat-ru10-32768`; see [the evaluation report](../reports/TOKENIZER_V2_EVALUATION.md).

## Desired outcome

Select the smallest category-aware byte-level BPE tokenizer that materially improves Russian text efficiency while retaining the dedicated tokenizer's Kyrgyz advantage. The intended use is a future small bilingual model for the Kyrgyz market, where Kyrgyz and Russian are both common. Code is a bounded robustness diagnostic, not a training-corpus priority.

This is not copied from a general multilingual trend. The concrete product constraint is local bilingual use: the monolingual 32K v1 tokenizer compresses external Kyrgyz strongly but its Russian efficiency trails a Russian-specialized tokenizer.

## Baseline evidence

On the currently pinned evaluation data:

| Tokenizer | Vocabulary | Kyrgyz bytes/token | Russian UD SynTagRus bytes/token |
| --- | ---: | ---: | ---: |
| Kyrgyz BPE v1 | 32,768 | 8.983 | 4.740 |
| DeepSeek-V3 | 128,000 | 3.530 | 5.767 |
| Qwen2.5 | 151,643 | 3.261 | 5.176 |
| GigaChat 3 | 128,000 | 4.772 | 7.746 |

The Russian row is an initial diagnostic, not the final v2 test result.

## Inputs to upgrade

1. Keep the complete, provenance-preserving Kyrgyz corpus v1 unchanged.
2. Build a separate 160 MiB Russian supplement from the pinned FineWeb2 `rus_Cyrl` subset. Use deterministic approximate streaming shuffle, the existing structural filters, exact and near deduplication, and a hash-based 99/1 split.
3. Add pinned Russian validation and external benchmarks.
4. Derive a real mixed-language diagnostic from held-out web documents only if the source actually contains both Kyrgyz- and Russian-labelled spans. Do not manufacture code-switched text.
5. Add the official GigaChat tokenizer artifact as the Russian-specialized baseline.

## Controlled experiment

Hold total tokenizer-training text constant. Compare:

- Russian byte shares: 0%, 10%, 20%, and 30%;
- pre-tokenizers: the published DeepSeek-V3 structure and the published GigaChat 3 structure;
- nested vocabularies: 32K, 40K, and 50K, each derived from one 50K merge history per corpus/pre-tokenizer condition.

The Kyrgyz portion preserves the corpus-v1 source proportions. Candidate models use only training shards; validation and external data never enter BPE training.

## Forecasts before the run

1. A 20% Russian share should improve Russian bytes/token by at least 20% relative to v1 while reducing Kyrgyz bytes/token by less than 10%.
2. The GigaChat case-aware pre-tokenizer should help Russian capitalization and punctuation without a material Kyrgyz penalty.
3. Moving from 40K to 50K should produce less than a 5% balanced compression gain and therefore lose on embedding-table cost for a future small model.
4. If no candidate meets the Kyrgyz-retention constraint, the bilingual tokenizer direction is not ready and v1 remains the release.

## Selection rule

A candidate is eligible only if it has zero round-trip failures and external Kyrgyz bytes/token is at least 90% of v1. Among eligible candidates, discard Pareto-dominated points over Kyrgyz compression, Russian compression, and vocabulary size. Select the smallest remaining vocabulary at the knee of the bilingual compression curve; do not collapse the decision into an undocumented weighted score.

## Failure reading

Inspect raw tokenizations for the largest regressions in each bucket: Kyrgyz suffix-heavy words, Russian inflections, uppercase text, punctuation, numbers, and genuine mixed-language records. A global average is not sufficient evidence.

## Rust decision

The current Python package calls Hugging Face Tokenizers, whose core is already implemented in Rust. The complete 518.5 MB v1 merge run took 20.5 seconds. A separate Rust rewrite is rejected unless profiling shows a material bottleneck in the experiment or encode path; implementation language is not a quality feature.
