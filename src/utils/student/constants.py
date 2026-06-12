"""
Student-side constants for retrieval and content access.
"""

# Default embedding model identifier
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# Default vector backend for dense retrieval
DEFAULT_VECTOR_BACKEND = "faiss"

# Default number of final results returned to the agent
DEFAULT_TOP_K = 5

# Recall depth used before final fusion/ranking
DEFAULT_DENSE_TOP_K = 20
DEFAULT_BM25_TOP_K = 20

# Minimum score threshold for retrieval relevance
RETRIEVAL_SCORE_THRESHOLD = 0.3

# Maximum context string length for LLM input
MAX_CONTEXT_STRING_LENGTH = 8000

# Chunk size for splitting long content
CHUNK_SIZE = 420

# Chunk overlap for splitting long content
CHUNK_OVERLAP = 80

# Weighted hybrid retrieval defaults
DENSE_SCORE_WEIGHT = 0.6
BM25_SCORE_WEIGHT = 0.4

# Soft preference boosts for current teaching context
PREFER_SCRIPT_BLOCK_BOOST = 0.15
PREFER_PAGE_BOOST = 0.10
PREFER_SECTION_BOOST = 0.06
TITLE_KEYWORD_BOOST = 0.03

# Retriever cache size
DEFAULT_RETRIEVER_CACHE_SIZE = 8
