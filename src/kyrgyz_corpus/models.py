from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RawDocument:
    source_id: str
    upstream_id: str
    text: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CleanResult:
    text: str | None
    reason: str | None
    metrics: dict[str, float | int]
    transformations: dict[str, int]


@dataclass(slots=True)
class LanguageResult:
    label: str
    score: float
    alternatives: list[tuple[str, float]]
