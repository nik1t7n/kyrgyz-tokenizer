# Decision 0005: Lower the minimum document length to 100 characters

Date: 2026-08-29

## Context

The first structurally clean full build used a 200-character minimum. Its deterministic rejected-sample audit contained 31 source/reason buckets. Reviewing up to two records from every bucket, 59 records in total, showed that short-document rejection systematically removed valid Kyrgyz dictionary definitions, encyclopedia stubs, and concise news text. This is a larger loss for tokenizer vocabulary coverage than for language-model pretraining.

## Decision

Lower the minimum normalized document length from 200 to 100 Unicode characters. Keep the existing script-ratio, GlotLID, repetition, URL, HTML, symbol, and exact/near-duplicate checks unchanged.

## Tradeoffs

- The corpus retains more rare terms and concise grammatical contexts, which are useful to a tokenizer.
- Some headline-like fragments and low-context snippets will also pass. Language and structural filters reduce but do not eliminate this risk.
- The change is based on observed false positives rather than a desired byte target. The output mixture remains capped independently at approximately 500 MiB.
- Text shorter than 100 characters remains excluded because the current language and quality decisions are less reliable on very small fragments.
