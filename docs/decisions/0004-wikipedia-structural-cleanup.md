# Decision 0004: Remove residual Wikipedia structure, not article prose

Date: 2026-08-29

## Context

The first full build and a deterministic accepted-document audit found no non-Kyrgyz sample among 80 inspected records, but the Wikipedia sample exposed unmatched wiki-link brackets and citation text joined directly to prose. A corpus-wide query found residual closing wiki-link brackets in 1,083 of 73,427 near-unique Wikipedia records. This is large enough to address before declaring corpus v1 ready.

## Decision

The Wikimedia extractor now removes `ref`, `references`, and `gallery` tags before rendering visible text. It truncates conventional trailing source, reference, external-link, and see-also sections in Kyrgyz and Russian. A final normalization guard removes unmatched `[[`, `]]`, `{{`, `}}`, and `thumb|` fragments from every source and records the number of removed markers.

## Tradeoffs

- Article prose, headings, and ordinary link labels remain available to tokenizer training.
- Bibliographic strings, raw URLs, media metadata, and malformed wiki syntax are not useful enough to justify their token-frequency distortion.
- Removing a trailing section can discard an unusual article section if its heading matches a reference heading but contains prose. This is a narrow, explicit loss accepted in exchange for substantially cleaner structural text.
- The final guard is source-agnostic. It can remove literal wiki syntax from a document discussing MediaWiki, but the v1 target is general Kyrgyz language rather than code or markup modeling.
