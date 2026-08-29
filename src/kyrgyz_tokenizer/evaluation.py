from __future__ import annotations

import glob
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import regex
import tiktoken
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from .benchmarks import iter_benchmark_texts, load_morphology_records
from .config import load_config, resolve_path, sha256_file


LOGGER = logging.getLogger(__name__)


class TokenizerAdapter(Protocol):
    id: str
    vocab_size: int

    def encode(self, text: str) -> list[int]: ...

    def decode(self, token_ids: list[int]) -> str: ...

    def boundaries(self, text: str) -> set[int]: ...


@dataclass
class HuggingFaceAdapter:
    id: str
    tokenizer: Tokenizer

    @property
    def vocab_size(self) -> int:
        return self.tokenizer.get_vocab_size(with_added_tokens=False)

    def encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def decode(self, token_ids: list[int]) -> str:
        return self.tokenizer.decode(token_ids, skip_special_tokens=False)

    def boundaries(self, text: str) -> set[int]:
        encoding = self.tokenizer.encode(text, add_special_tokens=False)
        return {end for _, end in encoding.offsets[:-1]}


@dataclass
class TiktokenAdapter:
    id: str
    tokenizer: tiktoken.Encoding

    @property
    def vocab_size(self) -> int:
        return self.tokenizer.n_vocab

    def encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, disallowed_special=())

    def decode(self, token_ids: list[int]) -> str:
        return self.tokenizer.decode(token_ids)

    def boundaries(self, text: str) -> set[int]:
        token_ids = self.encode(text)
        byte_offset = 0
        character_boundaries: dict[int, int] = {}
        encoded = text.encode("utf-8")
        for character_index in range(1, len(text)):
            character_boundaries[len(text[:character_index].encode("utf-8"))] = character_index
        boundaries: set[int] = set()
        for token_id in token_ids[:-1]:
            byte_offset += len(self.tokenizer.decode_single_token_bytes(token_id))
            if byte_offset in character_boundaries:
                boundaries.add(character_boundaries[byte_offset])
        if byte_offset > len(encoded):
            raise RuntimeError("Tokenizer byte offsets exceed encoded text length")
        return boundaries


