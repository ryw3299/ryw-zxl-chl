"""
BM25-based lexical retrieval for lesson chunks.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from .chunking import ChunkRecord

try:
    import jieba  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    jieba = None

try:
    from rank_bm25 import BM25Okapi  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    BM25Okapi = None


class BM25Store:
    """Lexical retriever for ChunkRecord collections."""

    def __init__(self, chunks: Iterable[ChunkRecord] | None = None):
        self._chunks: list[ChunkRecord] = []
        self._tokenized_docs: list[list[str]] = []
        self._bm25 = None
        if chunks is not None:
            self.build(chunks)

    @property
    def size(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunks)

    def build(self, chunks: Iterable[ChunkRecord]) -> None:
        """Build lexical index from chunks."""
        self._chunks = list(chunks)
        self._tokenized_docs = [self.tokenize(chunk.text) for chunk in self._chunks]
        if BM25Okapi is not None and self._tokenized_docs:
            self._bm25 = BM25Okapi(self._tokenized_docs)
        else:
            self._bm25 = None

    def search(
        self,
        query: str,
        *,
        k: int = 10,
        source_filter: list[str] | None = None,
    ) -> list[tuple[ChunkRecord, float]]:
        """Search chunks with BM25 or a simple lexical fallback."""
        if not self._chunks:
            return []

        tokens = self.tokenize(query)
        if not tokens:
            return []

        fallback_scores = [self._fallback_score(tokens, doc_tokens) for doc_tokens in self._tokenized_docs]
        if self._bm25 is not None:
            bm25_scores = list(self._bm25.get_scores(tokens))
            scores = [
                max(float(bm25_score), fallback_score)
                for bm25_score, fallback_score in zip(bm25_scores, fallback_scores)
            ]
        else:
            scores = fallback_scores

        ranked: list[tuple[ChunkRecord, float]] = []
        for chunk, score in zip(self._chunks, scores):
            if source_filter and chunk.source_type not in source_filter:
                continue
            if score > 0:
                ranked.append((chunk, float(score)))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:k]

    def save(self, path: str | Path) -> None:
        """Persist chunk metadata for rebuilding lexical index."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        payload = [chunk.to_dict() for chunk in self._chunks]
        (path / "bm25_chunks.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> BM25Store:
        """Load lexical store from persisted chunk metadata."""
        path = Path(path)
        data = json.loads((path / "bm25_chunks.json").read_text(encoding="utf-8"))
        chunks = [ChunkRecord.from_dict(item) for item in data]
        return cls(chunks)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize Chinese/English mixed text for lexical retrieval."""
        normalized = (text or "").strip().lower()
        if not normalized:
            return []

        if jieba is not None:
            tokens = [token.strip() for token in jieba.lcut_for_search(normalized) if token.strip()]
        else:
            tokens = _fallback_tokenize(normalized)

        return [token for token in tokens if token]

    @staticmethod
    def _fallback_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        overlap = sum(1 for token in query_tokens if token in doc_tokens)
        return overlap / max(len(query_tokens), 1)


def _fallback_tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for part in re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_]+", text):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            if len(part) == 1:
                tokens.append(part)
                continue
            tokens.append(part)
            tokens.extend(part[idx : idx + 2] for idx in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens
