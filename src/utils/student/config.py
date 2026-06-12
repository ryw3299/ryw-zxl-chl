"""
Configuration helpers for student-side retrieval.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from .constants import (
    BM25_SCORE_WEIGHT,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_BM25_TOP_K,
    DEFAULT_DENSE_TOP_K,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RETRIEVER_CACHE_SIZE,
    DEFAULT_TOP_K,
    DEFAULT_VECTOR_BACKEND,
    DENSE_SCORE_WEIGHT,
    PREFER_PAGE_BOOST,
    PREFER_SCRIPT_BLOCK_BOOST,
    PREFER_SECTION_BOOST,
    RETRIEVAL_SCORE_THRESHOLD,
    TITLE_KEYWORD_BOOST,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_INDEX_DIR = _PROJECT_ROOT / "data" / "rag_indices"
_PLACEHOLDER_API_KEY_MARKERS = frozenset({"", "test", "fake", "placeholder", "mock"})


class EmbeddingSettings(BaseSettings):
    """Environment-backed settings for embedding generation."""

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_BASE_URL: str | None = None
    EMBEDDING_API_KEY: str | None = None
    EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODEL
    EMBEDDING_ENDPOINT_PATH: str = "/embeddings"
    EMBEDDING_TIMEOUT_SECONDS: int = 30
    EMBEDDING_BATCH_SIZE: int = 16
    EMBEDDING_FALLBACK_TO_IN_MEMORY: bool = True

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "extra": "ignore"}

    @property
    def provider(self) -> str:
        return self.EMBEDDING_PROVIDER

    @property
    def base_url(self) -> str | None:
        return self.EMBEDDING_BASE_URL

    @property
    def api_key(self) -> str | None:
        return self.EMBEDDING_API_KEY

    @property
    def model(self) -> str:
        return self.EMBEDDING_MODEL

    @property
    def endpoint_path(self) -> str:
        return self.EMBEDDING_ENDPOINT_PATH

    @property
    def timeout_seconds(self) -> int:
        return self.EMBEDDING_TIMEOUT_SECONDS

    @property
    def batch_size(self) -> int:
        return self.EMBEDDING_BATCH_SIZE

    @property
    def fallback_to_in_memory(self) -> bool:
        return self.EMBEDDING_FALLBACK_TO_IN_MEMORY

    @property
    def mode(self) -> str:
        return "remote" if self.use_remote_embeddings() else "in_memory"

    def use_remote_embeddings(self) -> bool:
        """Return whether a real embedding API should be used."""
        if not self.base_url or not self.api_key:
            return False
        return self.api_key.strip().lower() not in _PLACEHOLDER_API_KEY_MARKERS


class RAGSettings(BaseSettings):
    """Environment-backed settings for retrieval pipeline behavior."""

    RAG_VECTOR_BACKEND: str = DEFAULT_VECTOR_BACKEND
    RAG_INDEX_DIR: str = Field(default=str(_DEFAULT_INDEX_DIR))
    RAG_CHUNK_SIZE: int = CHUNK_SIZE
    RAG_CHUNK_OVERLAP: int = CHUNK_OVERLAP
    RAG_DENSE_TOP_K: int = DEFAULT_DENSE_TOP_K
    RAG_BM25_TOP_K: int = DEFAULT_BM25_TOP_K
    RAG_FINAL_TOP_K: int = DEFAULT_TOP_K
    RAG_SCORE_THRESHOLD: float = RETRIEVAL_SCORE_THRESHOLD
    RAG_DENSE_WEIGHT: float = DENSE_SCORE_WEIGHT
    RAG_BM25_WEIGHT: float = BM25_SCORE_WEIGHT
    RAG_PREFER_SCRIPT_BLOCK_BOOST: float = PREFER_SCRIPT_BLOCK_BOOST
    RAG_PREFER_PAGE_BOOST: float = PREFER_PAGE_BOOST
    RAG_PREFER_SECTION_BOOST: float = PREFER_SECTION_BOOST
    RAG_TITLE_KEYWORD_BOOST: float = TITLE_KEYWORD_BOOST
    RAG_RETRIEVER_CACHE_SIZE: int = DEFAULT_RETRIEVER_CACHE_SIZE
    RAG_REBUILD_INDEX: bool = False

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "extra": "ignore"}

    @property
    def vector_backend(self) -> str:
        return self.RAG_VECTOR_BACKEND.lower()

    @property
    def index_dir(self) -> Path:
        return Path(self.RAG_INDEX_DIR)

    @property
    def chunk_size(self) -> int:
        return self.RAG_CHUNK_SIZE

    @property
    def chunk_overlap(self) -> int:
        return self.RAG_CHUNK_OVERLAP

    @property
    def dense_top_k(self) -> int:
        return self.RAG_DENSE_TOP_K

    @property
    def bm25_top_k(self) -> int:
        return self.RAG_BM25_TOP_K

    @property
    def final_top_k(self) -> int:
        return self.RAG_FINAL_TOP_K

    @property
    def score_threshold(self) -> float:
        return self.RAG_SCORE_THRESHOLD

    @property
    def dense_weight(self) -> float:
        return self.RAG_DENSE_WEIGHT

    @property
    def bm25_weight(self) -> float:
        return self.RAG_BM25_WEIGHT

    @property
    def prefer_script_block_boost(self) -> float:
        return self.RAG_PREFER_SCRIPT_BLOCK_BOOST

    @property
    def prefer_page_boost(self) -> float:
        return self.RAG_PREFER_PAGE_BOOST

    @property
    def prefer_section_boost(self) -> float:
        return self.RAG_PREFER_SECTION_BOOST

    @property
    def title_keyword_boost(self) -> float:
        return self.RAG_TITLE_KEYWORD_BOOST

    @property
    def retriever_cache_size(self) -> int:
        return self.RAG_RETRIEVER_CACHE_SIZE

    @property
    def rebuild_index(self) -> bool:
        return self.RAG_REBUILD_INDEX


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    """Get cached embedding settings."""
    return EmbeddingSettings()


@lru_cache(maxsize=1)
def get_rag_settings() -> RAGSettings:
    """Get cached retrieval settings."""
    return RAGSettings()


def clear_student_settings_cache() -> None:
    """Clear cached retrieval settings. Useful for tests."""
    get_embedding_settings.cache_clear()
    get_rag_settings.cache_clear()
