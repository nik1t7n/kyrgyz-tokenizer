# Corpus v1 build report

Date: 2026-08-29

Pipeline revision: `46e4e4fc0b225917941139d0a067987bef5f4496`

Configuration SHA-256: `943868dac3eb6dae7d1e5bd8017502f96742ec6a1ccfb98cd0655524d0c61367`

## Result

The first reproducible tokenizer-training corpus contains 188,208 documents and 524,284,895 UTF-8 bytes. The whole-document selector finished 3,105 bytes below the 500 MiB target rather than truncating a document.

| Split | Documents | UTF-8 bytes |
| --- | ---: | ---: |
| train | 186,360 | 518,527,574 |
| validation | 1,848 | 5,757,321 |
| total | 188,208 | 524,284,895 |

## Final source mixture

| Source | Documents | UTF-8 bytes | Share of bytes |
| --- | ---: | ---: | ---: |
| FineWeb2 `kir_Cyrl` | 52,374 | 236,088,121 | 45.03% |
| Kyrgyz Wikipedia | 74,322 | 136,746,810 | 26.08% |
| Kyrgyz News Corpus | 60,771 | 131,071,033 | 25.00% |
| Manas-UdS | 741 | 20,378,931 | 3.89% |

The mixture is intentionally diverse rather than proportional to upstream availability. FineWeb2 is capped, the complete cleaned Wikipedia and Manas collections are retained, and news fills the remaining budget after quality-ranked selection.

## Deduplication

| Source | Exact-unique documents | Near-unique documents | Removed by near deduplication |
| --- | ---: | ---: | ---: |
| FineWeb2 `kir_Cyrl` | 104,264 | 99,337 | 4,927 |
| Kyrgyz News Corpus | 88,290 | 74,660 | 13,630 |
| Kyrgyz Wikipedia | 74,517 | 74,322 | 195 |
| Manas-UdS | 766 | 741 | 25 |
| total | 267,837 | 249,060 | 18,777 |

Exact duplicates are removed by normalized-text SHA-256. Near duplicates use 5-word shingles, 112 MinHash permutations, a 0.75 candidate threshold, and exact Jaccard verification. Source priority, language score, byte length, and content hash provide deterministic survivor selection.

## Immutable source locks

| Source | Version lock | Upstream license |
| --- | --- | --- |
| Manas-UdS | SHA-1 `82fc72b9687175c55b5309822da2a7c44bb303f1` | CC-BY-NC-SA-4.0 |
| Kyrgyz Wikipedia | `20260801`, SHA-1 `27570d9673f0538d0a4bb21e1eb54e425a9906c1` | CC-BY-SA-4.0 |
| `the-cramer-project/Kyrgyz_News_Corpus` | revision `a7e5ac9c28b86f07c1ad4db1d9c095deb03e46c9` | CC-BY-NC-4.0 |
| FineWeb2 `kir_Cyrl` | revision `af9c13333eb981300149d5ca60a8e9d659b276b9` | ODC-BY-1.0 |

GlotLID V3 is pinned at revision `85cd6716494360367b75f642b5bc78667605d0b4`. FineWeb2 records use the upstream language-identification metadata; the other sources are checked locally.

## Output integrity

The build writes paired compressed JSONL and plain-text shards. These are the SHA-256 checksums of the exact local corpus-v1 outputs:

| File | SHA-256 |
| --- | --- |
| `train-00000.jsonl.zst` | `d9d6e909cacab0945a83311a3ae5c36e394473fca9e17b62c98550d19d48037c` |
| `train-00000.txt.zst` | `8d11ea174ce372addb5367cf22f60eb7897f1acf11fdb4821f0e4cd055b67dce` |
| `train-00001.jsonl.zst` | `68bb7bcff99654975ea59937adc84001c8082496d48d81a40e384781e456fa73` |
| `train-00001.txt.zst` | `6d2f128c19a8ff557a886fa818dcfb6c0454ddc1cf2829d7c12f82089ff23678` |
| `train-00002.jsonl.zst` | `4dd9ba084167fc45422226c02c23c4d660bdae57a44991645723553275ddc1c7` |
| `train-00002.txt.zst` | `531ae1322587492d76153a1cb41ab8ae86b5a5555a54f4779249afa24534e83d` |
| `train-00003.jsonl.zst` | `0dd653640be798b54af951d5ea1616341ee18a111ed3e7b86403b79c5fa4c552` |
| `train-00003.txt.zst` | `35d989378c8fe7e238fd67dc21b94a20a2ba4adc43bbe6348ed2b7d5807a873d` |
| `train-00004.jsonl.zst` | `5cb0c702bb9142e722c373b944e3cdebb71a9b214e5150d585a25846c599ecbb` |
| `train-00004.txt.zst` | `2dc6c4f26699f9cdcfa486506206bb888d7777b0adf19161f6aa4f7f81f630a5` |
| `train-00005.jsonl.zst` | `fa49d184a243a2f71551070429f8a3c208880ccf888499dc199ab0240183991e` |
| `train-00005.txt.zst` | `3970a748dfaaf4eb872641d13021b9187f6e22cdcea6550d5f09249d619d6357` |
| `train-00006.jsonl.zst` | `ac8753d725b132a99f5006214b7ed87cb4e30228704e02a0dc7e3902a843dd2c` |
| `train-00006.txt.zst` | `6663466a8c4d016d0ebd3a6d725ca7e406056d6feaa6dde2ffdaf13bbdeebf2c` |
| `train-00007.jsonl.zst` | `11475a7686771203daa40fffefd2e2a687d7db9c93e80ac9c34f651146a55f6c` |
| `train-00007.txt.zst` | `7d1f3be0b60119fe4523a7a8748702a643f57dc321de43db2c52bdd7db2e3de6` |
| `validation-00000.jsonl.zst` | `d312675f5d95ee7a286fb07ee20e4b1a1dec319a53e47bd570f918fd3456ab45` |
| `validation-00000.txt.zst` | `9a7cecdad36c623f4a1164b837f15c1434a6e0c120e670ee82c2ae9bba1c1adc` |

Corpus payloads are intentionally Git-ignored because redistribution obligations differ by source. The tracked pipeline, locks, decisions, and aggregate reports are sufficient to reproduce and verify them from the authorized upstream sources.

## Scope boundary

This is a tokenizer-training corpus, not a general-purpose language-model pretraining corpus. Its upstream non-commercial components make the assembled local corpus unsuitable for commercial redistribution without a separate license review.