def _load_adapters(
    config: dict[str, Any], working_dir: Path
) -> tuple[list[TokenizerAdapter], list[dict[str, Any]], list[dict[str, str]]]:
    adapters: list[TokenizerAdapter] = []
    locks: list[dict[str, Any]] = []
    unavailable: list[dict[str, str]] = []
    manifest_path = working_dir / "training-manifest.json"
    local_models: list[tuple[str, Path]] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        local_models = [
            (str(item["id"]), Path(item["path"])) for item in manifest["variants"]
        ]
    else:
        local_models = [
            (
                f"kyrgyz-bpe-{Path(path_value).parent.name.removeprefix('bpe-')}",
                Path(path_value),
            )
            for path_value in sorted(
                glob.glob(str(working_dir / "models" / "bpe-*" / "tokenizer.json"))
            )
        ]

    for model_id, path in local_models:
        tokenizer = Tokenizer.from_file(str(path))
        adapters.append(
            HuggingFaceAdapter(
                id=model_id,
                tokenizer=tokenizer,
            )
        )
        locks.append(
            {
                "id": model_id,
                "kind": "local",
                "path": str(path),
                "sha256": sha256_file(path),
            }
        )

    cache_dir = working_dir / "baselines"
    cache_dir.mkdir(parents=True, exist_ok=True)
    for spec in config["baselines"]:
        try:
            if spec["kind"] == "local":
                path = resolve_path(spec["path"])
                adapters.append(
                    HuggingFaceAdapter(spec["id"], Tokenizer.from_file(str(path)))
                )
                locks.append(
                    {
                        "id": spec["id"],
                        "kind": "local-baseline",
                        "path": str(path),
                        "sha256": sha256_file(path),
                    }
                )
            elif spec["kind"] == "huggingface":
                path = hf_hub_download(
                    spec["repo"],
                    "tokenizer.json",
                    revision=spec["revision"],
                    local_dir=cache_dir / spec["id"],
                )
                adapters.append(
                    HuggingFaceAdapter(spec["id"], Tokenizer.from_file(path))
                )
                locks.append(
                    {
                        "id": spec["id"],
                        "kind": "huggingface",
                        "repo": spec["repo"],
                        "revision": spec["revision"],
                        "sha256": sha256_file(Path(path)),
                    }
                )
            elif spec["kind"] == "tiktoken":
                adapters.append(
                    TiktokenAdapter(spec["id"], tiktoken.get_encoding(spec["encoding"]))
                )
                locks.append(
                    {
                        "id": spec["id"],
                        "kind": "tiktoken",
                        "encoding": spec["encoding"],
                        "artifact_sha256": spec["artifact_sha256"],
                    }
                )
            else:
                raise ValueError(f"Unknown baseline kind: {spec['kind']}")
        except Exception as error:
            LOGGER.warning("Baseline %s unavailable: %s", spec["id"], error)
            unavailable.append(
                {
                    "id": spec["id"],
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    if not adapters:
        raise RuntimeError("No trained tokenizers or baselines are available")
    return adapters, locks, unavailable


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    values.sort()
    return values[round((len(values) - 1) * fraction)]


def _evaluate_morphology(
    adapter: TokenizerAdapter, records: list[dict[str, str]]
) -> dict[str, Any]:
    eligible = 0
    aligned = 0
    token_count = 0
    for record in records:
        form = record["form"]
        lemma = record["lemma"]
        if not form.isalpha() or not lemma.isalpha() or len(form) <= len(lemma):
            continue
        if not form.casefold().startswith(lemma.casefold()):
            continue
        target = len(lemma)
        eligible += 1
        token_count += len(adapter.encode(form))
        if target in adapter.boundaries(form):
            aligned += 1
    return {
        "eligible_ud_suffix_forms": eligible,
        "lemma_suffix_boundary_recall": aligned / eligible if eligible else None,
        "tokens_per_inflected_word": token_count / eligible if eligible else None,
        "method": "Heuristic: surface form case-insensitively begins with the UD lemma",
    }


def evaluate_tokenizers(config_path: Path) -> dict[str, Any]:
    config, config_sha256 = load_config(config_path)
    working_dir = resolve_path(config["paths"]["working_dir"])
    adapters, tokenizer_locks, unavailable = _load_adapters(config, working_dir)
    word_pattern = regex.compile(config["evaluation"]["word_pattern"])

    texts_by_dataset: dict[str, list[str]] = defaultdict(list)
    for dataset_id, text in iter_benchmark_texts(config):
        texts_by_dataset[dataset_id].append(text)
    morphology = load_morphology_records(config)

    results: list[dict[str, Any]] = []
    for adapter in adapters:
        LOGGER.info("Evaluating %s", adapter.id)
        per_dataset: dict[str, Any] = {}
        aggregate = Counter()
        word_token_cache: dict[str, int] = {}
        for dataset_id, texts in texts_by_dataset.items():
            token_lengths: list[int] = []
            words: list[str] = []
            roundtrip_failures = 0
            byte_count = 0
            char_count = 0
            token_count = 0
            for text in texts:
                token_ids = adapter.encode(text)
                token_lengths.append(len(token_ids))
                token_count += len(token_ids)
                byte_count += len(text.encode("utf-8"))
                char_count += len(text)
                words.extend(match.group(0) for match in word_pattern.finditer(text))
                if adapter.decode(token_ids) != text:
                    roundtrip_failures += 1

            word_frequencies = Counter(words)
            single_token_words = 0
            total_word_tokens = 0
            for word, frequency in word_frequencies.items():
                if word not in word_token_cache:
                    word_token_cache[word] = len(adapter.encode(word))
                count = word_token_cache[word]
                total_word_tokens += count * frequency
                if count == 1:
                    single_token_words += frequency

            metrics = {
                "records": len(texts),
                "utf8_bytes": byte_count,
                "characters": char_count,
                "words": len(words),
                "tokens": token_count,
                "bytes_per_token": byte_count / token_count,
                "characters_per_token": char_count / token_count,
                "sequence_fertility": token_count / len(words) if words else None,
                "isolated_word_fertility": total_word_tokens / len(words) if words else None,
                "single_token_word_rate": single_token_words / len(words) if words else None,
                "tokens_per_record_p50": _percentile(token_lengths, 0.50),
                "tokens_per_record_p90": _percentile(token_lengths, 0.90),
                "roundtrip_failures": roundtrip_failures,
            }
            per_dataset[dataset_id] = metrics
            for key in ("utf8_bytes", "characters", "words", "tokens"):
                aggregate[key] += metrics[key]
            aggregate["word_tokens"] += total_word_tokens
            aggregate["single_token_words"] += single_token_words
            aggregate["roundtrip_failures"] += roundtrip_failures

        results.append(
            {
                "id": adapter.id,
                "vocab_size": adapter.vocab_size,
                "aggregate": {
                    "utf8_bytes": aggregate["utf8_bytes"],
                    "characters": aggregate["characters"],
                    "words": aggregate["words"],
                    "tokens": aggregate["tokens"],
                    "bytes_per_token": aggregate["utf8_bytes"] / aggregate["tokens"],
                    "characters_per_token": aggregate["characters"] / aggregate["tokens"],
                    "sequence_fertility": aggregate["tokens"] / aggregate["words"],
                    "isolated_word_fertility": aggregate["word_tokens"] / aggregate["words"],
                    "single_token_word_rate": aggregate["single_token_words"] / aggregate["words"],
                    "roundtrip_failures": aggregate["roundtrip_failures"],
                },
                "external_only": _external_summary(per_dataset),
                "groups": {
                    group_id: _summary_for_datasets(per_dataset, dataset_ids)
                    for group_id, dataset_ids in config["evaluation"].get(
                        "groups", {}
                    ).items()
                },
                "morphology": _evaluate_morphology(adapter, morphology),
                "datasets": per_dataset,
                "embedding_parameters": {
                    str(dimension): adapter.vocab_size * int(dimension)
                    for dimension in config["evaluation"]["embedding_dimensions"]
                },
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha256,
        "datasets": {key: len(value) for key, value in texts_by_dataset.items()},
        "tokenizer_locks": tokenizer_locks,
        "tokenizers": sorted(
            results,
            key=lambda item: (-item["external_only"]["bytes_per_token"], item["vocab_size"]),
        ),
        "unavailable_baselines": unavailable,
    }
    report_path = working_dir / "evaluation-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _external_summary(per_dataset: dict[str, Any]) -> dict[str, Any]:
    included = [
        values for key, values in per_dataset.items() if not key.endswith("validation")
    ]
    return _summarize_metrics(included)


def _summary_for_datasets(
    per_dataset: dict[str, Any], dataset_ids: list[str]
) -> dict[str, Any]:
    missing = [dataset_id for dataset_id in dataset_ids if dataset_id not in per_dataset]
    if missing:
        raise KeyError(f"Missing evaluation datasets: {', '.join(missing)}")
    return _summarize_metrics([per_dataset[dataset_id] for dataset_id in dataset_ids])


def _summarize_metrics(included: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    for values in included:
        for key in ("utf8_bytes", "characters", "words", "tokens"):
            totals[key] += values[key]
        totals["word_tokens"] += values["isolated_word_fertility"] * values["words"]
        totals["single_token_words"] += values["single_token_word_rate"] * values["words"]
        totals["roundtrip_failures"] += values["roundtrip_failures"]
    if not totals["tokens"] or not totals["words"]:
        raise ValueError("Cannot summarize an empty evaluation group")
    return {
        "utf8_bytes": totals["utf8_bytes"],
        "characters": totals["characters"],
        "words": totals["words"],
        "tokens": totals["tokens"],
        "bytes_per_token": totals["utf8_bytes"] / totals["tokens"],
        "characters_per_token": totals["characters"] / totals["tokens"],
        "sequence_fertility": totals["tokens"] / totals["words"],
        "isolated_word_fertility": totals["word_tokens"] / totals["words"],
        "single_token_word_rate": totals["single_token_words"] / totals["words"],
        "roundtrip_failures": totals["roundtrip_failures"],
    }
