from __future__ import annotations

import gzip
import re
import unicodedata
from collections import Counter

from .models import CleanResult


RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
RE_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
RE_MANY_NEWLINES = re.compile(r"\n{3,}")
RE_URL = re.compile(r"https?://\S+", re.IGNORECASE)
RE_HTML_TAG = re.compile(r"<[^>]{1,500}>")
RE_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
RE_IPV4 = re.compile(
    r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)"
)
RE_RESIDUAL_WIKI_MARKUP = re.compile(r"\[\[|\]\]|\{\{|\}\}|\bthumb\|", re.IGNORECASE)
RE_WORD = re.compile(r"[^\W_]+", re.UNICODE)
KYRGYZ_SPECIFIC = frozenset("ҢңӨөҮү")


def normalize_text(text: str, max_chars: int, redact_pii: bool) -> tuple[str, dict[str, int]]:
    transformations: dict[str, int] = {
        "control_chars_removed": 0,
        "emails_redacted": 0,
        "ipv4_redacted": 0,
        "residual_wiki_markup_removed": 0,
        "truncated": 0,
    }

    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text, transformations["control_chars_removed"] = RE_CONTROL.subn("", text)

    if redact_pii:
        text, transformations["emails_redacted"] = RE_EMAIL.subn(" ", text)
        text, transformations["ipv4_redacted"] = RE_IPV4.subn(" ", text)

    text, transformations["residual_wiki_markup_removed"] = RE_RESIDUAL_WIKI_MARKUP.subn(
        " ", text
    )

    text = "\n".join(RE_HORIZONTAL_SPACE.sub(" ", line).strip() for line in text.splitlines())
    text = RE_MANY_NEWLINES.sub("\n\n", text).strip()

    if len(text) > max_chars:
        cut = text.rfind("\n\n", 0, max_chars)
        if cut < max_chars // 2:
            cut = text.rfind("\n", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        text = text[:cut].rstrip()
        transformations["truncated"] = 1

    return text, transformations


def script_metrics(text: str) -> dict[str, float | int]:
    nonspace = [char for char in text if not char.isspace()]
    alpha = [char for char in nonspace if char.isalpha()]
    cyrillic = sum("\u0400" <= char <= "\u052f" for char in alpha)
    latin = sum(char.isascii() and char.isalpha() for char in alpha)
    special = sum(not char.isalnum() for char in nonspace)
    kyrgyz_specific = sum(char in KYRGYZ_SPECIFIC for char in text)

    return {
        "alpha_ratio": len(alpha) / max(1, len(nonspace)),
        "cyrillic_ratio": cyrillic / max(1, len(alpha)),
        "latin_ratio": latin / max(1, len(alpha)),
        "special_char_ratio": special / max(1, len(nonspace)),
        "kyrgyz_specific_chars": kyrgyz_specific,
    }


def repeated_line_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) >= 20]
    if len(lines) < 2:
        return 0.0
    counts = Counter(lines)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / len(lines)


def repeated_ngram_ratio(text: str, n: int) -> float:
    words = RE_WORD.findall(text.lower())[:50_000]
    if len(words) < n * 2:
        return 0.0
    counts = Counter(tuple(words[index : index + n]) for index in range(len(words) - n + 1))
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / max(1, len(words) - n + 1)


def gzip_ratio(text: str) -> float:
    encoded = text.encode("utf-8")
    if not encoded:
        return 1.0
    return len(gzip.compress(encoded, compresslevel=6)) / len(encoded)


def clean_text(raw_text: str, config: dict) -> CleanResult:
    text, transformations = normalize_text(
        raw_text,
        max_chars=int(config["max_chars"]),
        redact_pii=bool(config.get("redact_pii", True)),
    )

    byte_length = len(text.encode("utf-8"))
    words = RE_WORD.findall(text)
    metrics: dict[str, float | int] = {
        "char_length": len(text),
        "byte_length": byte_length,
        "word_count": len(words),
    }

    if len(text) < int(config["min_chars"]):
        return CleanResult(None, "too_short", metrics, transformations)

    url_density = len(RE_URL.findall(text)) / max(1.0, len(text) / 1000)
    html_tags = len(RE_HTML_TAG.findall(text))
    metrics["url_density"] = url_density
    metrics["html_tags"] = html_tags

    if url_density > float(config["max_urls_per_1000_chars"]):
        return CleanResult(None, "url_density", metrics, transformations)
    if html_tags > int(config["max_html_tags"]):
        return CleanResult(None, "html_tags", metrics, transformations)

    metrics.update(script_metrics(text))
    if metrics["alpha_ratio"] < float(config["min_alpha_ratio"]):
        return CleanResult(None, "low_alpha_ratio", metrics, transformations)
    if metrics["cyrillic_ratio"] < float(config["min_cyrillic_ratio"]):
        return CleanResult(None, "low_cyrillic_ratio", metrics, transformations)
    if metrics["latin_ratio"] > float(config["max_latin_ratio"]):
        return CleanResult(None, "high_latin_ratio", metrics, transformations)
    if metrics["special_char_ratio"] > float(config["max_special_char_ratio"]):
        return CleanResult(None, "high_special_ratio", metrics, transformations)

    line_ratio = repeated_line_ratio(text)
    ngram_ratio = repeated_ngram_ratio(text, int(config["repeated_ngram_size"]))
    compressed_ratio = gzip_ratio(text)
    metrics["repeated_line_ratio"] = line_ratio
    metrics["repeated_ngram_ratio"] = ngram_ratio
    metrics["gzip_ratio"] = compressed_ratio

    if line_ratio > float(config["max_repeated_line_ratio"]):
        return CleanResult(None, "repeated_lines", metrics, transformations)
    if ngram_ratio > float(config["max_repeated_ngram_ratio"]):
        return CleanResult(None, "repeated_ngrams", metrics, transformations)
    if compressed_ratio < float(config["min_gzip_ratio"]):
        return CleanResult(None, "template_repetition", metrics, transformations)

    return CleanResult(text, None, metrics, transformations)
