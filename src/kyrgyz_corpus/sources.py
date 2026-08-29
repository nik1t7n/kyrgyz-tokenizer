from __future__ import annotations

import bz2
import hashlib
import html
import io
import json
import logging
import os
import re
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import mwparserfromhell
from datasets import load_dataset

from .models import RawDocument


LOGGER = logging.getLogger(__name__)
USER_AGENT = "kyrgyz-tokenizer-corpus/0.1 (+https://github.com/nik1t7n/kyrgyz-tokenizer)"
ATTRIBUTE_RE = re.compile(r'(\w+)="([^"]*)"')
HIDDEN_WIKI_NAMESPACES = frozenset(
    {"category", "file", "image", "media", "категория", "файл", "сүрөт"}
)
WIKI_TRAILING_SECTION_RE = re.compile(
    r"(?im)^==+\s*(?:"
    r"булактар|тышкы шилтемелер|шилтемелер|колдонулган адабияттар|"
    r"дагы караңыз|эскертүүлөр|ссылки|примечания|литература"
    r")\s*==+\s*$"
)
HIDDEN_WIKI_TAGS = frozenset({"gallery", "ref", "references"})


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    destination: Path,
    *,
    expected_hash: str | None = None,
    hash_algorithm: str = "sha256",
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        actual = file_hash(destination, hash_algorithm)
        if expected_hash is None or actual == expected_hash:
            return {
                "url": url,
                "path": str(destination),
                "size": destination.stat().st_size,
                hash_algorithm: actual,
                "reused": True,
            }
        destination.unlink()

    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    os.replace(temporary, destination)

    actual = file_hash(destination, hash_algorithm)
    if expected_hash is not None and actual != expected_hash:
        destination.unlink(missing_ok=True)
        raise ValueError(
            f"Checksum mismatch for {url}: expected {expected_hash}, got {actual}"
        )
    return {
        "url": url,
        "path": str(destination),
        "size": destination.stat().st_size,
        hash_algorithm: actual,
        "reused": False,
    }


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8")


def iter_huggingface(source: dict) -> Iterator[RawDocument]:
    kwargs: dict[str, Any] = {
        "path": source["dataset"],
        "split": source.get("split", "train"),
        "streaming": True,
        "revision": source["revision"],
    }
    if source.get("subset"):
        kwargs["name"] = source["subset"]

    dataset = load_dataset(**kwargs)
    shuffle_seed = source.get("shuffle_seed")
    if shuffle_seed is not None:
        dataset = dataset.shuffle(
            seed=int(shuffle_seed),
            buffer_size=int(source.get("shuffle_buffer_size", 10_000)),
        )
    text_field = source.get("text_field", "text")
    id_field = source.get("id_field")
    url_field = source.get("url_field")
    metadata_fields = source.get("metadata_fields", [])

    for index, row in enumerate(dataset):
        text = row.get(text_field)
        if not isinstance(text, str) or not text:
            continue
        upstream_id = str(row.get(id_field)) if id_field and row.get(id_field) else f"{index:012d}"
        url = str(row.get(url_field)) if url_field and row.get(url_field) else None
        metadata = {field: row.get(field) for field in metadata_fields if field in row}
        yield RawDocument(
            source_id=source["id"],
            upstream_id=upstream_id,
            text=text,
            url=url,
            metadata=metadata,
        )


def _wiki_plain_text(wikitext: str) -> str:
    wikitext = WIKI_TRAILING_SECTION_RE.split(wikitext, maxsplit=1)[0]
    code = mwparserfromhell.parse(wikitext)
    for tag in code.filter_tags(recursive=True):
        if str(tag.tag).strip().casefold() in HIDDEN_WIKI_TAGS:
            try:
                code.remove(tag, recursive=True)
            except ValueError:
                pass
    for link in code.filter_wikilinks(recursive=True):
        namespace = str(link.title).partition(":")[0].strip().casefold()
        if namespace in HIDDEN_WIKI_NAMESPACES:
            try:
                code.remove(link, recursive=True)
            except ValueError:
                pass
    return str(code.strip_code(normalize=True, collapse=True)).strip()


