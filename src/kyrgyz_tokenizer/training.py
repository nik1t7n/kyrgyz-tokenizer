from __future__ import annotations

import glob
import json
import logging
import shutil
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import zstandard
from tokenizers import Tokenizer, pre_tokenizers, trainers

from .config import load_config, resolve_path, sha256_file
from .pretokenizer import build_deepseek_style_byte_bpe


LOGGER = logging.getLogger(__name__)


def training_batches(paths: list[Path], batch_size: int) -> Iterator[list[str]]:
    batch: list[str] = []
    for path in paths:
        LOGGER.info("Reading tokenizer training shard %s", path)
        with zstandard.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                batch.append(line)
                if len(batch) == batch_size:
                    yield batch
                    batch = []
    if batch:
        yield batch


def _derive_nested_variant(master: dict[str, Any], vocab_size: int) -> dict[str, Any]:
    variant = json.loads(json.dumps(master))
    model = variant["model"]
    vocab = model["vocab"]
    merges = model["merges"]
    base_vocabulary_size = len(vocab) - len(merges)
    if base_vocabulary_size != 256:
        raise RuntimeError(
            f"Expected a 256-byte base vocabulary, found {base_vocabulary_size}"
        )
    if vocab_size < base_vocabulary_size or vocab_size > len(vocab):
        raise ValueError(f"Invalid nested vocabulary size: {vocab_size}")

    model["vocab"] = {
        token: token_id for token, token_id in vocab.items() if token_id < vocab_size
    }
    model["merges"] = merges[: vocab_size - base_vocabulary_size]
    return variant


def train_tokenizers(config_path: Path, *, reset: bool = False) -> dict[str, Any]:
    config, config_sha256 = load_config(config_path)
    training = config["training"]
    vocab_sizes = sorted({int(value) for value in training["vocab_sizes"]})
    if not vocab_sizes:
        raise ValueError("training.vocab_sizes must not be empty")

    train_paths = [
        Path(path).resolve()
        for path in sorted(glob.glob(config["paths"]["train_glob"]))
    ]
    if not train_paths:
        raise FileNotFoundError("No tokenizer training shards matched the configured glob")

    working_dir = resolve_path(config["paths"]["working_dir"])
    models_dir = working_dir / "models"
    if reset and models_dir.exists():
        if not models_dir.is_relative_to(Path.cwd().resolve()):
            raise RuntimeError(f"Refusing to reset outside repository: {models_dir}")
        shutil.rmtree(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    maximum_size = vocab_sizes[-1]
    tokenizer = build_deepseek_style_byte_bpe()
    trainer = trainers.BpeTrainer(
        vocab_size=maximum_size,
        min_frequency=int(training["min_frequency"]),
        show_progress=True,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        limit_alphabet=256,
        max_token_length=int(training["max_token_length"]),
        special_tokens=[],
    )

    started = time.monotonic()
    tokenizer.train_from_iterator(
        training_batches(train_paths, int(training["iterator_batch_size"])),
        trainer=trainer,
    )
    elapsed_seconds = time.monotonic() - started
    master = json.loads(tokenizer.to_str())
    actual_size = len(master["model"]["vocab"])
    if actual_size < maximum_size:
        raise RuntimeError(
            f"BPE stopped at {actual_size:,} tokens before requested {maximum_size:,}"
        )

    variants: list[dict[str, Any]] = []
    for vocab_size in vocab_sizes:
        model_dir = models_dir / f"bpe-{vocab_size}"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "tokenizer.json"
        variant_data = _derive_nested_variant(master, vocab_size)
        variant = Tokenizer.from_str(json.dumps(variant_data, ensure_ascii=False))
        variant.save(str(model_path), pretty=True)
        variants.append(
            {
                "id": f"kyrgyz-bpe-{vocab_size}",
                "vocab_size": vocab_size,
                "merge_count": vocab_size - 256,
                "path": str(model_path),
                "sha256": sha256_file(model_path),
            }
        )
        LOGGER.info("Wrote nested %s-token tokenizer", f"{vocab_size:,}")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha256,
        "training_seconds": elapsed_seconds,
        "algorithm": "byte-level BPE",
        "pretokenizer": "DeepSeek-V3 published regex sequence followed by ByteLevel",
        "normalizer": None,
        "special_tokens": [],
        "base_vocabulary_size": 256,
        "input_shards": [
            {
                "path": str(path),
                "compressed_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in train_paths
        ],
        "variants": variants,
    }
    manifest_path = working_dir / "training-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Training completed in %.1f seconds", elapsed_seconds)
    return manifest
