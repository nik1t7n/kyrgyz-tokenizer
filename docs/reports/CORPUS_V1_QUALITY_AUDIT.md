# Corpus v1 quality audit

Date: 2026-08-29

## Automated checks

The completed build produced 249,060 near-unique candidate documents before mixture selection. All four source databases completed, every final compressed JSONL shard opened successfully, and the first record from each shard parsed as valid JSON.

| Source | Near-unique documents | Median bytes | P90 bytes | Minimum accepted LID score | Non-NFC documents |
| --- | ---: | ---: | ---: | ---: | ---: |
| FineWeb2 `kir_Cyrl` | 99,337 | 2,193 | 9,526 | 0.757 | 0 |
| Kyrgyz News Corpus | 74,660 | 1,573 | 4,035 | 0.794 | 0 |
| Kyrgyz Wikipedia | 74,322 | 968 | 3,381 | 0.756 | 0 |
| Manas-UdS | 741 | 7,643 | 26,040 | 0.999 | 0 |

The complete near-unique databases were scanned for residual `[[...]]`, `{{...}}`, and `thumb|` Wikipedia markers; none remained. Long records are split at deterministic paragraph or sentence boundaries instead of being silently truncated. Email addresses and IPv4 addresses are redacted before hashing and deduplication.

## Human sample audit

The final deterministic accepted sample contains 80 records across sources and length buckets. Manual review found:

- 80/80 records were Kyrgyz-dominant;
- 0/80 contained severe extraction junk or unusable text;
- approximately 5/80 contained minor presentation artifacts that do not make the text unusable.

Observed minor artifacts were a pipe-delimited web table row, a `Ctrl+Enter` site instruction, occasional missing whitespace at sentence boundaries in news, one fused Manas table-of-contents fragment, and empty parentheses left after Wikipedia template removal. These are known corpus limitations, not hidden failures.

The first rejected-sample audit reviewed 59 records, covering up to two examples from each of 31 source/reason buckets. It exposed valid short Kyrgyz definitions, encyclopedia stubs, and concise news articles rejected by the original 200-character cutoff. Decision 0005 therefore lowered the cutoff to 100 characters while leaving language, script, repetition, URL, HTML, symbol, and duplicate checks unchanged.

## What the audit does not prove

An 80-record manual sample cannot prove that all 188,208 selected documents are clean. Language identification can also accept closely related Turkic or mixed-language passages, and source licenses do not guarantee that every upstream record was lawfully collected. The report establishes reproducibility, broad language quality, normalization, deduplication, and the observed error profile; it is not a legal or exhaustive content certification.

## Release assessment

Corpus v1 is ready for the next project stage: training and evaluating the first byte-level BPE tokenizer. It is not approved for public or commercial corpus redistribution because Manas-UdS and the news source carry non-commercial terms.
