from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from tokenizers import Tokenizer

from .benchmarks import prepare_benchmarks
from .evaluation import evaluate_tokenizers
from .release import release_tokenizer
from .reporting import write_evaluation_report
from .training import train_tokenizers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and evaluate the Kyrgyz tokenizer")
    parser.add_argument(
        "command",
        choices=("train", "prepare-benchmarks", "evaluate", "report", "release", "inspect", "build"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/tokenizer-v1.yaml"),
    )
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--vocab-size", type=int)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--text")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command in {"train", "build"}:
        train_tokenizers(args.config, reset=args.reset)
    if args.command in {"prepare-benchmarks", "build"}:
        prepare_benchmarks(args.config)
    if args.command in {"evaluate", "build"}:
        evaluate_tokenizers(args.config)
    if args.command in {"report", "build"}:
        print(write_evaluation_report(args.config))
    if args.command == "release":
        if args.vocab_size is None:
            raise SystemExit("--vocab-size is required for release")
        print(json.dumps(release_tokenizer(args.config, args.vocab_size), ensure_ascii=False, indent=2))
    if args.command == "inspect":
        if args.model is None or args.text is None:
            raise SystemExit("--model and --text are required for inspect")
        tokenizer = Tokenizer.from_file(str(args.model))
        encoding = tokenizer.encode(args.text, add_special_tokens=False)
        print(json.dumps({"ids": encoding.ids, "tokens": encoding.tokens, "decoded": tokenizer.decode(encoding.ids)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
