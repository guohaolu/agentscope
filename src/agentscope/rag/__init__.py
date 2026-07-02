# -*- coding: utf-8 -*-
"""The retrieval-augmented generation (RAG) module in AgentScope."""

from ._chunker import ApproxTokenChunker, ChunkerBase
from ._document import (
    Section,
    Chunk,
)
from ._fusion import FusionStrategy, LLMFusionStrategy, RRFStrategy
from ._parser import ImageParser, ParserBase, PDFParser, PPTParser, TextParser
from ._vdb import (
    DocumentSummary,
    VectorStoreBase,
    VectorRecord,
    VectorSearchResult,
    QdrantStore,
)
from ._knowledge import KnowledgeBase

__all__ = [
    "ApproxTokenChunker",
    "ChunkerBase",
    "Chunk",
    "DocumentSummary",
    "FusionStrategy",
    "ImageParser",
    "LLMFusionStrategy",
    "ParserBase",
    "PDFParser",
    "PPTParser",
    "RRFStrategy",
    "TextParser",
    "Section",
    "VectorStoreBase",
    "VectorRecord",
    "VectorSearchResult",
    "QdrantStore",
    "KnowledgeBase",
]
