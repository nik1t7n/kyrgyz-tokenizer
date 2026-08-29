# Kyrgyz Byte BPE v1

## Historical baseline

This is the historical Kyrgyz-only 32,768-token baseline. The current bilingual release candidate is [`kyrgyz-russian-byte-bpe-v2`](../kyrgyz-russian-byte-bpe-v2/).

V1 is a no-UNK byte-level BPE trained on corpus-v1 with the published DeepSeek-V3 pre-tokenization structure. It performs no runtime Unicode normalization and defines no special tokens. Applications must add model-specific protocol tokens separately.

## Usage

```python
from tokenizers import Tokenizer
tokenizer = Tokenizer.from_file("tokenizer.json")
encoding = tokenizer.encode("Кыргыз тили", add_special_tokens=False)
assert tokenizer.decode(encoding.ids) == "Кыргыз тили"
```

## Limitations and rights

This tokenizer was optimized for Kyrgyz, not Russian or natural mixed-language chat. No downstream language model was trained to validate it. Its training sources include non-commercial and share-alike material; the artifact is published for research inspection under the repository rights notice.

Tokenizer SHA-256: `5047b4f427bb1af1c06cfb9cefbe83790b56df409b137b887988db6eba4b159f`.

See [`metadata.json`](metadata.json), [the v1 evaluation](../../docs/reports/TOKENIZER_V1_EVALUATION.md), and [the public release boundary](../../docs/PUBLIC_RELEASE.md).
