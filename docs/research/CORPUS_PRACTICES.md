# Corpus Construction Practices

Last updated: 2026-08-29

## Research question

Which practices from well-documented English/multilingual, Chinese, Russian, and Kazakh pre-training corpora should govern a reproducible Kyrgyz corpus intended for tokenizer research?

The useful comparison unit is not raw size alone. For each project we track source diversity, language identification, normalization, quality filtering, exact and fuzzy deduplication, domain balancing, provenance, licensing, and evaluation.

## Evidence reviewed

| Project | Scale reported by authors | High-signal practices | Limits relevant to us |
| --- | ---: | --- | --- |
| [FineWeb](https://arxiv.org/html/2406.17557) | 15T tokens from 96 Common Crawl snapshots | URL filtering, Trafilatura extraction, language identification, repetition and quality rules, MinHash deduplication, PII reformatting, ablation-driven filter selection | English thresholds do not transfer directly to Kyrgyz |
| [FineWeb2](https://arxiv.org/html/2506.20920) | 20 TB, 5B documents, 1,000+ languages | GlotLID language+script labels, per-language confidence thresholds, global-per-language MinHash, language-adaptive quality thresholds, retained cluster-size metadata | Automated LID and thresholds remain imperfect for low-resource languages |
| [DataComp-LM](https://arxiv.org/html/2406.11794) | 240T-token candidate pool | Controlled comparisons, fixed downstream evaluations, global exact/fuzzy dedup, model-based quality scoring | Model-based quality filters need trustworthy positive and negative data that Kyrgyz does not yet have |
| [ChineseWebText 2.0](https://github.com/CASIA-LM/ChineseWebText-2.0) | 6.6 TB raw to 3.8 TB cleaned | Reject bad sources after manual sampling, length and character-profile rules, internal repetition filtering, document quality scores, domain and toxicity labels | Chinese-specific character rules and BERT scorers cannot be copied directly |
| [SkyPile-150B](https://arxiv.org/html/2310.19341) | 150B released tokens, about 620 GB | Structural extraction, semantic distribution filtering, deduplication, CCNet-style quality classification, bounded upsampling of selected high-quality domains | Most detailed thresholds and the complete 6T-token corpus are not public |
| [YaLM-100B](https://github.com/yandex/YaLM-100B/blob/main/README.md) | 1.7 TB training mix; Russian web filtered from roughly 100 TB to 1 TB | LSH deduplication, length and entropy filters, repetitive-domain removal, WebText-style classifier, explicit source mixture | Training corpus and exact pipeline are not reproducible from the repository |
| [SozKZ](https://arxiv.org/html/2603.20854) | about 9B Kazakh tokens | Dedicated language corpus and tokenizer, multiple public sources, domain-aware construction, open scripts and artifacts | Documentation spans several evolving dataset versions and must be checked against code |
| [SozKZ deduplicated web corpus](https://huggingface.co/datasets/stukenov/sozkz-corpus-dedup-kk-web-v1) | 9,475,089 unique texts, 31.7 GB | Six public sources, NFC, control/whitespace cleanup, URL/HTML rules, exact MD5 dedup against 12.4M reference texts, source labels | This particular artifact uses exact dedup only; exact hashing does not remove syndicated and lightly edited copies |

## Convergent practices

The strongest projects converge on the following sequence:

1. Preserve document boundaries and provenance before transforming text.
2. Normalize only encoding and technical artifacts; do not erase useful linguistic variation.
3. Identify language and script using a model, then calibrate thresholds per language rather than copying an English threshold.
4. Apply interpretable heuristic filters and record every rejection reason.
5. Remove exact duplicates and near-duplicates globally, not only inside each source.
6. Prevent one source or domain from dominating the frequency distribution.
7. Keep a held-out split and evaluate pipeline decisions instead of assuming that more filtering is always better.
8. Version source revisions, configuration, code commit, model artifacts, and output manifests so a build is reproducible.

## Kyrgyz-specific evidence

FineWeb2 publishes a dedicated `kir_Cyrl` configuration. The filtered subset contains approximately 397M words in 1.07M documents and 4.36 GB of UTF-8 text. Its current configuration uses a GlotLID language confidence threshold of `0.756`, a maximum average word length of `12`, minimum average word length of `4`, and Kyrgyz-specific stopwords and repetition thresholds.

This is a stronger starting point than a fresh uncontrolled crawl because it already covers 96 Common Crawl snapshots, performs global per-language MinHash deduplication, and retains source URLs and language scores. It is not treated as ground truth: bounded native-speaker audit and cross-source deduplication are still required.

## Implications for this repository

- Start from real public corpora rather than recrawling the same web immediately.
- Use FineWeb2 as broad web coverage, not as the entire language distribution.
- Add encyclopedia, news, and literature as separately labelled domains.
- Do not use synthetic or translated text for tokenizer corpus v1; it would distort naturally occurring byte and subword frequencies.
- Use GlotLID V3 with a pinned model file and begin from FineWeb2's `0.756` Kyrgyz threshold, then calibrate against a manual audit sample.
- Apply SHA-256 exact deduplication and 5-word-shingle MinHash near-deduplication across all sources.
- Keep the full clean unique pool, then create a deterministic capped mixture for tokenizer training without duplicative upsampling.

## Source-quality notes

- FineWeb/FineWeb2 and DataComp-LM provide code, ablations, artifacts, and measured downstream comparisons; they are the strongest methodological evidence.
- ChineseWebText and SkyPile are practitioner-built and publish substantial details, but some thresholds or full source data remain unavailable.
- YaLM documents a useful production-scale mixture and filtering outline, but does not release the actual corpus pipeline.
- SozKZ is the closest language analogue and publishes working code and datasets. Its evolving artifacts must be cited by exact version because the exact-dedup web corpus and the deeper clean-pretrain pipeline are not the same dataset.
