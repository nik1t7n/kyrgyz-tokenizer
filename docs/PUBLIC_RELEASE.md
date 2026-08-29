# Public release boundary

Date: 2026-08-29

## Release status

The repository is packaged for public inspection at tokenizer checkpoint v2. The GitHub repository remains private until the owner deliberately changes its visibility. Changing visibility is an external publication action and is not part of this packaging commit.

The current public-facing result is `models/kyrgyz-russian-byte-bpe-v2/tokenizer.json`, selected from the completed 24-candidate Kyrgyz-Russian experiment. No new corpus or tokenizer experiment is required before starting a separate downstream LLM study.

## What is tracked

- corpus and tokenizer source code;
- exact configuration files and dependency lock;
- source identities, revisions, and license records;
- decisions, preregistered hypotheses, aggregate reports, and limitations;
- the selected v1 and v2 tokenizer files with hashes and metadata;
- public repository guidance, citation metadata, and security reporting instructions.

## What is intentionally excluded

- downloaded source archives and raw web text;
- normalized, deduplicated, train, and validation corpus shards;
- SQLite state and local model/download caches;
- generated benchmark records and non-selected candidate tokenizers;
- raw audit examples that could republish licensed or sensitive text;
- credentials and machine-specific paths.

These paths are ignored through `.gitignore`. A public clone can inspect and use the tracked tokenizer artifact, but reproducing corpus construction or training requires downloading the real pinned upstream sources under their original terms.

## Rights boundary

Public visibility and open-source licensing are different decisions. The repository currently uses an explicit all-rights-reserved notice: it is public-review ready, but it does not grant broad reuse, modification, redistribution, or commercial rights.

This conservative boundary is intentional. The training mixture includes, among other sources, `CC BY-NC 4.0`, `CC BY-NC-SA 4.0`, `CC BY-SA 4.0`, GFDL, and ODC-By material plus source-site terms. The repository does not claim that combining these sources creates one universal license or that a tokenizer artifact automatically erases upstream obligations. See `SOURCE_REGISTRY.md` before any redistribution or commercial use.

If the owner later wants an open-source release, code and documentation can receive a standard license separately. The tokenizer artifact needs an explicit model-license decision informed by the source review; that legal policy choice must not be inferred from the code license.

## Readiness evidence

The packaging audit covered the current tree and every Git revision reachable from it:

- no detected credential patterns;
- no tracked `/Users/...` machine paths;
- raw/generated data remains ignored;
- selected tokenizer SHA-256 matches its metadata;
- config SHA-256 matches the recorded training and release metadata;
- the existing v2 artifact round-trips real pinned Kyrgyz, Russian, and mixed-language records exactly;
- the repository explains setup, structure, provenance, evaluation, limitations, contribution, citation, security, and rights.

The audit is bounded evidence, not a legal opinion or a guarantee that every upstream web page is free of third-party rights.

## Publication checklist

Before changing GitHub visibility:

1. read this rights boundary and accept that the release is public-source, not open source;
2. confirm that `main` is at the recorded packaging checkpoint and clean;
3. enable GitHub private vulnerability reporting when it becomes available for the public repository;
4. set the repository description and topics to match the README;
5. change visibility only as a separate deliberate action.

After publication, corpus text must remain excluded. Future LLM code, checkpoints, and evaluations should live in a separate phase or repository so this tokenizer result remains independently reproducible and citable.