def iter_wikimedia(source: dict, raw_dir: Path) -> tuple[Iterator[RawDocument], dict[str, Any]]:
    checksum_text = fetch_text(source["checksum_url"])
    expected_sha1 = None
    for line in checksum_text.splitlines():
        if line.rstrip().endswith(source["filename"]):
            expected_sha1 = line.split()[0]
            break
    if expected_sha1 is None:
        raise ValueError(f"No checksum found for {source['filename']}")

    archive_path = raw_dir / source["id"] / source["filename"]
    lock = download_file(
        source["url"],
        archive_path,
        expected_hash=expected_sha1,
        hash_algorithm="sha1",
    )
    lock["checksum_url"] = source["checksum_url"]

    def generate() -> Iterator[RawDocument]:
        with bz2.open(archive_path, "rb") as handle:
            for _event, page in ElementTree.iterparse(handle, events=("end",)):
                if not page.tag.endswith("}page"):
                    continue

                namespace = page.tag.removesuffix("page")
                namespace_id = page.findtext(f"{namespace}ns")
                redirect = page.find(f"{namespace}redirect")
                title = page.findtext(f"{namespace}title") or ""
                page_id = page.findtext(f"{namespace}id") or ""
                revision = page.find(f"{namespace}revision")

                if namespace_id == "0" and redirect is None and revision is not None:
                    revision_id = revision.findtext(f"{namespace}id") or ""
                    text = revision.findtext(f"{namespace}text") or ""
                    if text:
                        try:
                            plain = _wiki_plain_text(text)
                        except Exception as exc:
                            LOGGER.warning("Wikipedia parse failure for page %s: %s", page_id, exc)
                            plain = ""
                        if plain:
                            if title and not plain.startswith(title):
                                plain = f"{title}\n\n{plain}"
                            yield RawDocument(
                                source_id=source["id"],
                                upstream_id=page_id,
                                text=plain,
                                url=f"https://ky.wikipedia.org/?curid={page_id}",
                                metadata={"title": title, "revision_id": revision_id},
                            )
                page.clear()

    return generate(), lock


def _detokenize(tokens: list[str]) -> str:
    if not tokens:
        return ""
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:!?%…\)\]\}»])", r"\1", text)
    text = re.sub(r"([\(\[\{«])\s+", r"\1", text)
    text = re.sub(r"\s+([’'])\s+", r"\1", text)
    return text.strip()


def iter_manas(source: dict, raw_dir: Path) -> tuple[Iterator[RawDocument], dict[str, Any]]:
    archive_path = raw_dir / source["id"] / source["filename"]
    lock = download_file(
        source["url"],
        archive_path,
        expected_hash=source["sha1"],
        hash_algorithm="sha1",
    )

    def generate() -> Iterator[RawDocument]:
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(source["member"]) as binary:
                stream = io.TextIOWrapper(binary, encoding="utf-8")
                attributes: dict[str, str] | None = None
                sentences: list[str] = []
                tokens: list[str] = []

                for raw_line in stream:
                    line = raw_line.rstrip("\n")
                    if line.startswith("<text "):
                        attributes = {
                            key: html.unescape(value) for key, value in ATTRIBUTE_RE.findall(line)
                        }
                        sentences = []
                    elif line == "<s>":
                        tokens = []
                    elif line == "</s>":
                        sentence = _detokenize(tokens)
                        if sentence:
                            sentences.append(sentence)
                    elif line == "</text>" and attributes is not None:
                        text = " ".join(sentences).strip()
                        if text:
                            yield RawDocument(
                                source_id=source["id"],
                                upstream_id=attributes.get("id", hashlib.sha256(text.encode()).hexdigest()),
                                text=text,
                                url=attributes.get("source"),
                                metadata={
                                    key: value
                                    for key, value in attributes.items()
                                    if key not in {"id", "source"}
                                },
                            )
                        attributes = None
                    elif attributes is not None and line and not line.startswith("<"):
                        tokens.append(line.split("\t", 1)[0])

    return generate(), lock


def open_source(source: dict, raw_dir: Path) -> tuple[Iterator[RawDocument], dict[str, Any]]:
    kind = source["kind"]
    if kind == "huggingface":
        lock = {
            "dataset": source["dataset"],
            "subset": source.get("subset"),
            "split": source.get("split", "train"),
            "revision": source["revision"],
            "shuffle_seed": source.get("shuffle_seed"),
            "shuffle_buffer_size": source.get("shuffle_buffer_size"),
        }
        return iter_huggingface(source), lock
    if kind == "wikimedia_xml":
        return iter_wikimedia(source, raw_dir)
    if kind == "manas_vrt":
        return iter_manas(source, raw_dir)
    raise ValueError(f"Unknown source kind: {kind}")


def write_source_lock(path: Path, lock: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
