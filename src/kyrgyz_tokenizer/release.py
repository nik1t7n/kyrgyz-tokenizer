from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from tokenizers import Tokenizer

from .config import load_config, resolve_path, sha256_file


def release_tokenizer(config_path: Path, vocab_size: int) -> dict:
    config, config_sha256 = load_config(config_path)
    working_dir = resolve_path(config["paths"]["working_dir"])
    source = working_dir / "models" / f"bpe-{vocab_size}" / "tokenizer.json"
    if not source.exists():
        raise FileNotFoundError(f"Missing trained tokenizer: {source}")

    evaluation = json.loads((working_dir / "evaluation-report.json").read_text(encoding="utf-8"))
    result = next(
        (item for item in evaluation["tokenizers"] if item["id"] == f"kyrgyz-bpe-{vocab_size}"),
        None,
    )
    if result is None:
        raise RuntimeError(f"Vocabulary size {vocab_size} has not been evaluated")
    if result["aggregate"]["roundtrip_failures"]:
        raise RuntimeError("Refusing to release a tokenizer with round-trip failures")

    release_dir = resolve_path(config["paths"]["release_dir"])
    release_dir.mkdir(parents=True, exist_ok=True)
    destination = release_dir / "tokenizer.json"
    shutil.copyfile(source, destination)
    tokenizer = Tokenizer.from_file(str(destination))

    metadata = {
        "schema_version": 1,
        "released_at": datetime.now(timezone.utc).isoformat(),
        "id": f"kyrgyz-byte-bpe-v1-{vocab_size}",
        "algorithm": "byte-level BPE",
        "vocab_size": tokenizer.get_vocab_size(with_added_tokens=False),
        "base_byte_tokens": 256,
        "special_tokens": [],
        "normalizer": None,
        "config_sha256": config_sha256,
        "tokenizer_sha256": sha256_file(destination),
        "evaluation": result,
    }
    (release_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (release_dir / "README.md").write_text(
        "\n".join(
            [
                "# Kyrgyz Byte BPE v1",
                "",
                "## Historical baseline",
                "",
                f"This is the historical Kyrgyz-only {vocab_size:,}-token baseline. The current bilingual release candidate is [`kyrgyz-russian-byte-bpe-v2`](../kyrgyz-russian-byte-bpe-v2/).",
                "",
                "V1 is a no-UNK byte-level BPE trained on corpus-v1 with the published DeepSeek-V3 pre-tokenization structure. It performs no runtime Unicode normalization and defines no special tokens. Applications must add model-specific protocol tokens separately.",
                "",
                "## Usage",
                "",
                "```python",
                "from tokenizers import Tokenizer",
                "tokenizer = Tokenizer.from_file(\"tokenizer.json\")",
                "encoding = tokenizer.encode(\"Кыргыз тили\", add_special_tokens=False)",
                "assert tokenizer.decode(encoding.ids) == \"Кыргыз тили\"",
                "```",
                "",
                "## Limitations and rights",
                "",
                "This tokenizer was optimized for Kyrgyz, not Russian or natural mixed-language chat. No downstream language model was trained to validate it. Its training sources include non-commercial and share-alike material; the artifact is published for research inspection under the repository rights notice.",
                "",
                f"Tokenizer SHA-256: `{metadata['tokenizer_sha256']}`.",
                "",
                "See [`metadata.json`](metadata.json), [the v1 evaluation](../../docs/reports/TOKENIZER_V1_EVALUATION.md), and [the public release boundary](../../docs/PUBLIC_RELEASE.md).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata
