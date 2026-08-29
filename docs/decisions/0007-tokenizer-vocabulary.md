# Decision 0007: Release the 32K vocabulary

Date: 2026-08-29

## Context

The same 50K BPE merge history was evaluated at 8,192, 16,384, 32,768, and 50,000 entries. On the combined external Kyrgyz benchmark, 32K reaches 8.983 UTF-8 bytes per token and 1.637 sequence tokens per word. The 50K variant reaches 9.521 bytes per token and 1.544 tokens per word.

Moving from 32K to 50K therefore expands the embedding vocabulary by 52.6% for only a 6.0% bytes-per-token improvement. At model width 768, the embedding table grows from 25.2M to 38.4M parameters. The smaller variants save parameters but increase sequence length materially.

## Decision

Release 32,768 entries as `kyrgyz-byte-bpe-v1`. Retain the 8K, 16K, and 50K outputs as local experiment artifacts but do not present them as the primary tokenizer.

## Tradeoffs

- The 32K release uses approximately 61% fewer sequence tokens than DeepSeek-V3 on the external Kyrgyz benchmark while using one quarter of its mergeable vocabulary.
- The 50K variant compresses slightly better and may become preferable for a larger future model.
- The 32K tokenizer has lower heuristic suffix-boundary recall than the smaller variants because it more often stores complete inflected words. Morphological alignment is a diagnostic rather than a sole selection objective.
- Final downstream model quality remains unmeasured. A controlled small-language-model training experiment is the next extrinsic gate.
