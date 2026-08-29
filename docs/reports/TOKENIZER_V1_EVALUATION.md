# Tokenizer v1 evaluation

Date: 2026-08-29

Configuration SHA-256: `caec6499d11759f2e54c7bc8fe85bee2504b3b6cf09ea51e7246a9cc39b2e4bd`

Released artifact: `models/kyrgyz-byte-bpe-v1/tokenizer.json`

Artifact SHA-256: `5047b4f427bb1af1c06cfb9cefbe83790b56df409b137b887988db6eba4b159f`

## Outcome

The primary release is a 32,768-entry category-aware ByteLevel-BPE tokenizer. It has a complete 256-byte base alphabet, 32,512 learned merges, no unknown token, no normalizer, and no special tokens. The final reproducibility run trained the 50K parent merge sequence on 518,527,574 UTF-8 bytes in 20.5 seconds on the current machine; the 8K, 16K, and 32K variants were derived as exact merge-history prefixes.

Across 12,601 untouched corpus-validation records and 2,489 external records, every evaluated tokenizer completed exact encode/decode round trips. The released tokenizer had zero failures across all 15,090 records.

## External Kyrgyz benchmark

External evaluation combines pinned test data from UD-KTMU, UD-TueCL, Belebele, and SIB-200. It contains 1,331,087 UTF-8 bytes and 90,519 Unicode word matches.

| Tokenizer | Vocabulary | Bytes/token | Sequence fertility | Isolated one-token words | Heuristic suffix-boundary recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kyrgyz BPE 50K | 50,000 | 9.521 | 1.544 | 36.45% | 31.78% |
| **Kyrgyz BPE 32K** | **32,768** | **8.983** | **1.637** | **30.36%** | **34.14%** |
| Kyrgyz BPE 16K | 16,384 | 8.088 | 1.818 | 18.92% | 40.14% |
| Kyrgyz BPE 8K | 8,192 | 7.153 | 2.056 | 11.83% | 43.98% |
| OpenAI `o200k_base` | 200,019 | 5.480 | 2.684 | 8.50% | 62.79% |
| DeepSeek-V3 | 128,000 | 3.530 | 4.166 | 4.37% | 72.85% |
| Qwen2.5 | 151,643 | 3.261 | 4.510 | 4.12% | 71.27% |
| OpenAI `cl100k_base` | 100,277 | 2.601 | 5.654 | 2.60% | 76.72% |

Higher bytes/token and lower fertility mean shorter token sequences. On this external Kyrgyz set, the 32K release produces approximately 61% fewer tokens than DeepSeek-V3, 64% fewer than Qwen2.5, 71% fewer than `cl100k_base`, and 39% fewer than `o200k_base`.

## Per-domain compression

| Tokenizer | Corpus validation | UD-KTMU | UD-TueCL | Belebele | SIB-200 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kyrgyz BPE 50K | 9.010 | 10.108 | 7.901 | 9.466 | 9.664 |
| **Kyrgyz BPE 32K** | **8.597** | **9.648** | **7.602** | **8.914** | **9.162** |
| Kyrgyz BPE 16K | 7.809 | 8.693 | 7.064 | 8.022 | 8.255 |
| Kyrgyz BPE 8K | 6.912 | 7.635 | 6.207 | 7.100 | 7.307 |
| OpenAI `o200k_base` | 5.359 | 5.430 | 4.974 | 5.487 | 5.590 |
| DeepSeek-V3 | 3.540 | 3.472 | 3.432 | 3.536 | 3.576 |
| Qwen2.5 | 3.252 | 3.202 | 3.169 | 3.268 | 3.283 |
| OpenAI `cl100k_base` | 2.658 | 2.607 | 2.626 | 2.599 | 2.623 |

Values are UTF-8 bytes per token. The dedicated tokenizer advantage persists in every tested domain. The benchmark sources are not pinned corpus-v1 inputs, but a full substring-level decontamination against the web corpus has not been performed, so the external rows must not be described as contamination-free.

## Why 32K won

Moving from 32K to 50K improves external bytes/token by 6.0% and reduces sequence fertility by 5.7%, but expands the vocabulary and embedding table by 52.6%. At model width 768, the token embedding grows from 25,165,824 to 38,400,000 parameters. This is a poor exchange for a future small or medium Kyrgyz model.

Moving from 16K to 32K costs another 12.6M embedding parameters at width 768, but lowers external sequence fertility from 1.818 to 1.637 and raises isolated one-token word coverage from 18.92% to 30.36%. The 32K point is therefore the practical knee of the measured curve.

## Morphology diagnostic

The UD morphology check contains 5,885 eligible inflected tokens whose surface form case-insensitively begins with the annotated lemma. It asks whether the tokenizer places a boundary at that lemma/suffix transition.

Smaller vocabularies score higher because they create more boundaries everywhere; larger vocabularies frequently store a complete inflected word as one token. The score must not be read as “8K understands morphology better.” Published controlled work shows that morphological alignment alone is not a reliable predictor of downstream model performance. The report therefore uses it as a fragmentation diagnostic, not the selection objective.

## Baseline provenance and blockers

- DeepSeek-V3 is pinned to revision `e815299b0bcbac849fa540c768ef21845365c9eb`.
- Qwen2.5-7B is pinned to revision `d149729398750b98c0af14eb82c78cfe92750796`.
- OpenAI `cl100k_base` and `o200k_base` are loaded through the official `tiktoken` package with upstream artifact hashes pinned in the configuration.
- Direct Llama 3.2 and Gemma 3 evaluation was attempted. Both official Hugging Face repositories returned `401 GatedRepoError` because this machine has not accepted their access terms. No mirror or substitute tokenizer was used.

## What remains unproven

This evaluation proves lossless encoding and strong intrinsic Kyrgyz sequence efficiency. It does not prove that a language model trained with this tokenizer will outperform one trained with another tokenizer. That requires a controlled extrinsic experiment with the same model, data, token budget, optimizer, and evaluation tasks.
