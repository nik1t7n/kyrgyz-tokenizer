# Russian supplement corpus v1 build report

Date: 2026-08-29

## Purpose

This is a bounded Russian supplement for controlled Kyrgyz-Russian tokenizer experiments. It is not a standalone claim of comprehensive Russian coverage and it does not change the Kyrgyz corpus v1. The source is the globally filtered and deduplicated FineWeb2 `rus_Cyrl` subset, pinned at revision `af9c13333eb981300149d5ca60a8e9d659b276b9`.

The stream was approximately shuffled with seed `20260829` and buffer size 10,000 before applying the byte cap. This avoids taking one contiguous source prefix while keeping the build deterministic at the pinned dataset revision.

## Result

| Stage | Documents | UTF-8 bytes |
| --- | ---: | ---: |
| Accepted pool before export cap | 19,437 | 209,723,226 |
| Exported total | 15,388 | 167,771,682 |
| Train | 15,216 | 165,723,290 |
| Validation | 172 | 2,048,392 |

All exported records retain source, license, language, quality, transformation, and text-hash metadata. The final train/validation split is hash-based and is performed after filtering and deduplication.

## Filtering evidence

The real collection path rejected 83 high-Latin records, 80 low-Cyrillic records, 24 HTML-heavy records, 53 repeated-line records, 14 repeated-ngram records, and 35 URL-dense records. It redacted 298 e-mail addresses and 189 IPv4 addresses. No near-duplicate was found in the bounded accepted pool, which is consistent with FineWeb2 already applying global MinHash deduplication.

The retained language-identification score had minimum `0.902` and median `0.999`; all documents were NFC-normalized. A deterministic manual audit covered 20 accepted records. All were Russian-dominant. Several still contained ordinary web-corpus defects such as promotional wording, minor spelling mistakes, or residual page furniture. These are a known quality limit, not evidence of a language-selection failure.

## Reproducibility

Config SHA-256: `97f9830ac455c93c86bc1e8a2ec3365f785ebb8258774ead53d7ca82ae18d633`.

| Split | Format | SHA-256 |
| --- | --- | --- |
| train-00000 | JSONL | `bbedf5c2236352ca9599a8ca728f8ff28934e83871bdf4c8a5dc8a31efb82cb8` |
| train-00001 | JSONL | `048e84456eeb905078c942cc92c399902d1068fd082c6fbe065783eb85a3b077` |
| train-00002 | JSONL | `f9fdc5167959b460c9458f046cf18ac244b8e01204ca5f2b457f4a0c4f2ab0f0` |
| validation-00000 | JSONL | `647fd0fbccf58cb9d4b4b60fe97e3c4ee3f3298229133e29aa62e140dde68153` |

The full generated build report and source lock remain under `artifacts/corpus-ru-v1/`; the licensed corpus text remains ignored by Git.

## Readiness boundary

This supplement is fit for the documented tokenizer mixture experiment. It is not sufficient by itself for language-model pretraining, and its Common Crawl provenance requires a separate license and content-risk review before any commercial redistribution or broader downstream use.
