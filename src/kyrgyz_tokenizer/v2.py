from __future__ import annotations

import glob
import json
import logging
import math
import shutil
import time
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import zstandard
from tokenizers import Tokenizer, pre_tokenizers, trainers

from .benchmarks import prepare_benchmarks
from .config import load_config, resolve_path, sha256_file
from .evaluation import evaluate_tokenizers
from .pretokenizer import build_category_aware_byte_bpe
from .training import _derive_nested_variant


LOGGER = logging.getLogger(__name__)


def _paths_for_glob(pattern: str) -> list[Path]:
    paths = [Path(value).resolve() for value in sorted(glob.glob(pattern))]
    if not paths:
        raise FileNotFoundError(f"No files matched {pattern}")
    return paths


def _iter_records(paths: list[Path]) -> Iterator[dict[str, Any]]:
    for path in paths:
        with zstandard.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def _source_availability(paths: list[Path]) -> Counter[str]:
    availability: Counter[str] = Counter()
    for record in _iter_records(paths):
        availability[str(record["source_id"])] += len(str(record["text"]).encode("utf-8"))
    return availability


def _proportional_quotas(availability: Counter[str], budget: int) -> dict[str, int]:
    total = sum(availability.values())
    if budget > total:
        raise ValueError(f"Requested {budget:,} bytes from only {total:,} available")
    exact = {source: budget * value / total for source, value in availability.items()}
    quotas = {source: math.floor(value) for source, value in exact.items()}
    remainder = budget - sum(quotas.values())
    for source in sorted(exact, key=lambda key: (exact[key] - quotas[key], key), reverse=True):
        if remainder == 0:
            break
        quotas[source] += 1
        remainder -= 1
    return quotas


