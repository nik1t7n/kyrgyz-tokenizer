from __future__ import annotations

import json
import subprocess
from pathlib import Path
from .config import load_config, resolve_path


def _percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _float(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_evaluation_report(config_path: Path) -> Path:
    config, config_sha256 = load_config(config_path)
    working_dir = resolve_path(config["paths"]["working_dir"])
    training = json.loads((working_dir / "training-manifest.json").read_text(encoding="utf-8"))
    evaluation = json.loads((working_dir / "evaluation-report.json").read_text(encoding="utf-8"))

    lines = [
        "# tokenizer-v1 evaluation report",
        "",
        f"Git revision: `{_git_revision()}`",
        "",
        f"Configuration SHA-256: `{config_sha256}`",
        "",
        "## Training",
        "",
        f"- Algorithm: {training['algorithm']}",
        f"- Pretokenizer: {training['pretokenizer']}",
        f"- Training time: {training['training_seconds']:.1f} seconds",
        "- Base alphabet: all 256 byte values",
        "- Runtime normalization: none",
        "- Special tokens: none",
        "- Nested vocabulary variants are prefixes of one deterministic 50K merge sequence.",
        "",
        "## Aggregate Kyrgyz benchmark",
        "",
        "External means UD-KTMU, UD-TueCL, Belebele, and SIB-200; corpus validation is excluded from that column.",
        "",
        "| Tokenizer | Vocabulary | External bytes/token | External tokens/word | External one-token words | UD suffix-boundary recall | Round-trip failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in evaluation["tokenizers"]:
        external = item["external_only"]
        morphology = item["morphology"]
        lines.append(
            f"| {item['id']} | {item['vocab_size']:,} | "
            f"{external['bytes_per_token']:.3f} | {external['sequence_fertility']:.3f} | "
            f"{_percent(external['single_token_word_rate'])} | "
            f"{_percent(morphology['lemma_suffix_boundary_recall'])} | "
            f"{item['aggregate']['roundtrip_failures']:,} |"
        )

    lines.extend(
        [
            "",
            "## Per-dataset compression",
            "",
            "| Tokenizer | Corpus validation | UD-KTMU | UD-TueCL | Belebele | SIB-200 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in evaluation["tokenizers"]:
        datasets = item["datasets"]
        lines.append(
            f"| {item['id']} | "
            + " | ".join(
                _float(datasets[key]["bytes_per_token"])
                for key in ("corpus-validation", "ud_ktmu", "ud_tuecl", "belebele", "sib200")
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Embedding-table cost",
            "",
            "The figures below are token-embedding parameter counts only; tied output embeddings have the same count and untied output projections double it.",
            "",
            "| Tokenizer | d=768 | d=2048 | d=4096 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in evaluation["tokenizers"]:
        parameters = item["embedding_parameters"]
        lines.append(
            f"| {item['id']} | {parameters['768']:,} | {parameters['2048']:,} | {parameters['4096']:,} |"
        )

    lines.extend(["", "## Unavailable requested baselines", ""])
    if evaluation["unavailable_baselines"]:
        for item in evaluation["unavailable_baselines"]:
            first_line = item["error"].splitlines()[0]
            lines.append(f"- `{item['id']}`: `{item['error_type']}` — {first_line}")
    else:
        lines.append("None.")

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Compression, fertility, and the UD lemma-boundary diagnostic are intrinsic measurements. They measure sequence efficiency and one narrow form of morphological alignment, not downstream language-model quality. The UD diagnostic is explicitly heuristic: it only covers inflected forms whose surface begins with the annotated lemma. A later model-training experiment is required for an extrinsic conclusion.",
            "",
        ]
    )

    output_path = working_dir / "evaluation-report.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
