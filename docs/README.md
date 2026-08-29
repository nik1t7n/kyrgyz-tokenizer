# Documentation

This directory is the durable record of how the corpus and tokenizer are built.

- `IMPLEMENTATION_PLAN.md` describes the current executable plan.
- `ARCHITECTURE.md` describes module ownership, data flow, and the stable tokenizer/LLM boundary.
- `PUBLIC_RELEASE.md` records what can be published, what stays local, and the rights boundary.
- `SOURCE_REGISTRY.md` records source identity, version, provenance, license, and inclusion status.
- `research/` contains evidence gathered from published corpus projects.
- `decisions/` contains dated decisions and trade-offs. A decision is changed by adding a new entry or explicitly superseding the old one, not by silently rewriting history.
- `reports/` contains tracked aggregate build and audit reports, never licensed corpus text.

## Decision log

- [0001: corpus v1 scope](decisions/0001-corpus-v1.md)
- [0002: official Wikipedia dump](decisions/0002-official-wikipedia-dump.md)
- [0003: deterministic long-document chunking](decisions/0003-document-chunking.md)
- [0004: Wikipedia structural cleanup](decisions/0004-wikipedia-structural-cleanup.md)
- [0005: minimum document length](decisions/0005-minimum-document-length.md)
- [0006: tokenizer architecture](decisions/0006-tokenizer-architecture.md)
- [0007: select the 32K release vocabulary](decisions/0007-tokenizer-vocabulary.md)
- [0008: optimize v2 for Kyrgyz-Russian use](decisions/0008-bilingual-tokenizer-scope.md)
- [0009: release the 32K 10%-Russian v2 candidate](decisions/0009-tokenizer-v2-selection.md)

## Reports

- [Final build report](reports/CORPUS_V1_BUILD_REPORT.md)
- [Quality audit](reports/CORPUS_V1_QUALITY_AUDIT.md)
- [Tokenizer v1 evaluation](reports/TOKENIZER_V1_EVALUATION.md)
- [Russian supplement corpus v1 build report](reports/CORPUS_RU_V1_BUILD_REPORT.md)
- [Kyrgyz-Russian tokenizer v2 evaluation](reports/TOKENIZER_V2_EVALUATION.md)
