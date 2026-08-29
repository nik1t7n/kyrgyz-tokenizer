# Tokenizer design research

Date: 2026-08-29

## Method

The review used Exa to inspect 168 search results across 15 workstreams. Results were deduplicated and reduced to primary material: technical reports, official model artifacts, library documentation, released datasets, and implementation repositories. Commentary pages and unverified tokenizer mirrors were not used to define the implementation.

## High-signal findings

| System or study | Verified tokenizer design | What transfers to this project |
| --- | --- | --- |
| [DeepSeek-V3](https://arxiv.org/html/2412.19437) | Byte-level BPE, 128K mergeable vocabulary, modified pre-tokenizer and training data for multilingual compression. The published [`tokenizer.json`](https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/tokenizer.json) shows digit chunks of one to three digits, a separate CJK branch, Unicode category-aware text splitting, and ByteLevel encoding with no normalizer. | Reuse the published pre-tokenization structure, byte coverage, and no-cross-category merge boundary. Do not claim to reproduce DeepSeek training: its exact tokenizer corpus and mixture are not public. |
| [OpenAI GPT-2](https://github.com/openai/gpt-2/blob/a74da5d99abaaba920de8131d64da2862a8f213b/src/encoder.py) and [tiktoken](https://github.com/openai/tiktoken/blob/dcb39287/tiktoken_ext/openai_public.py) | Byte remapping guarantees coverage without a large Unicode base alphabet. Regex pre-tokenization prevents wasteful merges across letters, numbers, punctuation, and whitespace. `cl100k_base` separately limits number groups; `o200k_base` refines Unicode-case patterns. | Preserve all 256 byte values and isolate character categories before BPE. Pin comparison artifacts by their official hashes. |
| [Llama 2](https://arxiv.org/html/2307.09288) | SentencePiece BPE, 32K vocabulary, split digits, byte decomposition for unknown UTF-8 characters. | A 32K candidate is a serious baseline, not an arbitrary default. Byte coverage and digit isolation converge with the DeepSeek/OpenAI designs. |
| [Gemma 3](https://arxiv.org/html/2503.19786) | SentencePiece with split digits, preserved whitespace, byte encodings, and a 262K multilingual vocabulary. | Large vocabularies are justified by broad multilingual coverage; they are not automatically efficient for a dedicated Kyrgyz model. |
| [SentencePiece](https://aclanthology.org/D18-2012/) | Language-independent BPE and Unigram training directly from raw sentences. | Unigram remains a valid future ablation, but v1 stays with transparent BPE because the project goal is to inspect merge learning directly. |
| [SozKZ](https://arxiv.org/html/2603.20854) | Dedicated 50K ByteLevel BPE for Kazakh, reported as having a two-to-three-fold fertility advantage over multilingual tokenizers. | Train a 50K upper bound and compare smaller nested vocabularies on held-out Kyrgyz text instead of copying 50K blindly. |
| [Kazakh CSE tokenizer study](https://www.mdpi.com/2078-2489/17/2/128) | SentencePiece BPE and Unigram trained on morphology-aware segmented corpora; provides a reproducible Kazakh morphology experiment. | Add an explicit suffix-boundary diagnostic. Do not inject Kazakh morphological rules into Kyrgyz without a verified Kyrgyz segmentation resource. |
| [Tokenizer Choice for LLM Training](https://aclanthology.org/2024.findings-naacl.247/) | Controlled 2.6B-parameter experiments show tokenizer choice changes training cost and downstream quality, while fertility and parity alone are unreliable predictors. | Use intrinsic metrics to choose a practical v1, but label downstream model training as the remaining extrinsic gate. |
| [Morphological Alignment in 70 Languages](https://arxiv.org/html/2507.06378) | Morphological alignment explains little downstream variance by itself. | Treat the UD lemma/suffix boundary score as a diagnostic, not the optimization target. |

## DeepSeek artifact inspection

The pinned DeepSeek-V3 tokenizer artifact at revision `e815299b0bcbac849fa540c768ef21845365c9eb` has SHA-256 `621ac2e32d0dba658404412318818aaa8ce8cda492e59830109d8da6b517fb41`. Its BPE model contains 128,000 mergeable entries and 127,741 merges; the repository also defines added/reserved tokens for model protocols. The Kyrgyz v1 tokenizer deliberately excludes those protocol tokens because they belong to a future language-model interface, not to lexical compression.

The transferable pre-tokenizer sequence is:

1. isolate Unicode numbers in groups of one to three;
2. isolate CJK spans;
3. isolate letter/mark spans, punctuation/symbol spans, newlines, and whitespace through Unicode category-aware regular expressions;
4. map the resulting UTF-8 bytes to the reversible ByteLevel alphabet;
5. permit BPE merges only inside those fragments.

## Chosen experiment

One 50K merge sequence is trained on the complete corpus-v1 train split. The 8K, 16K, and 32K variants are exact prefixes of that same merge history. This removes run-to-run and corpus-order confounding from the vocabulary-size comparison.

Evaluation uses the untouched corpus validation split plus pinned external data:

- [UD Kyrgyz-KTMU](https://universaldependencies.org/treebanks/ky_ktmu/index.html), news headlines;
- [UD Kyrgyz-TueCL](https://github.com/UniversalDependencies/UD_Kyrgyz-TueCL), fiction;
- [Belebele](https://huggingface.co/datasets/facebook/belebele), translated reading comprehension;
- [SIB-200](https://huggingface.co/datasets/Davlan/sib200), topic-classification sentences.

The benchmark reports UTF-8 bytes per token, sequence fertility, isolated single-token word rate, round-trip failures, and a narrowly defined UD lemma/suffix boundary recall. It also reports embedding-table parameter cost at three model widths.

## Known evidence limits

- DeepSeek publishes the tokenizer artifact and a high-level description, not the exact tokenizer corpus or complete training recipe.
- Meta Llama 3.2 and Gemma 3 artifacts are gated. The current machine is not authenticated for either repository, so their direct Kyrgyz benchmark rows are explicitly unavailable rather than replaced with mirrors.
- Intrinsic tokenizer results do not establish downstream language-model quality.
- The UD boundary measure only covers surface forms that begin with their annotated lemma; Kyrgyz morphophonological alternations fall outside it.
