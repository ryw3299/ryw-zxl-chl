"""
Factory helpers for cached HybridRetriever instances.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import RLock

from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript

from .config import RAGSettings, get_rag_settings
from .embedder import Embedder, create_embedder
from .hybrid_retriever import HybridRetriever

try:
    from cachetools import LRUCache  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    LRUCache = None


class RetrieverFactory:
    """Create and cache lesson-scoped retrievers."""

    _lock = RLock()
    _cache = None

    @classmethod
    def get_or_create(
        cls,
        *,
        structured_content: StructuredLessonContent,
        lesson_script: LessonScript | None = None,
        rag_settings: RAGSettings | None = None,
        embedder: Embedder | None = None,
        force_rebuild: bool | None = None,
    ) -> HybridRetriever:
        settings = rag_settings or get_rag_settings()
        cls._ensure_cache(settings)

        cache_key = cls.build_cache_key(structured_content, lesson_script)
        if force_rebuild is None:
            force_rebuild = settings.rebuild_index

        with cls._lock:
            cached = cls._cache.get(cache_key) if cls._cache is not None else None
            if cached is not None and not force_rebuild:
                return cached

        embedder = embedder or create_embedder()
        index_path = cls.get_index_path(structured_content, lesson_script, rag_settings=settings)

        if index_path.exists() and not force_rebuild:
            try:
                retriever = HybridRetriever.load_from_disk(
                    index_path,
                    structured_content=structured_content,
                    lesson_script=lesson_script,
                    embedder=embedder,
                    rag_settings=settings,
                )
            except Exception:
                retriever = cls._build_retriever(
                    structured_content=structured_content,
                    lesson_script=lesson_script,
                    rag_settings=settings,
                    embedder=embedder,
                )
                retriever.save_to_disk(index_path)
        else:
            retriever = cls._build_retriever(
                structured_content=structured_content,
                lesson_script=lesson_script,
                rag_settings=settings,
                embedder=embedder,
            )
            retriever.save_to_disk(index_path)

        with cls._lock:
            cls._cache[cache_key] = retriever
        return retriever

    @classmethod
    def build_cache_key(
        cls,
        structured_content: StructuredLessonContent,
        lesson_script: LessonScript | None,
    ) -> str:
        content_hash = cls._build_content_hash(structured_content, lesson_script)
        return f"{structured_content.lesson_id}:{content_hash}"

    @classmethod
    def get_index_path(
        cls,
        structured_content: StructuredLessonContent,
        lesson_script: LessonScript | None,
        *,
        rag_settings: RAGSettings | None = None,
    ) -> Path:
        settings = rag_settings or get_rag_settings()
        lesson_id = structured_content.lesson_id
        content_hash = cls._build_content_hash(structured_content, lesson_script)
        return settings.index_dir / lesson_id / content_hash

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-process retriever cache."""
        with cls._lock:
            if cls._cache is not None:
                cls._cache.clear()

    @classmethod
    def _build_retriever(
        cls,
        *,
        structured_content: StructuredLessonContent,
        lesson_script: LessonScript | None,
        rag_settings: RAGSettings,
        embedder: Embedder,
    ) -> HybridRetriever:
        return HybridRetriever(
            structured_content=structured_content,
            lesson_script=lesson_script,
            embedder=embedder,
            rag_settings=rag_settings,
            default_top_k=rag_settings.final_top_k,
            score_threshold=rag_settings.score_threshold,
        )

    @classmethod
    def _ensure_cache(cls, settings: RAGSettings) -> None:
        with cls._lock:
            if cls._cache is not None:
                return
            if LRUCache is not None:
                cls._cache = LRUCache(maxsize=settings.retriever_cache_size)
            else:
                cls._cache = _SimpleLRUCache(maxsize=settings.retriever_cache_size)

    @staticmethod
    def _build_content_hash(
        structured_content: StructuredLessonContent,
        lesson_script: LessonScript | None,
    ) -> str:
        payload = {
            "structured_content": structured_content.model_dump(mode="json"),
            "lesson_script": lesson_script.model_dump(mode="json") if lesson_script is not None else None,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()[:16]


class _SimpleLRUCache(dict):
    """Tiny OrderedDict-free fallback used when cachetools is unavailable."""

    def __init__(self, maxsize: int):
        super().__init__()
        self._order: list[str] = []
        self._maxsize = maxsize

    def __setitem__(self, key, value):  # type: ignore[override]
        if key in self:
            self._order.remove(key)
        super().__setitem__(key, value)
        self._order.append(key)
        while len(self._order) > self._maxsize:
            oldest = self._order.pop(0)
            super().__delitem__(oldest)

    def get(self, key, default=None):  # type: ignore[override]
        if key not in self:
            return default
        self._order.remove(key)
        self._order.append(key)
        return super().get(key, default)

    def clear(self):  # type: ignore[override]
        self._order.clear()
        super().clear()
