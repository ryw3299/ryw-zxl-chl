"""
Embedder module for text embedding generation.

Provides both a lightweight in-memory fallback and a production-ready
OpenAI-compatible embedding client.
"""

from __future__ import annotations

import json
from http.client import IncompleteRead
from typing import Optional, Protocol, runtime_checkable
from urllib import error, request

from .config import EmbeddingSettings, get_embedding_settings
from .constants import DEFAULT_EMBEDDING_MODEL


class EmbeddingRequestError(RuntimeError):
    """Raised when an embedding API request fails."""


@runtime_checkable
class EmbeddingClient(Protocol):
    """Protocol for embedding-capable clients."""

    def embed_text(self, text: str, model: str) -> list[float]:
        """Embed a single text using the configured model."""
        ...

    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        """Embed multiple texts using the configured model."""
        ...


class OpenAICompatibleEmbeddingClient:
    """Minimal client for OpenAI-compatible embedding endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        endpoint_path: str = "/embeddings",
        timeout_seconds: int = 30,
    ):
        self._endpoint = f"{base_url.rstrip('/')}{endpoint_path}"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def embed_text(self, text: str, model: str) -> list[float]:
        """Embed a single text."""
        return self.embed_texts([text], model=model)[0]

    def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        """Embed multiple texts in one request."""
        if not texts:
            return []

        payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
        req = request.Request(
            self._endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError, IncompleteRead) as exc:
            raise EmbeddingRequestError(f"Embedding request failed: {exc}") from exc

        try:
            data = json.loads(raw)
            embeddings = sorted(data["data"], key=lambda item: item.get("index", 0))
            return [item["embedding"] for item in embeddings]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingRequestError("Invalid embedding response payload") from exc


class Embedder:
    """
    Text embedder using a configurable embedding-capable client.
    """

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        client: Optional[EmbeddingClient] = None,
    ):
        self.model = model
        self._client = client

    @property
    def client(self) -> Optional[EmbeddingClient]:
        """Get the configured client."""
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        if self._client is not None:
            return self._client.embed_text(text, model=self.model)
        fallback = InMemoryEmbedder()
        return fallback.embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self._client is not None:
            return self._client.embed_texts(texts, model=self.model)
        fallback = InMemoryEmbedder()
        return fallback.embed_batch(texts)

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a query string."""
        return self.embed(query)


class InMemoryEmbedder:
    """
    Simple in-memory embedder for testing or standalone use.

    Uses a deterministic hash-based approach to generate pseudo-embeddings.
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-embedding."""
        import hashlib
        import random

        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)
        return [random.uniform(-1, 1) for _ in range(self.dimension)]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a query."""
        return self.embed(query)


def create_embedder(settings: EmbeddingSettings | None = None) -> Embedder:
    """Create an embedder from environment-backed settings."""
    settings = settings or get_embedding_settings()
    if settings.use_remote_embeddings():
        return _ResilientEmbedder(
            model=settings.model,
            client=OpenAICompatibleEmbeddingClient(
                base_url=settings.base_url or "",
                api_key=settings.api_key or "",
                endpoint_path=settings.endpoint_path,
                timeout_seconds=settings.timeout_seconds,
            ),
            fallback_enabled=settings.fallback_to_in_memory,
        )

    if settings.fallback_to_in_memory:
        return Embedder(model=settings.model, client=None)

    raise EmbeddingRequestError("Embedding configuration is incomplete and fallback is disabled.")


class _ResilientEmbedder(Embedder):
    """Embedder that falls back to InMemoryEmbedder on remote API errors."""

    def __init__(self, *, model: str, client: EmbeddingClient, fallback_enabled: bool):
        super().__init__(model=model, client=client)
        self._fallback_enabled = fallback_enabled
        self._fallback = InMemoryEmbedder()

    def embed(self, text: str) -> list[float]:
        try:
            return super().embed(text)
        except Exception:
            if self._fallback_enabled:
                return self._fallback.embed(text)
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            return super().embed_batch(texts)
        except Exception:
            if self._fallback_enabled:
                return self._fallback.embed_batch(texts)
            raise
