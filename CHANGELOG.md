# Changelog

All notable repository checkpoints are recorded here. Research decisions and measured evidence remain in `docs/decisions/` and `docs/reports/`.

## 0.2.0 — 2026-08-29

- Built a deterministic 160 MiB Russian FineWeb2 supplement without changing Kyrgyz corpus v1.
- Evaluated 24 controlled Kyrgyz-Russian byte-level BPE candidates across corpus ratio, pre-tokenizer, and vocabulary size.
- Released `kyrgyz-russian-byte-bpe-v2`, a 32K tokenizer trained with 10% Russian bytes and GigaChat-style category boundaries.
- Recorded a 35.33% bytes/token gain on external Russian data with a 0.75% Kyrgyz reduction relative to v1.
- Added real held-out mixed-language diagnostics, release metadata, model cards, architecture, citation, contribution, security, and publication guidance.

## 0.1.0 — 2026-08-29

- Built the reproducible Kyrgyz corpus v1 from pinned web, Wikipedia, news, and literary sources.
- Added cleaning, language identification, exact and near deduplication, deterministic splitting, provenance, and aggregate audit reports.
- Released the 32K Kyrgyz-only byte-level BPE v1 baseline after nested vocabulary evaluation.
