from __future__ import annotations

import logging
import re
from collections import OrderedDict

from datasketch import MinHash, MinHashLSH

from .store import CorpusStore


LOGGER = logging.getLogger(__name__)
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def shingles(text: str, n: int) -> set[str]:
    words = WORD_RE.findall(text.lower())
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[index : index + n]) for index in range(len(words) - n + 1)}


def minhash_for(values: set[str], num_perm: int) -> MinHash:
    signature = MinHash(num_perm=num_perm)
    for value in sorted(values):
        signature.update(value.encode("utf-8"))
    return signature


def jaccard(left: set[str], right: set[str]) -> float:
    union = len(left | right)
    return len(left & right) / union if union else 1.0


class ShingleCache:
    def __init__(self, store: CorpusStore, n: int, max_items: int = 2048):
        self.store = store
        self.n = n
        self.max_items = max_items
        self.items: OrderedDict[int, set[str]] = OrderedDict()

    def get(self, document_id: int) -> set[str]:
        if document_id in self.items:
            value = self.items.pop(document_id)
            self.items[document_id] = value
            return value
        value = shingles(self.store.document_text(document_id), self.n)
        self.items[document_id] = value
        if len(self.items) > self.max_items:
            self.items.popitem(last=False)
        return value


def run_near_dedup(store: CorpusStore, config: dict) -> dict[str, int]:
    threshold = float(config["threshold"])
    num_perm = int(config["num_perm"])
    ngram_size = int(config["word_ngram_size"])

    store.reset_near_duplicates()
    index = MinHashLSH(threshold=threshold, num_perm=num_perm)
    cache = ShingleCache(store, ngram_size)
    kept = 0
    removed = 0

    for position, row in enumerate(store.iter_for_near_dedup(), start=1):
        document_id = int(row["id"])
        values = shingles(str(row["text"]), ngram_size)
        signature = minhash_for(values, num_perm)
        candidate_ids = sorted(int(item) for item in index.query(signature))

        retained_id = None
        for candidate_id in candidate_ids:
            if jaccard(values, cache.get(candidate_id)) >= threshold:
                retained_id = candidate_id
                break

        if retained_id is not None:
            store.mark_near_duplicate(document_id, retained_id)
            removed += 1
        else:
            index.insert(str(document_id), signature)
            kept += 1

        if position % 5000 == 0:
            store.commit()
            LOGGER.info(
                "Near-dedup processed %d documents: kept=%d removed=%d",
                position,
                kept,
                removed,
            )

    store.set_meta("near_dedup_complete", "true")
    store.commit()
    return {"kept": kept, "removed": removed}
