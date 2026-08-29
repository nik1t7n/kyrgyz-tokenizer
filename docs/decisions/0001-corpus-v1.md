# Decision 0001: Corpus v1 scope and trust boundaries

Date: 2026-08-29
Status: accepted

## Context

The first corpus must be good enough to compare tokenizer algorithms while remaining reproducible on a local workstation. It does not need to be large enough to pre-train a frontier language model. Raw source datasets have different licenses and contain web-derived text that should not be silently republished.

## Decisions

1. The first tokenizer mixture targets approximately 500 MiB of clean UTF-8 text after global deduplication. The pipeline also retains the larger clean unique pool when disk permits.
2. Version 1 uses four real source families: FineWeb2 `kir_Cyrl`, cleaned Kyrgyz Wikipedia, Kyrgyz News Corpus, and Manas-UdS literature/proverbs/news.
3. The repository stores code, configuration, source revisions, aggregate reports, and checksums. It does not commit or push raw or processed documents.
4. Every output document retains source, upstream identifier or URL where available, upstream revision, license label, and transformation metadata.
5. Text is normalized to Unicode NFC; invalid/control characters and technical whitespace artifacts are removed. Case, punctuation, digits, paragraph boundaries, spelling variation, and code-switching that survives language checks are preserved.
6. No machine translation, generated text, spelling correction, lowercasing, transliteration, or rare-character deletion is allowed in corpus v1.
7. GlotLID V3 is pinned for language identification. FineWeb2's `0.756` Kyrgyz threshold is the initial threshold, subject to a documented native-speaker audit rather than silent tuning.
8. Exact deduplication uses SHA-256 of normalized text. Near deduplication uses MinHash over 5-word shingles across all included sources.
9. Dominant sources are downsampled deterministically. Smaller high-value sources are not duplicated to meet a target ratio.
10. A stable hash split is created only after global deduplication, preventing near-identical documents from leaking into both train and validation.

## Trade-offs

- A 500 MiB mixture is much smaller than modern LLM corpora but large enough for stable tokenizer frequency estimates and practical local iteration.
- NFC changes the byte representation of canonically equivalent Unicode sequences. It reduces accidental vocabulary fragmentation, while the future byte-level tokenizer itself will remain capable of encoding arbitrary unnormalized UTF-8.
- Strict Kyrgyz LID improves purity but can discard legitimate mixed Kyrgyz/Russian text. Mixed-language documents are therefore measured and sampled for audit instead of being removed solely because Russian characters occur.
- Combining CC BY-SA, CC BY-NC, CC BY-NC-SA, and ODC-By sources creates redistribution obligations. Keeping texts local and preserving per-document provenance avoids pretending that a private GitHub repository grants new rights.
- Existing corpora reduce crawling work but may overlap. Global cross-source near-deduplication is therefore mandatory.

## Rejected alternatives

- A fresh crawl of the entire Kyrgyz web for v1: duplicates existing Common Crawl coverage and adds major extraction, robots, privacy, and licensing risk before tokenizer research can begin.
- News-only training: gives misleading merge frequencies dominated by political and administrative language.
- Requiring a Kyrgyz-specific character in every document: rejects valid Kyrgyz passages that happen not to contain `ң`, `ө`, or `ү`.
- Exact deduplication only: fails on syndicated news and pages with small boilerplate edits.
- LLM-generated quality scoring in v1: no validated Kyrgyz preference dataset exists yet, so the score would add opaque bias rather than demonstrated quality.
