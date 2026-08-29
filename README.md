# Kyrgyz Tokenizer

Research repository for building a transparent, reproducible Kyrgyz text corpus and training a tokenizer from first principles.

The repository stores code, manifests, provenance, and quality reports. Downloaded source text and generated corpus artifacts stay local and are excluded from Git because the upstream sources have different licenses and the corpus is large.

## Documentation

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Source registry](docs/SOURCE_REGISTRY.md)
- [Research: corpus construction practices](docs/research/CORPUS_PRACTICES.md)
- [Research: tokenizer design practices](docs/research/TOKENIZER_PRACTICES.md)
- [Tokenizer v1 evaluation](docs/reports/TOKENIZER_V1_EVALUATION.md)
- [Kyrgyz-Russian tokenizer v2 experiment plan](docs/experiments/TOKENIZER_V2_PLAN.md)
- [Russian supplement corpus report](docs/reports/CORPUS_RU_V1_BUILD_REPORT.md)
- [Kyrgyz-Russian tokenizer v2 evaluation](docs/reports/TOKENIZER_V2_EVALUATION.md)
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

The v1 workflow trains one 50K byte-level BPE merge sequence, derives nested 8K/16K/32K variants, prepares pinned external Kyrgyz benchmarks, and compares every variant with accessible published tokenizers.

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

The v2 workflow builds a separate deterministic Russian supplement and compares 24 controlled Kyrgyz-Russian candidates across corpus ratio, pre-tokenizer, and vocabulary size:

```bash
uv run kyrgyz-corpus build --config configs/corpus-ru-v1.yaml --reset
uv run kyrgyz-tokenizer v2-build --config configs/tokenizer-v2.yaml --reset
```

The selected bilingual 32K release is tracked at `models/kyrgyz-russian-byte-bpe-v2/tokenizer.json`. It uses 90% Kyrgyz and 10% Russian training bytes. External Kyrgyz compression is 0.75% below v1 while Russian compression improves by 35.33%; every evaluated record round-trips exactly.

## Status

Corpus pipeline v1, the Russian supplement, tokenizer v1, and the controlled Kyrgyz-Russian tokenizer v2 experiment are complete. V2 is the current candidate for future small bilingual-model work. Intrinsic tokenizer metrics do not establish downstream model quality; a matched language-model experiment remains optional future research rather than a prerequisite for using or studying the tokenizer artifact.
