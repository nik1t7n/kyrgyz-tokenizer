from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Kyrgyz tokenizer research corpus")
    parser.add_argument(
        "command",
        choices=("collect", "dedup", "export", "report", "build"),
        help="Pipeline stage to execute",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/corpus-v1.yaml"),
        help="Corpus configuration path",
    )
    parser.add_argument("--reset", action="store_true", help="Reset generated state before running")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Limit collection to one source ID; may be repeated",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        help="Bound each selected source for a real smoke run",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_pipeline(
        args.config,
        command=args.command,
        reset=args.reset,
        selected_sources=set(args.sources) if args.sources else None,
        max_docs=args.max_docs,
    )


if __name__ == "__main__":
    main()
