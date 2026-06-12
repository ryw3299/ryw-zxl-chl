"""
HybridRetriever module for chunk-level dense + lexical retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.schemas import RetrievedContextItem
from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript

from .bm25_store import BM25Store
from .chunking import ChunkBuilder, ChunkRecord
from .config import RAGSettings, get_rag_settings
from .constants import DEFAULT_TOP_K, RETRIEVAL_SCORE_THRESHOLD
from .content_getter import ContentGetter
from .embedder import Embedder, InMemoryEmbedder, create_embedder
from .helpers import map_to_retrieved_context_item
from .vector_store import BaseVectorStore, create_vector_store


class HybridRetriever:
    """
    Chunk-level hybrid retriever for student-side grounding.

    Dense search recalls semantically similar chunks, BM25 recalls exact lexical
    hits, and the final ranking applies lightweight teaching-context boosts.
    """

    def __init__(
        self,
        structured_content: Optional[StructuredLessonContent] = None,
        lesson_script: Optional[LessonScript] = None,
        embedder: Optional[Embedder] = None,
        vector_store: Optional[BaseVectorStore] = None,
        bm25_store: Optional[BM25Store] = None,
        chunks: Optional[list[ChunkRecord]] = None,
        rag_settings: Optional[RAGSettings] = None,
        default_top_k: int = DEFAULT_TOP_K,
        score_threshold: float = RETRIEVAL_SCORE_THRESHOLD,
    ):
        self._structured_content = structured_content
        self._lesson_script = lesson_script
        self._rag_settings = rag_settings or get_rag_settings()
        self._default_top_k = default_top_k
        self._score_threshold = score_threshold
        self._embedder = embedder or create_embedder()
        self._content_getter = ContentGetter(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        self._vector_store = vector_store or create_vector_store(self._rag_settings.vector_backend)
        self._bm25_store = bm25_store or BM25Store()
        self._chunks = list(chunks) if chunks is not None else self._build_chunks()
        self._chunk_map = {chunk.chunk_id: chunk for chunk in self._chunks}
        self._metadata = {
            "lesson_id": structured_content.lesson_id if structured_content else None,
            "vector_backend": self._rag_settings.vector_backend,
        }

        if self._chunks and self._vector_store.size == 0:
            self._build_vector_store()
        if self._chunks and self._bm25_store.size == 0:
            self._bm25_store.build(self._chunks)

    def _build_chunks(self) -> list[ChunkRecord]:
        if self._structured_content is None:
            return []
        builder = ChunkBuilder(
            chunk_size=self._rag_settings.chunk_size,
            overlap=self._rag_settings.chunk_overlap,
        )
        return builder.build(self._structured_content, self._lesson_script)

    def _build_vector_store(self) -> None:
        if not self._chunks:
            return

        texts = [chunk.text for chunk in self._chunks]
        vectors = self._embedder.embed_batch(texts)
        metadatas = [self._chunk_metadata(chunk) for chunk in self._chunks]
        ids = [chunk.chunk_id for chunk in self._chunks]
        self._vector_store.add_batch(vectors=vectors, texts=texts, ids=ids, metadatas=metadatas)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        source_filter: Optional[list[str]] = None,
        prefer_section_id: Optional[str] = None,
        prefer_page: Optional[int] = None,
        prefer_script_block_id: Optional[str] = None,
    ) -> list[RetrievedContextItem]:
        """
        Retrieve relevant chunk-backed context items for a query.
        """
        if not query or not query.strip():
            return []

        if top_k is None:
            top_k = self._default_top_k
        if score_threshold is None:
            score_threshold = self._score_threshold

        dense_top_k = max(top_k * 4, self._rag_settings.dense_top_k)
        bm25_top_k = max(top_k * 4, self._rag_settings.bm25_top_k)

        dense_results = []
        if self._has_semantic_embeddings():
            dense_results = self._vector_store.search_by_text(
                query_text=query,
                embedder=self._embedder,
                k=dense_top_k,
                score_threshold=None,
            )
        bm25_results = self._bm25_store.search(
            query,
            k=bm25_top_k,
            source_filter=source_filter,
        )

        dense_scores = {
            entry.id: self._normalize_dense_score(raw_score)
            for entry, raw_score in dense_results
            if entry.id in self._chunk_map
        }
        bm25_scores = self._normalize_sparse_scores(bm25_results)
        query_tokens = BM25Store.tokenize(query)

        ranked_by_parent: dict[tuple[str, str], RetrievedContextItem] = {}
        score_by_parent: dict[tuple[str, str], float] = {}

        candidate_ids = set(dense_scores) | {chunk.chunk_id for chunk, _ in bm25_results}
        for chunk_id in candidate_ids:
            chunk = self._chunk_map.get(chunk_id)
            if chunk is None:
                continue
            if source_filter and chunk.source_type not in source_filter:
                continue

            dense_weight = self._rag_settings.dense_weight if self._has_semantic_embeddings() else 0.0
            bm25_weight = self._rag_settings.bm25_weight if dense_weight > 0 else 1.0
            score = dense_weight * dense_scores.get(chunk_id, 0.0) + bm25_weight * bm25_scores.get(
                chunk_id, 0.0
            )
            score += self._context_boost(
                chunk,
                query_tokens=query_tokens,
                prefer_section_id=prefer_section_id,
                prefer_page=prefer_page,
                prefer_script_block_id=prefer_script_block_id,
            )

            if score < score_threshold:
                continue

            item = map_to_retrieved_context_item(
                source_type=chunk.parent_source_type,
                source_id=chunk.parent_source_id,
                title=chunk.title,
                text=chunk.text,
                section_id=chunk.section_id,
                page=chunk.page,
                score=round(float(score), 6),
            )
            parent_key = (item.source, item.source_id)
            if score > score_by_parent.get(parent_key, -1.0):
                score_by_parent[parent_key] = score
                ranked_by_parent[parent_key] = item

        ranked_items = sorted(
            ranked_by_parent.values(),
            key=lambda item: item.score or 0.0,
            reverse=True,
        )
        return ranked_items[:top_k]

    def retrieve_by_section(
        self,
        section_id: str,
        top_k: Optional[int] = None,
    ) -> list[RetrievedContextItem]:
        if top_k is None:
            top_k = self._default_top_k

        pages = self._content_getter.get_pages_in_section(section_id)
        scripts = self._content_getter.get_script_blocks_in_section(section_id)
        combined = pages + scripts
        return combined[:top_k]

    def save_to_disk(self, path: str | Path) -> None:
        """Persist retriever state to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        (path / "metadata.json").write_text(
            json.dumps(self._metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (path / "chunks.json").write_text(
            json.dumps([chunk.to_dict() for chunk in self._chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._vector_store.save(path / "vector_store")

    @classmethod
    def load_from_disk(
        cls,
        path: str | Path,
        *,
        structured_content: StructuredLessonContent,
        lesson_script: Optional[LessonScript] = None,
        embedder: Optional[Embedder] = None,
        rag_settings: Optional[RAGSettings] = None,
    ) -> HybridRetriever:
        """Load retriever state from disk."""
        path = Path(path)
        metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        chunk_data = json.loads((path / "chunks.json").read_text(encoding="utf-8"))
        chunks = [ChunkRecord.from_dict(item) for item in chunk_data]
        rag_settings = rag_settings or get_rag_settings()
        vector_backend = metadata.get("vector_backend", rag_settings.vector_backend)
        vector_store = _load_vector_store(path / "vector_store", backend=vector_backend)
        bm25_store = BM25Store(chunks)
        return cls(
            structured_content=structured_content,
            lesson_script=lesson_script,
            embedder=embedder or create_embedder(),
            vector_store=vector_store,
            bm25_store=bm25_store,
            chunks=chunks,
            rag_settings=rag_settings,
            default_top_k=rag_settings.final_top_k,
            score_threshold=rag_settings.score_threshold,
        )

    def _normalize_dense_score(self, score: float) -> float:
        return max(0.0, min(1.0, (float(score) + 1.0) / 2.0))

    def _normalize_sparse_scores(
        self,
        results: list[tuple[ChunkRecord, float]],
    ) -> dict[str, float]:
        if not results:
            return {}
        max_score = max(score for _, score in results) or 1.0
        return {chunk.chunk_id: max(0.0, float(score) / max_score) for chunk, score in results}

    def _context_boost(
        self,
        chunk: ChunkRecord,
        *,
        query_tokens: list[str],
        prefer_section_id: Optional[str],
        prefer_page: Optional[int],
        prefer_script_block_id: Optional[str],
    ) -> float:
        boost = 0.0
        if (
            prefer_script_block_id
            and chunk.source_type == "script_block"
            and chunk.source_id == prefer_script_block_id
        ):
            boost += self._rag_settings.prefer_script_block_boost
        if prefer_page is not None and chunk.page == prefer_page:
            boost += self._rag_settings.prefer_page_boost
        if prefer_section_id and chunk.section_id == prefer_section_id:
            boost += self._rag_settings.prefer_section_boost

        if query_tokens:
            title_blob = " ".join([chunk.title] + list(chunk.key_points)).lower()
            if any(token in title_blob for token in query_tokens):
                boost += self._rag_settings.title_keyword_boost
        return boost

    def _has_semantic_embeddings(self) -> bool:
        return getattr(self._embedder, "client", None) is not None

    def _chunk_metadata(self, chunk: ChunkRecord) -> dict:
        return {
            "chunk_id": chunk.chunk_id,
            "lesson_id": chunk.lesson_id,
            "source_type": chunk.source_type,
            "source_id": chunk.source_id,
            "parent_source_type": chunk.parent_source_type,
            "parent_source_id": chunk.parent_source_id,
            "section_id": chunk.section_id,
            "page": chunk.page,
            "title": chunk.title,
            "chunk_index": chunk.chunk_index,
            "key_points": chunk.key_points,
        }

    @property
    def vector_store(self) -> BaseVectorStore:
        """Get the dense vector store."""
        return self._vector_store

    @property
    def content_getter(self) -> ContentGetter:
        """Get the precise content getter."""
        return self._content_getter

    @property
    def embedder(self) -> Embedder | InMemoryEmbedder:
        """Get the configured embedder."""
        return self._embedder

    @property
    def chunks(self) -> list[ChunkRecord]:
        """Get the indexed retrieval chunks."""
        return list(self._chunks)


def _load_vector_store(path: Path, *, backend: str) -> BaseVectorStore:
    entries_path = path / "entries.json"
    vectors_path = path / "vectors.npy"
    if not entries_path.exists() or not vectors_path.exists():
        return create_vector_store(backend)

    payload = json.loads(entries_path.read_text(encoding="utf-8"))
    vector_store = create_vector_store(backend, dimension=payload.get("dimension"))
    import numpy as np

    vectors = np.load(vectors_path)
    entries = payload.get("entries", [])
    vector_store.add_batch(
        vectors=vectors.tolist(),
        texts=[entry.get("text", "") for entry in entries],
        ids=[entry["id"] for entry in entries],
        metadatas=[entry.get("metadata", {}) for entry in entries],
    )
    return vector_store
