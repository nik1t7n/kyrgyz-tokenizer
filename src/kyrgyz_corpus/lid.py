from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download

from .models import LanguageResult


class GlotLID:
    def __init__(self, config: dict, cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir
        self._model = None
        self.model_path: str | None = None

    def load(self):
        if self._model is not None:
            return self._model

        import fasttext

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = hf_hub_download(
            repo_id=self.config["repo_id"],
            revision=self.config["revision"],
            filename=self.config["filename"],
            cache_dir=self.cache_dir,
        )
        self._model = fasttext.load_model(self.model_path)
        return self._model

    def predict(self, text: str) -> LanguageResult:
        model = self.load()
        sample = " ".join(text[: int(self.config["sample_chars"])].splitlines())
        labels, scores = model.predict(sample, k=3)
        alternatives = [(str(label), float(score)) for label, score in zip(labels, scores)]
        return LanguageResult(
            label=alternatives[0][0],
            score=alternatives[0][1],
            alternatives=alternatives,
        )

    def accepts(self, result: LanguageResult) -> bool:
        return (
            result.label == self.config["expected_label"]
            and result.score >= float(self.config["min_score"])
        )
