# Decision 0008: Optimize v2 for Kyrgyz-Russian use

Date: 2026-08-29

## Context

Kyrgyz tokenizer v1 is efficient on Kyrgyz but weak on Russian. A practical tokenizer for the Kyrgyz market must handle both languages because real local documents and conversations commonly use them together. Broad multilingual and code coverage would consume scarce vocabulary entries without evidence that it is the primary product need.

## Decision

Treat Kyrgyz and Russian as the v2 optimization languages. Preserve the complete Kyrgyz corpus v1 and add a separately versioned, quality-filtered Russian supplement. Hold total training bytes constant while varying the Russian share. Measure code only as a robustness diagnostic; do not add a code corpus or let code determine the selected tokenizer.

Derive a mixed-language diagnostic from real held-out documents. Do not manufacture code-switched examples to make the benchmark look broader than the available evidence.

## Tradeoffs

- This scope directly targets local language use and keeps a small vocabulary viable.
- English and code are still byte-safe but intentionally under-optimized.
- The available mixed held-out set is publication-style and does not establish chat performance.
- Any future expansion to more languages or domains requires a new corpus-mixture experiment rather than silently changing v2.
