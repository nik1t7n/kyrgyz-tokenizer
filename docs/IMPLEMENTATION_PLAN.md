# Kyrgyz Corpus Implementation Plan

Last updated: 2026-08-29

## Goal

Produce a provenance-preserving, globally deduplicated, quality-audited Kyrgyz corpus for tokenizer experiments. The build must be resumable and deterministic from pinned source revisions and configuration.

## Output contract

Local generated artifacts:

```text
data/
  raw/                 downloaded archives that cannot be streamed
  interim/             SQLite staging database with normalized documents
  processed/
    corpus-v1/         deterministic train and validation JSONL/text shards
artifacts/
  manifests/           source revisions and downloaded checksums
  reports/             counts, bytes, rejection reasons, source distribution
  audit/               bounded random accepted/rejected samples
```

Git-tracked outputs contain aggregate statistics and bounded audit material only. Corpus text remains ignored.

## Pipeline

### Phase 1: source acquisition

1. Resolve and record the immutable Hugging Face revision for every Hub dataset.
2. Stream large Hub sources and select only required columns.
3. Download the official Wikimedia `kywiki` pages/articles dump and record its published checksum.
   Remove templates, formatting markup, media captions, category links, references, and conventional trailing link/source sections while retaining visible article prose and ordinary link text.
4. Download Manas-UdS from its official CLARIN URL and verify the published SHA-1 checksum.
5. Store source and license metadata before any transformation.

### Phase 2: normalization and structural checks

1. Decode valid UTF-8 and normalize to NFC.
2. Remove control characters; normalize horizontal whitespace; retain paragraph boundaries.
3. Split over-limit source records deterministically at paragraph, line, or sentence boundaries without overlap; preserve the parent ID and chunk coordinates.
4. Reject empty, extremely short, malformed, HTML-heavy, URL-heavy, and high-symbol-ratio documents.
5. Detect repeated lines, repeated word n-grams, and abnormally compressible template spam.
6. Redact e-mail addresses and IPv4 addresses while preserving surrounding natural text. Phone-like strings are retained in v1 because a broad rule would also destroy legitimate dates, identifiers, and numeric language examples; stronger PII handling remains a future audited stage.

### Phase 3: language and script filtering

1. Pin and load `cis-lmu/glotlid/model_v3.bin`.
2. Require top language label `kir_Cyrl` for sufficiently long non-FineWeb documents.
3. Start at score `0.756`, matching FineWeb2's published Kyrgyz configuration.
4. Keep score, top competing labels, Cyrillic ratio, Latin ratio, and Kyrgyz-specific-character count in audit metadata.
5. Calibrate the final threshold using a deterministic random audit sample; never tune silently against desired corpus size.

### Phase 4: deduplication

1. Compute SHA-256 from normalized text and remove exact duplicates globally.
2. Compute MinHash signatures from 5-word shingles.
3. Cluster documents at approximately 0.75 Jaccard similarity and retain one representative using a deterministic preference order: stronger provenance, higher LID score, longer useful text, stable document ID.
4. Record duplicate cluster size and retained source.

### Phase 5: mixture and split

1. Measure clean unique bytes by source and document-length bucket.
2. Create a deterministic source-capped mixture close to 500 MiB without duplicating documents.
3. Split after deduplication using the normalized-text hash: 99% train, 1% validation.
4. Write compressed sharded JSONL with document and provenance fields, plus plain UTF-8 text shards for future tokenizer training.

### Phase 6: quality report

Report at minimum:

- raw, normalized, accepted, exact-duplicate, near-duplicate, and final document/byte counts;
- rejection counts by reason and source;
- language-score and script-profile distributions;
- source and domain mixture;
- document length percentiles;
- character inventory and Unicode normalization statistics;
- deterministic accepted/rejected audit samples;
- build configuration, dependency lock, source revisions, file hashes, and Git commit.

## Acceptance gate for corpus v1

Corpus v1 is ready for tokenizer work only when:

1. all selected sources were processed through the real path;
2. every output document has provenance and license metadata;
3. exact and cross-source near-deduplication completed;
4. a manual random audit has quantified language purity and common rejection mistakes;
5. the final manifest and report reproduce the observed counts;
6. a clean checkout can run the documented command and resume from existing checkpoints.