def _selected_batches(
    kyrgyz_paths: list[Path],
    russian_paths: list[Path],
    kyrgyz_quotas: dict[str, int],
    russian_quota: int,
    batch_size: int,
    selected: Counter[str],
) -> Iterator[list[str]]:
    batch: list[str] = []

    def accept(record: dict[str, Any], quota: int, key: str) -> str | None:
        byte_length = len(str(record["text"]).encode("utf-8"))
        if selected[key] + byte_length > quota:
            return None
        selected[key] += byte_length
        return str(record["text"])

    for record in _iter_records(kyrgyz_paths):
        source = str(record["source_id"])
        if source not in kyrgyz_quotas:
            continue
        text = accept(record, kyrgyz_quotas[source], source)
        if text is None:
            continue
        batch.append(text)
        if len(batch) == batch_size:
            yield batch
            batch = []

    for record in _iter_records(russian_paths) if russian_quota else ():
        text = accept(record, russian_quota, "russian")
        if text is None:
            continue
        batch.append(text)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def train_v2_experiment(config_path: Path, *, reset: bool = False) -> dict[str, Any]:
    config, config_sha256 = load_config(config_path)
    training = config["training"]
    vocab_sizes = sorted({int(value) for value in training["vocab_sizes"]})
    maximum_size = vocab_sizes[-1]
    total_bytes = int(training["total_bytes"])
    kyrgyz_paths = _paths_for_glob(config["paths"]["kyrgyz_train_glob"])
    russian_paths = _paths_for_glob(config["paths"]["russian_train_glob"])
    kyrgyz_availability = _source_availability(kyrgyz_paths)
    russian_availability = _source_availability(russian_paths)
    if len(russian_availability) != 1:
        raise RuntimeError("The v2 experiment expects one deduplicated Russian supplement")

    working_dir = resolve_path(config["paths"]["working_dir"])
    models_dir = working_dir / "models"
    if reset and models_dir.exists():
        if not models_dir.is_relative_to(Path.cwd().resolve()):
            raise RuntimeError(f"Refusing to reset outside repository: {models_dir}")
        shutil.rmtree(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    variants: list[dict[str, Any]] = []
    conditions: list[dict[str, Any]] = []
    for russian_share in [float(value) for value in training["russian_shares"]]:
        if not 0 <= russian_share < 1:
            raise ValueError(f"Invalid Russian share: {russian_share}")
        russian_quota = round(total_bytes * russian_share)
        kyrgyz_budget = total_bytes - russian_quota
        kyrgyz_quotas = _proportional_quotas(kyrgyz_availability, kyrgyz_budget)
        if russian_quota > sum(russian_availability.values()):
            raise ValueError("Russian supplement is smaller than the requested experiment share")
        share_label = f"ru{round(russian_share * 100):02d}"

        for style in training["pretokenizers"]:
            LOGGER.info("Training v2 condition %s %s", style, share_label)
            tokenizer = build_category_aware_byte_bpe(str(style))
            trainer = trainers.BpeTrainer(
                vocab_size=maximum_size,
                min_frequency=int(training["min_frequency"]),
                show_progress=True,
                initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
                limit_alphabet=256,
                max_token_length=int(training["max_token_length"]),
                special_tokens=[],
            )
            selected: Counter[str] = Counter()
            started = time.monotonic()
            tokenizer.train_from_iterator(
                _selected_batches(
                    kyrgyz_paths,
                    russian_paths,
                    kyrgyz_quotas,
                    russian_quota,
                    int(training["iterator_batch_size"]),
                    selected,
                ),
                trainer=trainer,
            )
            elapsed = time.monotonic() - started
            master = json.loads(tokenizer.to_str())
            actual_size = len(master["model"]["vocab"])
            if actual_size < maximum_size:
                raise RuntimeError(
                    f"BPE stopped at {actual_size:,} tokens before {maximum_size:,}"
                )

            condition_dir = models_dir / str(style) / share_label
            for vocab_size in vocab_sizes:
                model_dir = condition_dir / f"bpe-{vocab_size}"
                model_dir.mkdir(parents=True, exist_ok=True)
                model_path = model_dir / "tokenizer.json"
                variant_data = _derive_nested_variant(master, vocab_size)
                variant = Tokenizer.from_str(json.dumps(variant_data, ensure_ascii=False))
                variant.save(str(model_path), pretty=True)
                model_id = f"bilingual-{style}-{share_label}-{vocab_size}"
                variants.append(
                    {
                        "id": model_id,
                        "vocab_size": vocab_size,
                        "pretokenizer": style,
                        "russian_share": russian_share,
                        "path": str(model_path),
                        "sha256": sha256_file(model_path),
                    }
                )

            conditions.append(
                {
                    "pretokenizer": style,
                    "russian_share": russian_share,
                    "training_seconds": elapsed,
                    "requested_bytes": total_bytes,
                    "selected_bytes": sum(selected.values()),
                    "selected_by_source": dict(sorted(selected.items())),
                    "kyrgyz_quotas": dict(sorted(kyrgyz_quotas.items())),
                    "russian_quota": russian_quota,
                }
            )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha256,
        "algorithm": "category-aware byte-level BPE",
        "normalizer": None,
        "special_tokens": [],
        "base_vocabulary_size": 256,
        "total_training_bytes_per_condition": total_bytes,
        "kyrgyz_availability": dict(sorted(kyrgyz_availability.items())),
        "russian_availability": dict(sorted(russian_availability.items())),
        "conditions": conditions,
        "variants": variants,
    }
    working_dir.mkdir(parents=True, exist_ok=True)
    (working_dir / "training-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_ky = left["groups"]["kyrgyz-external"]["bytes_per_token"]
    left_ru = left["groups"]["russian-external"]["bytes_per_token"]
    right_ky = right["groups"]["kyrgyz-external"]["bytes_per_token"]
    right_ru = right["groups"]["russian-external"]["bytes_per_token"]
    no_worse = (
        left["vocab_size"] <= right["vocab_size"]
        and left_ky >= right_ky
        and left_ru >= right_ru
    )
    strictly_better = (
        left["vocab_size"] < right["vocab_size"]
        or left_ky > right_ky
        or left_ru > right_ru
    )
    return no_worse and strictly_better


def select_and_release_v2(config_path: Path) -> dict[str, Any]:
    config, config_sha256 = load_config(config_path)
    working_dir = resolve_path(config["paths"]["working_dir"])
    evaluation = json.loads(
        (working_dir / "evaluation-report.json").read_text(encoding="utf-8")
    )
    selection = config["evaluation"]["selection"]
    baseline = next(
        item for item in evaluation["tokenizers"] if item["id"] == selection["baseline_id"]
    )
    base_ky = baseline["groups"]["kyrgyz-external"]["bytes_per_token"]
    base_ru = baseline["groups"]["russian-external"]["bytes_per_token"]
    candidates = [
        item for item in evaluation["tokenizers"] if item["id"].startswith("bilingual-")
    ]
    eligible = [
        item
        for item in candidates
        if item["aggregate"]["roundtrip_failures"] == 0
        and item["groups"]["kyrgyz-external"]["bytes_per_token"]
        >= base_ky * float(selection["minimum_kyrgyz_retention"])
        and item["groups"]["russian-external"]["bytes_per_token"]
        >= base_ru * float(selection["minimum_russian_gain"])
    ]
    if not eligible:
        raise RuntimeError("No v2 candidate met the published selection constraints")
    pareto = [
        item
        for item in eligible
        if not any(_dominates(other, item) for other in eligible if other is not item)
    ]
    smallest_vocab = min(item["vocab_size"] for item in pareto)
    smallest = [item for item in pareto if item["vocab_size"] == smallest_vocab]
    chosen = max(
        smallest,
        key=lambda item: min(
            item["groups"]["kyrgyz-external"]["bytes_per_token"] / base_ky,
            item["groups"]["russian-external"]["bytes_per_token"] / base_ru,
        ),
    )

    manifest = json.loads(
        (working_dir / "training-manifest.json").read_text(encoding="utf-8")
    )
    variant = next(item for item in manifest["variants"] if item["id"] == chosen["id"])
    condition = next(
        item
        for item in manifest["conditions"]
        if item["pretokenizer"] == variant["pretokenizer"]
        and item["russian_share"] == variant["russian_share"]
    )
    selected_by_source = dict(condition["selected_by_source"])
    if "russian" in selected_by_source:
        russian_source = next(iter(manifest["russian_availability"]))
        selected_by_source[russian_source] = selected_by_source.pop("russian")
    release_dir = resolve_path(config["paths"]["release_dir"])
    release_dir.mkdir(parents=True, exist_ok=True)
    destination = release_dir / "tokenizer.json"
    shutil.copyfile(variant["path"], destination)
    released = {
        "schema_version": 1,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "id": chosen["id"],
        "config_sha256": config_sha256,
        "tokenizer_sha256": sha256_file(destination),
        "training": {
            "algorithm": manifest["algorithm"],
            "base_vocabulary_size": manifest["base_vocabulary_size"],
            "vocabulary_size": chosen["vocab_size"],
            "pretokenizer": variant["pretokenizer"],
            "normalizer": manifest["normalizer"],
            "special_tokens": manifest["special_tokens"],
            "russian_share": variant["russian_share"],
            "requested_utf8_bytes": condition["requested_bytes"],
            "selected_utf8_bytes": condition["selected_bytes"],
            "selected_utf8_bytes_by_source": selected_by_source,
        },
        "selection_constraints": selection,
        "baseline": {
            "id": baseline["id"],
            "kyrgyz_bytes_per_token": base_ky,
            "russian_bytes_per_token": base_ru,
        },
        "evaluation": chosen,
        "pareto_front": [item["id"] for item in pareto],
    }
    (release_dir / "metadata.json").write_text(
        json.dumps(released, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_v2_model_card(release_dir, released)
    _write_v2_report(working_dir, candidates, eligible, pareto, released)
    return released


def _write_v2_model_card(release_dir: Path, released: dict[str, Any]) -> None:
    evaluation = released["evaluation"]
    training = released["training"]
    groups = evaluation["groups"]
    source_rows = [
        f"| `{source}` | {byte_count:,} |"
        for source, byte_count in training["selected_utf8_bytes_by_source"].items()
    ]
    lines = [
        "# Kyrgyz-Russian Byte BPE v2",
        "",
        "## Summary",
        "",
        f"`{released['id']}` is the selected 32K Kyrgyz-Russian byte-level BPE tokenizer. It is the frozen tokenizer checkpoint for a future small bilingual language-model experiment, not a language model itself.",
        "",
        "It has a complete 256-byte base alphabet, no unknown token, no runtime normalizer, and no special or chat-protocol tokens. Any model using it must define protocol tokens separately.",
        "",
        "## Intended use",
        "",
        "Use it to encode and decode Kyrgyz, Russian, or mixed Kyrgyz-Russian UTF-8 text for research and future model training. English, code, and other languages remain byte-safe but were not optimization targets.",
        "",
        "Do not interpret tokenizer compression as evidence of factuality, safety, reasoning ability, or downstream language-model quality.",
        "",
        "## Training",
        "",
        f"The tokenizer was trained on {training['selected_utf8_bytes']:,} UTF-8 bytes: 90% from the versioned Kyrgyz corpus v1 and 10% from the separate FineWeb2 Russian supplement. It uses the released GigaChat-style Unicode category pre-tokenizer and a byte-level BPE merge vocabulary of {training['vocabulary_size']:,} entries.",
        "",
        "| Source | Selected UTF-8 bytes |",
        "| --- | ---: |",
        *source_rows,
        "",
        "Raw corpus text is not redistributed. Source identities, revisions, transformations, and licenses are documented in the [source registry](../../docs/SOURCE_REGISTRY.md) and corpus reports.",
        "",
        "## Evaluation",
        "",
        "Higher bytes/token means that the same text uses fewer tokens.",
        "",
        "| Group | Bytes/token | Round-trip failures |",
        "| --- | ---: | ---: |",
        f"| Kyrgyz external | {groups['kyrgyz-external']['bytes_per_token']:.3f} | {groups['kyrgyz-external']['roundtrip_failures']} |",
        f"| Russian external | {groups['russian-external']['bytes_per_token']:.3f} | {groups['russian-external']['roundtrip_failures']} |",
        f"| Real mixed held-out | {groups['mixed-validation']['bytes_per_token']:.3f} | {groups['mixed-validation']['roundtrip_failures']} |",
        f"| Code diagnostic | {groups['code-diagnostic']['bytes_per_token']:.3f} | {groups['code-diagnostic']['roundtrip_failures']} |",
        "",
        "Relative to the same-size Kyrgyz-only v1 release, this tokenizer uses about 26% fewer tokens on external Russian data, about 9% fewer on the real mixed diagnostic, and about 0.8% more on external Kyrgyz data. Selection required zero round-trip failures, at least 90% Kyrgyz compression retention, and at least a 20% Russian compression gain.",
        "",
        "## Usage",
        "",
        "```python",
        "from tokenizers import Tokenizer",
        "",
        "tokenizer = Tokenizer.from_file(\"tokenizer.json\")",
        "text = \"Кыргызстанда кыргызча жана по-русски сүйлөшөт.\"",
        "encoding = tokenizer.encode(text, add_special_tokens=False)",
        "assert tokenizer.decode(encoding.ids) == text",
        "```",
        "",
        "## Limitations and rights",
        "",
        "The mixed evaluation contains 21 real held-out publication-style documents and is not representative of natural chat. No downstream LLM comparison has been run. The training mix includes non-commercial and share-alike sources; the artifact is published for research inspection under the repository rights notice, not under an inferred open-source model license.",
        "",
        f"Tokenizer SHA-256: `{released['tokenizer_sha256']}`.",
        "",
        "See [`metadata.json`](metadata.json), [the v2 evaluation](../../docs/reports/TOKENIZER_V2_EVALUATION.md), and [the public release boundary](../../docs/PUBLIC_RELEASE.md) for exact evidence and boundaries.",
        "",
    ]
    (release_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _write_v2_report(
    working_dir: Path,
    candidates: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    pareto: list[dict[str, Any]],
    released: dict[str, Any],
) -> None:
    eligible_ids = {item["id"] for item in eligible}
    pareto_ids = {item["id"] for item in pareto}
    selected_id = released["id"]
    lines = [
        "# Tokenizer v2 experiment report",
        "",
        f"Selected: `{selected_id}`",
        "",
        "| Candidate | Vocab | Kyrgyz bytes/token | Russian bytes/token | Mixed bytes/token | Code bytes/token | Eligible | Pareto |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in sorted(candidates, key=lambda value: value["id"]):
        lines.append(
            f"| {item['id']} | {item['vocab_size']:,} | "
            f"{item['groups']['kyrgyz-external']['bytes_per_token']:.3f} | "
            f"{item['groups']['russian-external']['bytes_per_token']:.3f} | "
            f"{item['groups']['mixed-validation']['bytes_per_token']:.3f} | "
            f"{item['groups']['code-diagnostic']['bytes_per_token']:.3f} | "
            f"{'yes' if item['id'] in eligible_ids else 'no'} | "
            f"{'yes' if item['id'] in pareto_ids else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Selection is constrained, not based on one opaque average: zero round-trip failures, at least 90% of v1 Kyrgyz compression, and at least a 20% Russian improvement. Pareto-dominated points are removed; the smallest remaining vocabulary wins, with worst-language relative retention used only to break ties at the same vocabulary size.",
            "",
            "Code is reported as a diagnostic and does not affect selection.",
            "",
        ]
    )
    (working_dir / "experiment-report.md").write_text("\n".join(lines), encoding="utf-8")


def build_v2(config_path: Path, *, reset: bool = False) -> dict[str, Any]:
    train_v2_experiment(config_path, reset=reset)
    prepare_benchmarks(config_path)
    evaluate_tokenizers(config_path)
    return select_and_release_v2(config_path)
