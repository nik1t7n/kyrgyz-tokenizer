# Repository architecture

## Scope

The repository has two bounded systems:

1. a provenance-preserving corpus pipeline;
2. a byte-level BPE training and evaluation pipeline.

It does not contain a language model, inference server, chat format, or model-specific special tokens. Those belong to the next research phase and should not be mixed into this tokenizer checkpoint.

## Data flow

```text
pinned upstream sources
        │
        ▼
collection → cleaning/LID → exact + near deduplication → deterministic split
        │                                                   │
        │                                                   ├─ validation shards
        │                                                   └─ training shards
        │                                                            │
        └─ source locks, audits, aggregate reports                    ▼
                                                      controlled BPE training matrix
                                                                    │
                                                                    ▼
                                              held-out + external evaluation
                                                                    │
                                                                    ▼
                                                constrained candidate selection
                                                                    │
                                                                    ▼
                                      tracked tokenizer + metadata + model card
```

Corpus records retain their upstream identifier, URL when available, source ID, license, text hash, language score, quality metrics, and transformations. Generated text stays local; Git contains only code, configuration, aggregate evidence, and the selected tokenizer artifacts.

## Source packages

### `src/kyrgyz_corpus`

| Module | Responsibility |
| --- | --- |
| `sources.py` | Open pinned real sources and write immutable source locks. |
| `cleaning.py` | Normalize UTF-8/NFC text, apply structural filters, and redact bounded PII patterns. |
| `lid.py` | Run the pinned GlotLID model and retain scores. |
| `store.py` | Persist normalized records and deduplication state in SQLite. |
| `dedup.py` | Apply exact SHA-256 and MinHash near-deduplication. |
| `pipeline.py` | Coordinate collection, filtering, deduplication, mixture, split, and export. |
| `reporting.py` | Produce manifests, deterministic audits, and aggregate build reports. |
| `cli.py` | Expose resumable corpus commands. |

### `src/kyrgyz_tokenizer`

| Module | Responsibility |
| --- | --- |
| `pretokenizer.py` | Define the pinned DeepSeek- and GigaChat-style category boundaries before byte BPE. |
| `training.py` | Train the v1 merge history and derive nested vocabulary variants. |
| `v2.py` | Build controlled Kyrgyz-Russian mixtures, train the v2 matrix, apply the published selection rule, and package the release. |
| `benchmarks.py` | Prepare pinned held-out, external, code, and real mixed-language evaluation inputs. |
| `evaluation.py` | Measure compression, fertility, morphology diagnostics, and exact round trips. |
| `release.py` | Package the v1 release. |
| `reporting.py` | Render v1 evaluation evidence. |
| `cli.py` | Expose training, evaluation, inspection, and packaging commands. |

The orchestration is Python, while Hugging Face Tokenizers executes BPE training, pre-tokenization, encoding, and decoding in its Rust core. A separate Rust rewrite was rejected because it would not change the learned vocabulary and no relevant performance bottleneck was measured.

## Repository layout

```text
configs/       pinned corpus and tokenizer experiment definitions
docs/
  decisions/   append-only decisions and trade-offs
  experiments/ preregistered hypotheses and selection rules
  reports/     tracked aggregate results and audit conclusions
  research/    primary-source review behind the implementation
models/        selected tokenizer artifacts, metadata, and model cards
src/           corpus and tokenizer packages
data/          ignored downloaded/generated text and benchmarks
artifacts/     ignored manifests, candidate models, and raw experiment reports
```

`models/kyrgyz-byte-bpe-v1` is the historical Kyrgyz-only baseline. `models/kyrgyz-russian-byte-bpe-v2` is the current release candidate for a future small bilingual model.

## Stable boundary before LLM work

The tokenizer phase is frozen at v2. A downstream LLM experiment should consume the tracked v2 `tokenizer.json` by hash and add its own protocol tokens without retraining or silently modifying the tokenizer. Any later tokenizer change must become a new version with a new corpus/config hash and a new decision record.
