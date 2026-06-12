"""
Vector store abstractions for student retrieval.

Provides both a NumPy fallback implementation and a FAISS-backed dense index.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    faiss = None


@dataclass
class VectorEntry:
    """A single entry in the vector store."""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseVectorStore(ABC):
    """Shared interface for dense vector stores."""

    def __init__(self, dimension: Optional[int] = None):
        self._dimension = dimension
        self._entries: dict[str, VectorEntry] = {}

    @property
    def dimension(self) -> Optional[int]:
        return self._dimension

    @property
    def size(self) -> int:
        return len(self._entries)

    def add(
        self,
        id: str,
        vector: list[float],
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        if self._dimension is None:
            self._dimension = len(vector)
        if len(vector) != self._dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self._dimension}, got {len(vector)}")
        self._entries[id] = VectorEntry(
            id=id,
            vector=list(vector),
            text=text,
            metadata=metadata or {},
        )
        self._invalidate_cache()
        return id

    def add_batch(
        self,
        vectors: list[list[float]],
        texts: list[str],
        ids: Optional[list[str]] = None,
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> list[str]:
        if len(vectors) != len(texts):
            raise ValueError("vectors and texts must have the same length")

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if metadatas is None:
            metadatas = [{} for _ in vectors]

        for vector, text, entry_id, metadata in zip(vectors, texts, ids, metadatas):
            self.add(entry_id, vector, text, metadata)
        return ids

    def get(self, id: str) -> Optional[VectorEntry]:
        return self._entries.get(id)

    def delete(self, id: str) -> bool:
        if id in self._entries:
            del self._entries[id]
            self._invalidate_cache()
            return True
        return False

    def search_by_text(
        self,
        query_text: str,
        embedder,
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[tuple[VectorEntry, float]]:
        query_vector = embedder.embed_query(query_text)
        return self.search(query_vector, k=k, score_threshold=score_threshold)

    def save(self, path: str | Path) -> None:
        """Persist dense vectors and metadata to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        ids = list(self._entries.keys())
        vectors = np.array([self._entries[entry_id].vector for entry_id in ids], dtype=np.float32)
        payload = {
            "dimension": self._dimension,
            "entries": [
                {
                    "id": entry_id,
                    "text": self._entries[entry_id].text,
                    "metadata": self._entries[entry_id].metadata,
                }
                for entry_id in ids
            ],
        }
        np.save(path / "vectors.npy", vectors)
        (path / "entries.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> BaseVectorStore:
        """Load persisted dense vectors and metadata."""
        path = Path(path)
        payload = json.loads((path / "entries.json").read_text(encoding="utf-8"))
        vectors = np.load(path / "vectors.npy")
        store = cls(dimension=payload.get("dimension"))
        entries = payload.get("entries", [])
        ids = [entry["id"] for entry in entries]
        texts = [entry.get("text", "") for entry in entries]
        metadatas = [entry.get("metadata", {}) for entry in entries]
        store.add_batch(
            vectors=vectors.tolist(),
            texts=texts,
            ids=ids,
            metadatas=metadatas,
        )
        return store

    def clear(self) -> None:
        self._entries.clear()
        self._invalidate_cache()

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[tuple[VectorEntry, float]]:
        """Search for the k most similar vectors."""

    @abstractmethod
    def _invalidate_cache(self) -> None:
        """Invalidate any cached search index."""


class NumpyVectorStore(BaseVectorStore):
    """NumPy-based cosine similarity store used as a fallback."""

    def __init__(self, dimension: Optional[int] = None):
        super().__init__(dimension=dimension)
        self._vectors_matrix: Optional[np.ndarray] = None
        self._ids_list: list[str] = []

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[tuple[VectorEntry, float]]:
        if not self._entries:
            return []
        if len(query_vector) != self._dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self._dimension}, got {len(query_vector)}"
            )

        self._ensure_cache()
        query = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        denominator = np.linalg.norm(self._vectors_matrix, axis=1) * np.linalg.norm(query)
        denominator = np.where(denominator == 0, 1e-12, denominator)
        similarities = np.dot(self._vectors_matrix, query.T).flatten() / denominator
        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_indices:
            entry_id = self._ids_list[idx]
            score = float(similarities[idx])
            if score_threshold is None or score >= score_threshold:
                results.append((self._entries[entry_id], score))
        return results

    def _invalidate_cache(self) -> None:
        self._vectors_matrix = None
        self._ids_list = []

    def _ensure_cache(self) -> None:
        if self._vectors_matrix is None:
            self._ids_list = list(self._entries.keys())
            self._vectors_matrix = np.array(
                [self._entries[entry_id].vector for entry_id in self._ids_list],
                dtype=np.float32,
            )


class FaissVectorStore(BaseVectorStore):
    """FAISS-backed vector store using normalized inner-product search."""

    def __init__(self, dimension: Optional[int] = None):
        if faiss is None:
            raise RuntimeError("faiss is not installed. Install faiss-cpu to use FaissVectorStore.")
        super().__init__(dimension=dimension)
        self._index = None
        self._ids_list: list[str] = []

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[tuple[VectorEntry, float]]:
        if not self._entries:
            return []
        if len(query_vector) != self._dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self._dimension}, got {len(query_vector)}"
            )

        self._ensure_index()
        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)
        scores, indices = self._index.search(query, min(k, len(self._ids_list)))

        results: list[tuple[VectorEntry, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue
            entry_id = self._ids_list[idx]
            score_value = float(score)
            if score_threshold is None or score_value >= score_threshold:
                results.append((self._entries[entry_id], score_value))
        return results

    def _invalidate_cache(self) -> None:
        self._index = None
        self._ids_list = []

    def _ensure_index(self) -> None:
        if self._index is not None:
            return

        self._ids_list = list(self._entries.keys())
        vectors = np.array(
            [self._entries[entry_id].vector for entry_id in self._ids_list],
            dtype=np.float32,
        )
        if vectors.size == 0:
            self._index = None
            return

        faiss.normalize_L2(vectors)
        self._index = faiss.IndexFlatIP(vectors.shape[1])
        self._index.add(vectors)


class VectorStore(NumpyVectorStore):
    """Backward-compatible alias for the historical in-memory vector store."""


def create_vector_store(
    backend: str = "faiss",
    *,
    dimension: Optional[int] = None,
) -> BaseVectorStore:
    """
    Create a vector store by backend name.

    Falls back to NumPy when FAISS is unavailable so local tests can still run.
    """
    backend_name = (backend or "numpy").lower()
    if backend_name == "faiss":
        if faiss is not None:
            return FaissVectorStore(dimension=dimension)
        return NumpyVectorStore(dimension=dimension)
    return NumpyVectorStore(dimension=dimension)
