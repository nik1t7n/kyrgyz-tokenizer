# Kyrgyz Tokenizer

A reproducible research repository for building a provenance-preserving Kyrgyz corpus and a compact Kyrgyz-Russian byte-level BPE tokenizer.

The current release is a 32,768-token bilingual tokenizer intended as the frozen text-encoding checkpoint for a future small language-model experiment. It uses no unknown token, runtime normalizer, special tokens, or chat protocol.

## Result

Compared with the Kyrgyz-only v1 tokenizer at the same vocabulary size:

| Evaluation group | Kyrgyz v1 | Kyrgyz-Russian v2 | Practical change |
| --- | ---: | ---: | --- |
| Kyrgyz external | 8.983 bytes/token | 8.916 bytes/token | about 0.8% more tokens |
| Russian external | 4.786 bytes/token | 6.477 bytes/token | about 26% fewer tokens |
| Real mixed held-out | 6.505 bytes/token | 7.132 bytes/token | about 9% fewer tokens |

Higher bytes/token means that the same text needs fewer tokens. V2 was selected from 24 controlled candidates while keeping the vocabulary at 32K. It uses 90% Kyrgyz and 10% Russian training bytes with the released GigaChat-style category-aware pre-tokenizer. Every evaluated record decoded exactly.

This is tokenizer evidence, not a claim that a downstream LLM will be smarter. Model quality remains a separate experiment.

## Use the released tokenizer

Requirements: Python 3.12 or 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/nik1t7n/kyrgyz-tokenizer.git
cd kyrgyz-tokenizer
uv sync --locked

uv run kyrgyz-tokenizer inspect \
  --model models/kyrgyz-russian-byte-bpe-v2/tokenizer.json \
  --text "Кыргыз тили жана русский язык"
```

Or load the tracked artifact directly:

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_file(
    "models/kyrgyz-russian-byte-bpe-v2/tokenizer.json"
)
text = "Кыргызстанда кыргызча жана по-русски сүйлөшөт."
encoding = tokenizer.encode(text, add_special_tokens=False)
assert tokenizer.decode(encoding.ids) == text
```

Applications must define their own BOS/EOS, chat, padding, and other model-protocol tokens. They are intentionally absent here.

## Repository map

```text
configs/       pinned corpus and tokenizer experiment definitions
docs/          research, decisions, experiment plans, and aggregate reports
models/        selected v1 and v2 tokenizer artifacts and metadata
src/
  kyrgyz_corpus/      collection, cleaning, LID, deduplication, export
  kyrgyz_tokenizer/   BPE training, benchmarks, evaluation, release
```

Downloaded and generated `data/` and `artifacts/` remain local and are ignored by Git. See [the architecture](docs/ARCHITECTURE.md) for module ownership and the complete data flow.

## Reproduce the completed work

The real corpus build requires network access, about 4 GiB of free disk space, and acceptance of every upstream source's terms.

```bash
# Kyrgyz corpus v1
uv run kyrgyz-corpus build --config configs/corpus-v1.yaml --reset

# Separate Russian supplement
uv run kyrgyz-corpus build --config configs/corpus-ru-v1.yaml --reset

# Kyrgyz-only tokenizer baseline
uv run kyrgyz-tokenizer build --config configs/tokenizer-v1.yaml --reset

# Completed 24-candidate bilingual experiment and release selection
uv run kyrgyz-tokenizer v2-build --config configs/tokenizer-v2.yaml --reset
```

`--reset` only clears generated paths configured inside this repository. Downloaded archives and model files are retained and checksum-verified for reuse. Pipeline stages are resumable; exact revisions, hashes, counts, selection constraints, and observed limitations are recorded in the linked reports.

## Evidence and documentation

- [Repository architecture](docs/ARCHITECTURE.md)
- [Public release and rights boundary](docs/PUBLIC_RELEASE.md)
- [Source registry](docs/SOURCE_REGISTRY.md)
- [Corpus implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Corpus-construction research](docs/research/CORPUS_PRACTICES.md)
- [Tokenizer-design research](docs/research/TOKENIZER_PRACTICES.md)
- [Kyrgyz corpus v1 build report](docs/reports/CORPUS_V1_BUILD_REPORT.md)
- [Kyrgyz corpus quality audit](docs/reports/CORPUS_V1_QUALITY_AUDIT.md)
- [Russian supplement report](docs/reports/CORPUS_RU_V1_BUILD_REPORT.md)
- [Tokenizer v1 evaluation](docs/reports/TOKENIZER_V1_EVALUATION.md)
- [Tokenizer v2 preregistered plan](docs/experiments/TOKENIZER_V2_PLAN.md)
- [Tokenizer v2 evaluation and selection](docs/reports/TOKENIZER_V2_EVALUATION.md)
- [Decision log](docs/README.md)
- [Changelog](CHANGELOG.md)

## Known boundaries

- The selected tokenizer is intrinsically evaluated; no matched downstream LLM has been trained.
- The 21-document mixed benchmark contains real held-out bilingual documents but is publication-style, not representative chat data.
- English and code round-trip safely through bytes but were not optimization targets.
- The corpus includes non-commercial and share-alike sources. Corpus text is not redistributed.
- A public repository is not automatically open source. This checkpoint is released for inspection under the [repository rights notice](LICENSE.md); upstream sources retain their own terms.

## Project status

Corpus v1, the Russian supplement, tokenizer v1, and the controlled Kyrgyz-Russian tokenizer v2 experiment are complete. Tokenizer v2 is frozen as the input artifact for the next LLM phase. New tokenizer experiments should create a new version rather than silently changing this checkpoint.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CITATION.cff](CITATION.cff) for public collaboration, vulnerability reporting, and citation.
