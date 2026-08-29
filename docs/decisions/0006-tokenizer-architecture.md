# Decision 0006: Use category-aware byte-level BPE

Date: 2026-08-29

## Context

Corpus v1 is NFC-normalized Kyrgyz text, but a released tokenizer must still encode every UTF-8 input without an unknown token. Direct byte-level BPE satisfies that requirement, while unrestricted merging can waste vocabulary entries on accidental combinations spanning letters, numbers, punctuation, and whitespace.

DeepSeek-V3 publishes a concrete category-aware ByteLevel-BPE artifact. OpenAI GPT-2/tiktoken and Llama independently converge on byte coverage plus pre-tokenization boundaries. The exact DeepSeek training mixture is not public, so only artifact-verifiable mechanics can be reproduced.

## Decision

Train BPE over the standard reversible ByteLevel alphabet containing all 256 byte values. Apply the published DeepSeek-V3 split sequence before ByteLevel conversion: one-to-three digit groups, CJK spans, Unicode letters/marks, punctuation/symbols, newlines, and whitespace. Do not permit merges across those pre-token boundaries.

Use no runtime normalizer and no special tokens. Corpus training text is already NFC; downstream applications remain responsible for their normalization policy. Model-specific BOS, EOS, padding, chat, and tool tokens will be added only when an actual model interface exists.

Set the maximum learned token length to 64 ByteLevel symbols to prevent long accidental strings from consuming vocabulary entries.

## Tradeoffs

- All Unicode text round-trips through UTF-8 bytes with no unknown token.
- Category boundaries reduce vocabulary waste and mirror a proven large-model design.
- No runtime normalization preserves exact input but allows canonically equivalent strings to tokenize differently.
- The 64-byte cap can exclude a genuinely useful very long token; such strings are rare and can still be represented by shorter tokens.
- Protocol special tokens are intentionally absent, so this artifact is not yet a drop-in chat-model tokenizer.
