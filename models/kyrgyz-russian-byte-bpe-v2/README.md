# Kyrgyz-Russian Byte BPE v2

## Summary

`bilingual-gigachat-ru10-32768` is the selected 32K Kyrgyz-Russian byte-level BPE tokenizer. It is the frozen tokenizer checkpoint for a future small bilingual language-model experiment, not a language model itself.

It has a complete 256-byte base alphabet, no unknown token, no runtime normalizer, and no special or chat-protocol tokens. Any model using it must define protocol tokens separately.

## Intended use

Use it to encode and decode Kyrgyz, Russian, or mixed Kyrgyz-Russian UTF-8 text for research and future model training. English, code, and other languages remain byte-safe but were not optimization targets.

Do not interpret tokenizer compression as evidence of factuality, safety, reasoning ability, or downstream language-model quality.

## Training

The tokenizer was trained on 503,315,878 UTF-8 bytes: 90% from the versioned Kyrgyz corpus v1 and 10% from the separate FineWeb2 Russian supplement. It uses the released GigaChat-style Unicode category pre-tokenizer and a byte-level BPE merge vocabulary of 32,768 entries.

| Source | Selected UTF-8 bytes |
| --- | ---: |
| `fineweb2-kir-cyrl` | 203,904,832 |
| `kyrgyz-news` | 113,451,489 |
| `kyrgyz-wikipedia` | 118,276,076 |
| `manas-uds` | 17,351,875 |
| `fineweb2-rus-cyrl` | 50,331,606 |

Raw corpus text is not redistributed. Source identities, revisions, transformations, and licenses are documented in the [source registry](../../docs/SOURCE_REGISTRY.md) and corpus reports.

## Evaluation

Higher bytes/token means that the same text uses fewer tokens.

| Group | Bytes/token | Round-trip failures |
| --- | ---: | ---: |
| Kyrgyz external | 8.916 | 0 |
| Russian external | 6.477 | 0 |
| Real mixed held-out | 7.132 | 0 |
| Code diagnostic | 1.604 | 0 |

Relative to the same-size Kyrgyz-only v1 release, this tokenizer uses about 26% fewer tokens on external Russian data, about 9% fewer on the real mixed diagnostic, and about 0.8% more on external Kyrgyz data. Selection required zero round-trip failures, at least 90% Kyrgyz compression retention, and at least a 20% Russian compression gain.

## Usage

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_file("tokenizer.json")
text = "Кыргызстанда кыргызча жана по-русски сүйлөшөт."
encoding = tokenizer.encode(text, add_special_tokens=False)
assert tokenizer.decode(encoding.ids) == text
```

## Limitations and rights

The mixed evaluation contains 21 real held-out publication-style documents and is not representative of natural chat. No downstream LLM comparison has been run. The training mix includes non-commercial and share-alike sources; the artifact is published for research inspection under the repository rights notice, not under an inferred open-source model license.

Tokenizer SHA-256: `751db52127be3c2bf6a7164a98b0caaac7c7fc180a941c99f8889f637ec3d688`.

See [`metadata.json`](metadata.json), [the v2 evaluation](../../docs/reports/TOKENIZER_V2_EVALUATION.md), and [the public release boundary](../../docs/PUBLIC_RELEASE.md) for exact evidence and boundaries.
