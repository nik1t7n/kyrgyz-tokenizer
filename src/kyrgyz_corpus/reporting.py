from __future__ import annotations

import json
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import CorpusStore


def percentile(sorted_values: list[int | float], fraction: float) -> int | float | None:
    if not sorted_values:
        return None
    index = round((len(sorted_values) - 1) * fraction)
    return sorted_values[index]


def quality_summary(store: CorpusStore) -> dict[str, Any]:
    values: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "byte_lengths": [],
            "char_lengths": [],
            "word_counts": [],
            "lid_scores": [],
            "characters": Counter(),
            "non_nfc_documents": 0,
        }
    )
    for row in store.quality_rows():
        bucket = values[str(row["source_id"])]
        bucket["byte_lengths"].append(int(row["byte_length"]))
        bucket["char_lengths"].append(int(row["char_length"]))
        bucket["word_counts"].append(int(row["word_count"]))
        if row["lid_score"] is not None:
            bucket["lid_scores"].append(float(row["lid_score"]))
        text = str(row["text"])
        bucket["characters"].update(text)
        if not unicodedata.is_normalized("NFC", text):
            bucket["non_nfc_documents"] += 1

    summary: dict[str, Any] = {}
    for source_id, bucket in values.items():
        for key in ("byte_lengths", "char_lengths", "word_counts", "lid_scores"):
            bucket[key].sort()
        scores = bucket["lid_scores"]
        summary[source_id] = {
            "documents": len(bucket["byte_lengths"]),
            "byte_length": {
                "p10": percentile(bucket["byte_lengths"], 0.10),
                "p50": percentile(bucket["byte_lengths"], 0.50),
                "p90": percentile(bucket["byte_lengths"], 0.90),
                "max": percentile(bucket["byte_lengths"], 1.0),
            },
            "char_length": {
                "p10": percentile(bucket["char_lengths"], 0.10),
                "p50": percentile(bucket["char_lengths"], 0.50),
                "p90": percentile(bucket["char_lengths"], 0.90),
                "max": percentile(bucket["char_lengths"], 1.0),
            },
            "word_count": {
                "p10": percentile(bucket["word_counts"], 0.10),
                "p50": percentile(bucket["word_counts"], 0.50),
                "p90": percentile(bucket["word_counts"], 0.90),
                "max": percentile(bucket["word_counts"], 1.0),
            },
            "lid_score": {
                "count": len(scores),
                "min": percentile(scores, 0.0),
                "p10": percentile(scores, 0.10),
                "p50": percentile(scores, 0.50),
                "p90": percentile(scores, 0.90),
            },
            "non_nfc_documents": bucket["non_nfc_documents"],
            "unique_characters": len(bucket["characters"]),
            "top_characters": [
                {"character": char, "codepoint": f"U+{ord(char):04X}", "count": count}
                for char, count in bucket["characters"].most_common(50)
            ],
        }
    return summary


def write_accepted_samples(store: CorpusStore, path: Path, limit_per_source: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for source in store.source_summary():
            for row in store.accepted_sample_rows(str(source["source_id"]), limit_per_source):
                record = {
                    "source_id": str(row["source_id"]),
                    "upstream_id": str(row["upstream_id"]),
                    "url": row["url"],
                    "lid_label": row["lid_label"],
                    "lid_score": row["lid_score"],
                    "metrics": json.loads(str(row["metrics_json"])),
                    "metadata": json.loads(str(row["metadata_json"])),
                    "text": str(row["text"])[:2000],
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def write_report(
    store: CorpusStore,
    config: dict,
    config_hash: str,
    export_stats: dict[str, Any] | None,
) -> None:
    artifacts_dir = Path(config["paths"]["artifacts_dir"]).resolve()
    report_dir = artifacts_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    quality = quality_summary(store)
    write_accepted_samples(store, artifacts_dir / "audit" / "accepted-samples.jsonl")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_version": config["version"],
        "git_revision": git_revision(),
        "config_sha256": config_hash,
        "sources": store.source_summary(),
        "source_locks": store.source_locks(),
        "stats": store.stats_summary(),
        "quality": quality,
        "export": export_stats,
    }
    (report_dir / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    stats_by_source: dict[str, dict[str, int]] = {}
    for row in report["stats"]:
        stats_by_source.setdefault(row["source_id"], {})[row["metric"]] = row["value"]

    lines = [
        f"# {config['version']} build report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Git revision: `{report['git_revision']}`",
        f"Config SHA-256: `{config_hash}`",
        "",
        "## Source summary",
        "",
        "| Source | Status | Exact-unique docs | Near-unique docs | Near-unique bytes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source in report["sources"]:
        lines.append(
            f"| {source['source_id']} | {source['status']} | {source['exact_unique_docs']:,} | "
            f"{source['near_unique_docs']:,} | {source['near_unique_bytes']:,} |"
        )

    lines.extend(["", "## Rejections and transformations", ""])
    for source_id, stats in sorted(stats_by_source.items()):
        lines.append(f"### {source_id}")
        lines.append("")
        for metric, value in sorted(stats.items()):
            lines.append(f"- `{metric}`: {value:,}")
        lines.append("")

    lines.extend(
        [
            "## Quality profile after near-deduplication",
            "",
            "| Source | Documents | Byte p10 | Byte p50 | Byte p90 | LID min | LID p50 | Non-NFC docs | Unique characters |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source_id, values in quality.items():
        lid = values["lid_score"]
        lid_min = f"{lid['min']:.3f}" if lid["min"] is not None else "n/a"
        lid_p50 = f"{lid['p50']:.3f}" if lid["p50"] is not None else "n/a"
        lengths = values["byte_length"]
        lines.append(
            f"| {source_id} | {values['documents']:,} | {lengths['p10']:,} | "
            f"{lengths['p50']:,} | {lengths['p90']:,} | {lid_min} | {lid_p50} | "
            f"{values['non_nfc_documents']:,} | {values['unique_characters']:,} |"
        )
    lines.append("")

    if export_stats:
        lines.extend(
            [
                "## Export",
                "",
                f"Selected documents: {export_stats['selected_documents']:,}",
                f"Selected UTF-8 bytes: {export_stats['selected_bytes']:,}",
                "",
                "### Splits",
                "",
                "| Split | Documents | UTF-8 bytes |",
                "| --- | ---: | ---: |",
            ]
        )
        for split, values in sorted(export_stats["splits"].items()):
            lines.append(
                f"| {split} | {values['documents']:,} | {values['bytes']:,} |"
            )

        lines.extend(
            [
                "",
                "### Selected source mixture",
                "",
                "| Source | Documents | UTF-8 bytes |",
                "| --- | ---: | ---: |",
            ]
        )
        for source_id, values in export_stats["sources"].items():
            lines.append(
                f"| {source_id} | {values['documents']:,} | {values['bytes']:,} |"
            )

        lines.extend(
            [
                "",
                "### Output manifest",
                "",
                "| Split | Format | Compressed bytes | SHA-256 | Path |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for split, shards in sorted(export_stats["files"].items()):
            for shard in shards:
                for format_name, file_info in sorted(shard.items()):
                    lines.append(
                        f"| {split} | {format_name} | "
                        f"{file_info['compressed_bytes']:,} | `{file_info['sha256']}` | "
                        f"`{file_info['path']}` |"
                    )
        lines.append("")

    (report_dir / "build-report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
