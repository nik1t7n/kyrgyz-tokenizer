# Contributing

This is an evidence-first research repository. Contributions should preserve provenance, deterministic configuration, and the distinction between measured results and hypotheses.

## Before opening a change

1. Open an issue describing the concrete problem and the evidence that it affects the current corpus or tokenizer path.
2. Keep one change focused on one research or implementation question.
3. Never commit downloaded corpus text, generated evaluation data, credentials, personal data, or local cache files.
4. Record every new external source in `docs/SOURCE_REGISTRY.md` with an immutable revision and license information before using it.
5. Do not replace an unavailable real source with synthetic or example data.

## Local setup

```bash
git clone https://github.com/nik1t7n/kyrgyz-tokenizer.git
cd kyrgyz-tokenizer
uv sync --locked
```

The released tokenizer can be inspected without downloading the training corpus:

```bash
uv run kyrgyz-tokenizer inspect \
  --model models/kyrgyz-russian-byte-bpe-v2/tokenizer.json \
  --text "Кыргыз тили жана русский язык"
```

For corpus or training changes, document the real command, pinned inputs, generated hashes, and smallest relevant real validation in the pull request. Do not commit the generated `data/` or `artifacts/` directories.

## Pull requests

- Explain what changed and why.
- Separate observations from interpretation.
- Update the relevant decision or report when a measured result changes.
- Run the smallest real path affected by the change and report its output.
- Keep unrelated refactors out of the same pull request.

By contributing, you confirm that you have the right to submit the change. Acceptance does not change the repository license or grant additional rights to other repository content.
