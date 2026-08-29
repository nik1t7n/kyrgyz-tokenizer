# Decision 0003: Preserve long documents through deterministic chunking

Date: 2026-08-29

## Context

The first real Manas-UdS smoke run exposed book-length source records. Three of the first twenty records exceeded the configured 200,000-character processing limit. Truncating those records preserved only their beginnings and discarded most of the source text, which is unacceptable for a tokenizer-training corpus.

## Decision

Before normalization and filtering, split every over-limit record into non-overlapping chunks of at most 200,000 characters. Prefer the latest paragraph, line, or sentence boundary in the second half of the candidate chunk; use a hard boundary only when no suitable structural boundary exists. Preserve the parent source ID, URL, metadata, chunk index, and chunk count on every generated record.

## Tradeoffs

- Non-overlapping chunks retain all source text and do not inflate token frequencies through overlap.
- Boundary-aware splitting preserves local prose structure better than hard truncation.
- A chunk is no longer equivalent to an upstream document, so provenance explicitly records both IDs.
- Language identification and quality filters run per chunk. This can remove a bad section without discarding an otherwise useful book, but it also changes rejection counts from document-level to chunk-level counts.
- The 200,000-character limit is operational, not linguistic. It bounds memory and per-record processing time and can be recalibrated from later build evidence.
