# Kyrgyz Tokenizer

Research repository for building a transparent, reproducible Kyrgyz text corpus and training a tokenizer from first principles.

The repository stores code, manifests, provenance, and quality reports. Downloaded source text and generated corpus artifacts stay local and are excluded from Git because the upstream sources have different licenses and the corpus is large.

## Documentation

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Source registry](docs/SOURCE_REGISTRY.md)
- [Research: corpus construction practices](docs/research/CORPUS_PRACTICES.md)
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

## Status

Corpus pipeline v1 is implemented and has completed a real end-to-end build. The tracked report records the observed corpus composition and the remaining quality limitations. Tokenizer training is the next project stage.
