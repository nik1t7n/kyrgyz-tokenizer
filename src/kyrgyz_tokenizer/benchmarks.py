from __future__ import annotations

import glob
import json
import logging
import re
import urllib.request
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import zstandard
from datasets import load_dataset
from kyrgyz_corpus.lid import GlotLID

from .config import load_config, resolve_path, sha256_file


LOGGER = logging.getLogger(__name__)


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "kyrgyz-tokenizer/0.1"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def _parse_conllu(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    sentences: list[str] = []
    morphology: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# text = "):
            sentences.append(line.removeprefix("# text = ").strip())
            continue
        if not line or line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) != 10 or "-" in columns[0] or "." in columns[0]:
            continue
        form, lemma = columns[1], columns[2]
        if lemma != "_":
            morphology.append({"form": form, "lemma": lemma})
    return sentences, morphology


def _write_texts(path: Path, texts: Iterator[str] | list[str]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for text in texts:
            cleaned = text.strip()
            if not cleaned:
                continue
            handle.write(json.dumps({"text": cleaned}, ensure_ascii=False) + "\n")
            count += 1
    return count


def _prepare_mixed_validation(spec: dict[str, Any], output_path: Path) -> tuple[int, list[str]]:
    source_paths = [Path(value) for value in sorted(glob.glob(spec["source_glob"]))]
    if not source_paths:
        raise FileNotFoundError(
            f"No held-out corpus shards matched {spec['source_glob']}"
        )
    lid = GlotLID(spec["glotlid"], output_path.parent / "models" / "glotlid")
    minimum_chars = int(spec["minimum_span_chars"])
    minimum_score = float(spec["minimum_score"])
    max_spans = int(spec["max_spans_per_document"])
    max_records = int(spec["max_records"])
    split_pattern = re.compile(
        r"\n\s*\n|(?<=[.!?])\s+(?=[А-ЯЁӨҮҢ])"
    )

    def mixed_texts() -> Iterator[str]:
        emitted = 0
        for path in source_paths:
            with zstandard.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    labels: set[str] = set()
                    spans = [
                        span.strip()
                        for span in split_pattern.split(str(row["text"]))
                        if len(span.strip()) >= minimum_chars
                    ]
                    for span in spans[:max_spans]:
                        result = lid.predict(span)
                        if result.score >= minimum_score:
                            labels.add(result.label)
                    if {
                        spec["kyrgyz_label"],
                        spec["russian_label"],
                    }.issubset(labels):
                        yield str(row["text"])
                        emitted += 1
                        if emitted >= max_records:
                            return

    count = _write_texts(output_path, mixed_texts())
    return count, [sha256_file(path) for path in source_paths]


def prepare_benchmarks(config_path: Path) -> dict[str, Any]:
    config, config_sha256 = load_config(config_path)
    output_dir = resolve_path(config["paths"]["evaluation_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha256,
        "datasets": [],
    }
    morphology_records: list[dict[str, str]] = []

    for dataset_id, spec in config["external_datasets"].items():
        output_path = output_dir / f"{dataset_id}.jsonl"
        if spec["kind"] == "conllu":
            source_path = output_dir / f"{dataset_id}.conllu"
            LOGGER.info("Downloading pinned benchmark %s", dataset_id)
            _download(spec["url"], source_path)
            texts, pairs = _parse_conllu(source_path)
            if spec.get("include_morphology", True):
                for pair in pairs:
                    pair["dataset"] = dataset_id
                morphology_records.extend(pairs)
            count = _write_texts(output_path, texts)
            source_sha256 = sha256_file(source_path)
        elif spec["kind"] == "huggingface":
            LOGGER.info("Loading pinned benchmark %s", dataset_id)
            dataset = load_dataset(
                spec["repo"],
                spec["subset"],
                split=spec["split"],
                revision=spec["revision"],
            )

            def records() -> Iterator[str]:
                for row in dataset:
                    yield "\n".join(
                        str(row[field]).strip()
                        for field in spec["text_fields"]
                        if row.get(field) is not None and str(row[field]).strip()
                    )

            count = _write_texts(output_path, records())
            source_sha256 = None
        elif spec["kind"] == "text_url":
            source_path = output_dir / f"{dataset_id}.txt"
            LOGGER.info("Downloading pinned text benchmark %s", dataset_id)
            _download(spec["url"], source_path)
            count = _write_texts(output_path, [source_path.read_text(encoding="utf-8")])
            source_sha256 = sha256_file(source_path)
        elif spec["kind"] == "mixed_validation":
            LOGGER.info("Deriving real held-out mixed-language benchmark %s", dataset_id)
            count, source_sha256 = _prepare_mixed_validation(spec, output_path)
        else:
            raise ValueError(f"Unknown external dataset kind: {spec['kind']}")

        manifest["datasets"].append(
            {
                "id": dataset_id,
                "kind": spec["kind"],
                "revision": spec.get("revision"),
                "generator_revision": spec.get("glotlid", {}).get("revision"),
                "license": spec["license"],
                "records": count,
                "output_path": str(output_path),
                "output_sha256": sha256_file(output_path),
                "source_sha256": source_sha256,
            }
        )

    morphology_path = output_dir / "ud-morphology.jsonl"
    with morphology_path.open("w", encoding="utf-8") as handle:
        for record in morphology_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest["morphology"] = {
        "records": len(morphology_records),
        "path": str(morphology_path),
        "sha256": sha256_file(morphology_path),
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def iter_benchmark_texts(config: dict[str, Any]) -> Iterator[tuple[str, str]]:
    validation_sets = config["paths"].get("validation_sets")
    if validation_sets:
        configured_sets = validation_sets.items()
    else:
        configured_sets = [("corpus-validation", config["paths"]["validation_glob"])]
    for dataset_id, path_glob in configured_sets:
        for path_value in sorted(glob.glob(path_glob)):
            path = Path(path_value)
            with zstandard.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    text = line.strip()
                    if text:
                        yield dataset_id, text

    output_dir = resolve_path(config["paths"]["evaluation_dir"])
    for dataset_id in config["external_datasets"]:
        path = output_dir / f"{dataset_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}; run `kyrgyz-tokenizer prepare-benchmarks` first"
            )
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                yield dataset_id, json.loads(line)["text"]


def load_morphology_records(config: dict[str, Any]) -> list[dict[str, str]]:
    path = resolve_path(config["paths"]["evaluation_dir"]) / "ud-morphology.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}; run `kyrgyz-tokenizer prepare-benchmarks` first"
        )
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
