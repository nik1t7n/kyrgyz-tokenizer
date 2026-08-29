# Kyrgyz-Russian Byte BPE v2

Selected experiment candidate: `bilingual-gigachat-ru10-32768`.

Vocabulary: 32,768 entries. The tokenizer uses the published gigachat-style Unicode category pre-tokenizer, a complete 256-byte base alphabet, no normalizer, and no special tokens.

It was selected under explicit constraints: zero round-trip failures, at least 90% retention of the v1 external Kyrgyz compression, and at least a 20% improvement on external Russian data. Code efficiency was measured only as a diagnostic and did not affect selection.

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_file("tokenizer.json")
text = "Кыргызстанда кыргызча жана по-русски сүйлөшөт."
encoding = tokenizer.encode(text, add_special_tokens=False)
assert tokenizer.decode(encoding.ids) == text
```

See `metadata.json` and `docs/reports/TOKENIZER_V2_EVALUATION.md` for the measured trade-offs and evidence limits.
