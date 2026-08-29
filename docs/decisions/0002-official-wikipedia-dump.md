# Decision 0002: Use the official Wikimedia dump

Date: 2026-08-29

Status: accepted

## Observation

The `Zhantas/Cleaned-Kyrgyz_Wikipedia` dataset card describes 76,519 cleaned Kyrgyz Wikipedia articles with `title` and `text` usage examples. During live inspection on 2026-08-29, the published Parquet artifact exposed `text` and `source` fields, and the dataset viewer returned a Sputnik news article with `source=Sputnik_kg` as its first document. That is not the structure or provenance described by the card. The Hub dataset-server endpoint also intermittently failed to resolve its split, which weakens reproducibility further.

## Decision

Corpus v1 will extract Kyrgyz Wikipedia from Wikimedia's official `kywiki` pages/articles dump. The build will record the resolved dump date, URL, byte size, and Wikimedia checksum. The community-cleaned artifact remains excluded unless a future audit demonstrates that its contents and documentation agree.

## Trade-off

Parsing the official XML/wikitext dump adds extraction work. In exchange, provenance, version identity, and licensing are authoritative, and the pipeline does not depend on an opaque community transformation whose live artifact currently contradicts its card.
