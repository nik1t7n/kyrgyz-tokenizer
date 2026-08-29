# Source Registry

Last updated: 2026-08-29

Exact upstream revisions and downloaded checksums will be written by the build pipeline into a generated manifest.

| Source ID | Upstream source | Published size | Intended role | License / use constraint | v1 status |
| --- | --- | ---: | --- | --- | --- |
| `fineweb2-kir-cyrl` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2), subset `kir_Cyrl` | 1,069,582 docs; 4.36 GB UTF-8 | Broad web and domain coverage | ODC-By 1.0 plus Common Crawl terms | include with a deterministic byte cap |
| `fineweb2-rus-cyrl` | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2), subset `rus_Cyrl` | 699,083,579 docs; 5.82 TB UTF-8 | Bounded Russian supplement for the bilingual tokenizer experiment | ODC-By 1.0 plus Common Crawl terms | build separately with a deterministic shuffled byte cap |
| `kyrgyz-wikipedia` | [Official Wikimedia `kywiki` dump](https://dumps.wikimedia.org/kywiki/latest/) | current `pages-articles` dump; exact size captured at build time | Encyclopedic and formal language | CC BY-SA 4.0 / GFDL as documented by Wikimedia | include from the official dump |
| `kyrgyz-news` | [the-cramer-project/Kyrgyz_News_Corpus](https://huggingface.co/datasets/the-cramer-project/Kyrgyz_News_Corpus) | 256,374 items; 536 MB download | Contemporary multi-topic news | CC BY-NC 4.0; research/non-commercial | include with a domain cap |
| `manas-uds` | [Manas-UdS Kyrgyz Corpus](https://fedora.clarin-d.uni-saarland.de/kyrgyz/) | about 2M words; 12 MB archive / 77 MB VRT | Literature, epic, fairy tales, proverbs, official newspaper | CC BY-NC-SA 4.0 with attribution | include all valid documents |
| `kyrgyz-commoncrawl-community` | [Zarinaaa/commoncrawl_dataset](https://huggingface.co/datasets/Zarinaaa/commoncrawl_dataset) | reported 271 MB | Possible marginal web coverage | dataset card claims CC0; upstream page rights still require care | defer until uniqueness/quality audit |
| `cleaned-kyrgyz-wikipedia-community` | [Zhantas/Cleaned-Kyrgyz_Wikipedia](https://huggingface.co/datasets/Zhantas/Cleaned-Kyrgyz_Wikipedia) | card claims 76,519 articles and 67.2 MB | Originally considered as cleaned Wikipedia | card states CC BY-SA 4.0 | exclude: live schema/sample does not match the card's described Wikipedia structure |

## Inclusion rule

A source is included only when its identity, extraction method, license statement, document field mapping, and upstream revision can be recorded. A source can be downloaded but still excluded after a bounded audit or if it contributes mostly duplicates.
