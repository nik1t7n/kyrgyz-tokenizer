# Kyrgyz Tokenizer

Research repository for building a transparent, reproducible Kyrgyz text corpus and training a tokenizer from first principles.

The repository stores code, manifests, provenance, and quality reports. Downloaded source text and generated corpus artifacts stay local and are excluded from Git because the upstream sources have different licenses and the corpus is large.

## Documentation

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Source registry](docs/SOURCE_REGISTRY.md)
- [Research: corpus construction practices](docs/research/CORPUS_PRACTICES.md)
- [Research: tokenizer design practices](docs/research/TOKENIZER_PRACTICES.md)
- [Tokenizer v1 evaluation](docs/reports/TOKENIZER_V1_EVALUATION.md)
- [Decision log](docs/README.md)

## Build the corpus

Requirements: `uv`, network access to the pinned upstream sources, about 4 GiB of free disk space, and a machine that can load the GlotLID V3 model.

```bash
uv sync
uv run kyrgyz-corpus build --reset
```

`--reset` removes only generated database, report, and processed-output paths inside this repository. Downloaded source archives and model files are retained and checksum-verified for reuse.

For a bounded real-source smoke run:

```bash
uv run kyrgyz-corpus build --reset --max-docs 10
```

Pipeline stages can also run separately and resume from the SQLite state:

```bash
uv run kyrgyz-corpus collect
uv run kyrgyz-corpus dedup
uv run kyrgyz-corpus export
uv run kyrgyz-corpus report
```

## Outputs

- `data/processed/corpus-v1/*.txt.zst`: plain UTF-8 text for future tokenizer training;
- `data/processed/corpus-v1/*.jsonl.zst`: the same documents with provenance, license, language, quality, and transformation metadata;
- `artifacts/corpus-v1/reports/`: machine-readable and Markdown build reports;
- `artifacts/corpus-v1/manifests/`: pinned upstream identities and downloaded checksums;
- `artifacts/corpus-v1/audit/`: deterministic accepted and rejected samples for manual review.

Raw and processed text is intentionally not pushed. The source mixture includes non-commercial licenses, so the generated composite must not be redistributed or used commercially without a separate license review.

## Train and evaluate the tokenizer

The tokenizer workflow trains one 50K byte-level BPE merge sequence, derives nested 8K/16K/32K variants, prepares pinned external Kyrgyz benchmarks, and compares every variant with accessible published tokenizers.

```bash
uv run kyrgyz-tokenizer build --reset
```

The selected 32K release is tracked at `models/kyrgyz-byte-bpe-v1/tokenizer.json`. It has no normalizer and no protocol-specific special tokens.

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_file("models/kyrgyz-byte-bpe-v1/tokenizer.json")
encoding = tokenizer.encode("Кыргызстандын келечеги кыргыз тилинде сүйлөйт.")
assert tokenizer.decode(encoding.ids) == "Кыргызстандын келечеги кыргыз тилинде сүйлөйт."
```

## Status

Corpus pipeline v1 and tokenizer v1 are implemented. The 32K tokenizer was trained on the complete real corpus, evaluated on held-out and external Kyrgyz data, and compared with DeepSeek-V3, Qwen2.5, and two OpenAI encodings. The next research gate is a controlled small-language-model experiment; intrinsic tokenizer metrics alone do not establish downstream quality.
