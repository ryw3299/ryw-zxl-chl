"""
Student-side retrieval and utility modules.

This package provides the retrieval底层能力 for the student agent,
including embedding, vector storage, hybrid retrieval, and content access.
"""

from .bm25_store import BM25Store
from .chunking import ChunkBuilder, ChunkRecord, split_text_into_chunks
from .config import (
    EmbeddingSettings,
    RAGSettings,
    clear_student_settings_cache,
    get_embedding_settings,
    get_rag_settings,
)
from .constants import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    DEFAULT_VECTOR_BACKEND,
    RETRIEVAL_SCORE_THRESHOLD,
)
from .content_getter import ContentGetter
from .embedder import Embedder, InMemoryEmbedder, OpenAICompatibleEmbeddingClient, create_embedder
from .helpers import build_context_string, map_to_retrieved_context_item
from .hybrid_retriever import HybridRetriever
from .retriever_factory import RetrieverFactory
from .vector_store import (
    BaseVectorStore,
    FaissVectorStore,
    NumpyVectorStore,
    VectorStore,
    create_vector_store,
)

__all__ = [
    "BaseVectorStore",
    "BM25Store",
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "ChunkBuilder",
    "ChunkRecord",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_VECTOR_BACKEND",
    "DEFAULT_TOP_K",
    "EmbeddingSettings",
    "RETRIEVAL_SCORE_THRESHOLD",
    "Embedder",
    "FaissVectorStore",
    "InMemoryEmbedder",
    "NumpyVectorStore",
    "OpenAICompatibleEmbeddingClient",
    "RAGSettings",
    "RetrieverFactory",
    "VectorStore",
    "ContentGetter",
    "HybridRetriever",
    "build_context_string",
    "clear_student_settings_cache",
    "create_embedder",
    "create_vector_store",
    "get_embedding_settings",
    "get_rag_settings",
    "map_to_retrieved_context_item",
    "split_text_into_chunks",
]
