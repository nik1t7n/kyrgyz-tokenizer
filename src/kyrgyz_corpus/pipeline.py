from __future__ import annotations

import hashlib
import heapq
import json
import logging
import shutil
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml
import zstandard

from .cleaning import clean_text
from .dedup import run_near_dedup
from .lid import GlotLID
from .models import RawDocument
from .reporting import write_report
from .sources import file_hash, open_source, write_source_lock
from .store import CorpusStore


LOGGER = logging.getLogger(__name__)
SHARD_BYTES = 64 * 1024 * 1024


def load_config(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    config = yaml.safe_load(raw)
    return config, hashlib.sha256(raw).hexdigest()


def resolve_path(value: str) -> Path:
    return Path(value).resolve()


def safe_remove(path: Path, repository_root: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(repository_root.resolve()):
        raise RuntimeError(f"Refusing to remove path outside repository: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def split_long_document(document: RawDocument, max_chars: int) -> Iterator[RawDocument]:
    if len(document.text) <= max_chars:
        yield document
        return

    chunks: list[str] = []
    start = 0
    while start < len(document.text):
        upper = min(start + max_chars, len(document.text))
        if upper == len(document.text):
            boundary = upper
        else:
            candidates = [
                document.text.rfind("\n\n", start, upper),
                document.text.rfind("\n", start, upper),
                document.text.rfind(". ", start, upper),
                document.text.rfind("! ", start, upper),
                document.text.rfind("? ", start, upper),
            ]
            boundary = max(candidates)
            if boundary < start + max_chars // 2:
                boundary = upper
            elif document.text[boundary : boundary + 2] in {". ", "! ", "? "}:
                boundary += 1

        chunk = document.text[start:boundary].strip()
        if chunk:
            chunks.append(chunk)
        start = boundary
        while start < len(document.text) and document.text[start].isspace():
            start += 1

    for chunk_index, text in enumerate(chunks):
        metadata = dict(document.metadata)
        metadata.update(
            {
                "parent_upstream_id": document.upstream_id,
                "chunk_index": chunk_index,
                "chunk_count": len(chunks),
            }
        )
        yield RawDocument(
            source_id=document.source_id,
            upstream_id=f"{document.upstream_id}#chunk-{chunk_index:05d}",
            text=text,
            url=document.url,
            metadata=metadata,
        )


class AuditSampler:
    def __init__(self, limit: int = 10):
        self.limit = limit
        self.samples: dict[
            tuple[str, str], list[tuple[int, str, dict[str, Any]]]
        ] = defaultdict(list)

    def add(self, source_id: str, reason: str, document: RawDocument, metrics: dict) -> None:
        score = int.from_bytes(hashlib.sha256(document.text.encode("utf-8")).digest()[:8], "big")
        item = (
            -score,
            document.upstream_id,
            {
                "source_id": source_id,
                "reason": reason,
                "upstream_id": document.upstream_id,
                "url": document.url,
                "metrics": metrics,
                "text": document.text[:2000],
            },
        )
        bucket = self.samples[(source_id, reason)]
        if len(bucket) < self.limit:
            heapq.heappush(bucket, item)
        elif item[0] > bucket[0][0]:
            heapq.heapreplace(bucket, item)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        records = []
        for bucket in self.samples.values():
            records.extend(item[2] for item in bucket)
        records.sort(key=lambda row: (row["source_id"], row["reason"], row["upstream_id"]))
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def collect_sources(
    store: CorpusStore,
    config: dict,
    *,
    selected_sources: set[str] | None = None,
    max_docs: int | None = None,
) -> None:
    raw_dir = resolve_path(config["paths"]["raw_dir"])
    artifacts_dir = resolve_path(config["paths"]["artifacts_dir"])
    lid = GlotLID(config["language_id"], raw_dir / "models" / "glotlid")
    sampler = AuditSampler()

    for source in sorted(config["sources"], key=lambda item: int(item["priority"])):
        source_id = source["id"]
        if selected_sources and source_id not in selected_sources:
            continue
        if store.source_status(source_id) == "complete" and max_docs is None:
            LOGGER.info("Skipping completed source %s", source_id)
            continue

        LOGGER.info("Opening source %s", source_id)
        documents, lock = open_source(source, raw_dir)
        lock.update({"source_id": source_id, "license": source["license"]})
        write_source_lock(artifacts_dir / "manifests" / f"{source_id}.lock.json", lock)
        store.start_source(source, lock)

        accepted_bytes = 0
        max_accepted_bytes = source.get("max_accepted_bytes")
        upstream_lid_field = source.get("upstream_lid_score_field")

        byte_cap_reached = False
        for index, document in enumerate(documents, start=1):
            if max_docs is not None and index > max_docs:
                store.increment_stat(source_id, "bounded_run_stop")
                break

            store.increment_stat(source_id, "raw_documents")
            store.increment_stat(source_id, "raw_bytes", len(document.text.encode("utf-8")))
            chunks = list(
                split_long_document(document, int(config["cleaning"]["max_chars"]))
            )
            if len(chunks) > 1:
                store.increment_stat(source_id, "chunked_raw_documents")
                store.increment_stat(source_id, "chunks_emitted", len(chunks))

            for chunk in chunks:
                result = clean_text(chunk.text, config["cleaning"])
                if result.text is None:
                    reason = f"reject:{result.reason}"
                    store.increment_stat(source_id, reason)
                    sampler.add(source_id, reason, chunk, result.metrics)
                    continue

                lid_label: str | None = None
                lid_score: float | None = None
                if source.get("require_lid", True):
                    language = lid.predict(result.text)
                    lid_label = language.label
                    lid_score = language.score
                    result.metrics["lid_alternatives"] = language.alternatives
                    if not lid.accepts(language):
                        reason = "reject:language_id"
                        store.increment_stat(source_id, reason)
                        sampler.add(source_id, reason, chunk, result.metrics)
                        continue
                elif upstream_lid_field:
                    lid_label = config["language_id"]["expected_label"]
                    value = chunk.metadata.get(upstream_lid_field)
                    lid_score = float(value) if value is not None else None

                text_sha256 = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
                document_id = store.insert_document(
                    source_id=source_id,
                    upstream_id=chunk.upstream_id,
                    url=chunk.url,
                    license_name=source["license"],
                    text=result.text,
                    text_sha256=text_sha256,
                    metrics=result.metrics,
                    metadata=chunk.metadata,
                    transformations=result.transformations,
                    lid_label=lid_label,
                    lid_score=lid_score,
                )
                if document_id is None:
                    store.increment_stat(source_id, "exact_duplicate")
                    continue

                accepted = int(result.metrics["byte_length"])
                accepted_bytes += accepted
                store.increment_stat(source_id, "accepted_documents")
                store.increment_stat(source_id, "accepted_bytes", accepted)
                for key, count in result.transformations.items():
                    if count:
                        store.increment_stat(source_id, f"transform:{key}", int(count))

                if max_accepted_bytes and accepted_bytes >= int(max_accepted_bytes):
                    store.increment_stat(source_id, "accepted_byte_cap_reached")
                    byte_cap_reached = True
                    break

            if index % 1000 == 0:
                store.commit()
                LOGGER.info(
                    "%s processed=%d accepted_bytes=%.1f MiB",
                    source_id,
                    index,
                    accepted_bytes / 1024 / 1024,
                )

            if byte_cap_reached:
                break

        store.finish_source(source_id, accepted_bytes)
        LOGGER.info("Completed %s with %.1f MiB accepted", source_id, accepted_bytes / 1024 / 1024)

    sampler.write(artifacts_dir / "audit" / "rejected-samples.jsonl")


class SplitShardWriter:
    def __init__(self, root: Path, split: str):
        self.root = root
        self.split = split
        self.index = -1
        self.bytes_in_shard = 0
        self.json_stream = None
        self.text_stream = None
        self.files: list[dict[str, Any]] = []

    def _open(self) -> None:
        self.index += 1
        self.bytes_in_shard = 0
        self.root.mkdir(parents=True, exist_ok=True)
        json_path = self.root / f"{self.split}-{self.index:05d}.jsonl.zst"
        text_path = self.root / f"{self.split}-{self.index:05d}.txt.zst"
        self.json_stream = zstandard.ZstdCompressor(level=6).stream_writer(
            json_path.open("wb")
        )
        self.text_stream = zstandard.ZstdCompressor(level=6).stream_writer(
            text_path.open("wb")
        )
        self.files.append({"jsonl": json_path, "text": text_path})

    def write(self, record: dict[str, Any]) -> int:
        text = str(record["text"])
        payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        text_payload = (text + "\n\n").encode("utf-8")
        if self.json_stream is None or self.bytes_in_shard >= SHARD_BYTES:
            self.close_current()
            self._open()
        self.json_stream.write(payload)
        self.text_stream.write(text_payload)
        self.bytes_in_shard += len(text_payload)
        return len(text.encode("utf-8"))

    def close_current(self) -> None:
        if self.json_stream is not None:
            self.json_stream.close()
            self.text_stream.close()
            self.json_stream = None
            self.text_stream = None

    def close(self) -> None:
        self.close_current()


def split_for_hash(text_sha256: str, mixture: dict) -> str:
    bucket = int(text_sha256[:16], 16) % int(mixture["validation_modulus"])
    return "validation" if bucket in set(mixture["validation_buckets"]) else "train"


def output_file_manifest(files: list[dict[str, Path]]) -> list[dict[str, Any]]:
    manifest = []
    for pair in files:
        record: dict[str, Any] = {}
        for format_name, path in pair.items():
            record[format_name] = {
                "path": str(path.relative_to(Path.cwd())),
                "compressed_bytes": path.stat().st_size,
                "sha256": file_hash(path, "sha256"),
            }
        manifest.append(record)
    return manifest


def export_mixture(store: CorpusStore, config: dict) -> dict[str, Any]:
    output_dir = resolve_path(config["paths"]["processed_dir"])
    repository_root = Path.cwd().resolve()
    if output_dir.exists():
        safe_remove(output_dir, repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    mixture = config["mixture"]
    target_bytes = int(mixture["target_bytes"])
    source_caps = {key: int(value) for key, value in mixture.get("max_bytes", {}).items()}
    writers = {
        "train": SplitShardWriter(output_dir, "train"),
        "validation": SplitShardWriter(output_dir, "validation"),
    }
    totals: dict[str, Any] = {
        "target_bytes": target_bytes,
        "selected_bytes": 0,
        "selected_documents": 0,
        "splits": defaultdict(lambda: {"documents": 0, "bytes": 0}),
        "sources": defaultdict(lambda: {"documents": 0, "bytes": 0}),
    }

    try:
        for source_id in mixture["source_order"]:
            source_bytes = 0
            source_cap = source_caps.get(source_id, target_bytes)
            for row in store.iter_unique_source(source_id):
                byte_length = int(row["byte_length"])
                if source_bytes + byte_length > source_cap:
                    break
                if totals["selected_bytes"] + byte_length > target_bytes:
                    break

                split = split_for_hash(str(row["text_sha256"]), mixture)
                record = {
                    "id": int(row["id"]),
                    "source_id": str(row["source_id"]),
                    "upstream_id": str(row["upstream_id"]),
                    "url": row["url"],
                    "license": str(row["license"]),
                    "text": str(row["text"]),
                    "text_sha256": str(row["text_sha256"]),
                    "lid_label": row["lid_label"],
                    "lid_score": row["lid_score"],
                    "metrics": json.loads(row["metrics_json"]),
                    "metadata": json.loads(row["metadata_json"]),
                    "transformations": json.loads(row["transformations_json"]),
                }
                actual_bytes = writers[split].write(record)
                source_bytes += actual_bytes
                totals["selected_bytes"] += actual_bytes
                totals["selected_documents"] += 1
                totals["splits"][split]["documents"] += 1
                totals["splits"][split]["bytes"] += actual_bytes
                totals["sources"][source_id]["documents"] += 1
                totals["sources"][source_id]["bytes"] += actual_bytes

            if totals["selected_bytes"] >= target_bytes:
                break
    finally:
        for writer in writers.values():
            writer.close()

    totals["splits"] = dict(totals["splits"])
    totals["sources"] = dict(totals["sources"])
    totals["files"] = {
        split: output_file_manifest(writer.files) for split, writer in writers.items()
    }
    return totals


def run_pipeline(
    config_path: Path,
    *,
    command: str,
    reset: bool = False,
    selected_sources: set[str] | None = None,
    max_docs: int | None = None,
) -> dict[str, Any] | None:
    config, config_hash = load_config(config_path)
    database_path = resolve_path(config["paths"]["database"])
    repository_root = Path.cwd().resolve()

    if reset:
        safe_remove(database_path, repository_root)
        safe_remove(database_path.with_suffix(database_path.suffix + "-wal"), repository_root)
        safe_remove(database_path.with_suffix(database_path.suffix + "-shm"), repository_root)
        safe_remove(resolve_path(config["paths"]["processed_dir"]), repository_root)
        safe_remove(resolve_path(config["paths"]["artifacts_dir"]), repository_root)

    store = CorpusStore(database_path, config_hash)
    export_stats = None
    try:
        if command in {"collect", "build"}:
            collect_sources(
                store,
                config,
                selected_sources=selected_sources,
                max_docs=max_docs,
            )
        if command in {"dedup", "build"}:
            if selected_sources or max_docs:
                LOGGER.warning("Near-dedup is running on a bounded source selection")
            dedup_stats = run_near_dedup(store, config["deduplication"])
            LOGGER.info("Near-dedup complete: %s", dedup_stats)
        if command in {"export", "build"}:
            if store.get_meta("near_dedup_complete") != "true":
                raise RuntimeError("Near-dedup must complete before export")
            export_stats = export_mixture(store, config)
            store.set_meta("export_stats", json.dumps(export_stats, sort_keys=True))
            store.commit()
            LOGGER.info("Exported %s", export_stats)
        if command in {"report", "build"}:
            if export_stats is None:
                stored_export = store.get_meta("export_stats")
                export_stats = json.loads(stored_export) if stored_export else None
            write_report(store, config, config_hash, export_stats)
        return export_stats
    finally:
        store.close()
