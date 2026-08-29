# Kyrgyz Byte BPE v1

Selected vocabulary: 32,768 tokens.

The tokenizer is a no-UNK byte-level BPE trained on corpus-v1 with the published DeepSeek-V3 pre-tokenization structure. It performs no runtime Unicode normalization and defines no special tokens. Applications must add model-specific special tokens separately.

Load with:

```python
from tokenizers import Tokenizer
tokenizer = Tokenizer.from_file("tokenizer.json")
encoding = tokenizer.encode("Кыргыз тили", add_special_tokens=False)
assert tokenizer.decode(encoding.ids) == "Кыргыз тили"
```

See `metadata.json` and `docs/reports/TOKENIZER_V1_EVALUATION.md` for provenance and measured limitations.
