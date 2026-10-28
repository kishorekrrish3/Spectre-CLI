"""
Base interface for Spectre vector memory stores.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ResurrectedMemory:
    id: str
    text: str
    source_file: str
    chunk_index: int
    metadata: Dict[str, Any]
    score: float = 0.0


class BaseVectorStore(ABC):
    """
    Abstract interface for indexing and searching resurrected historical documents.
    """

    @abstractmethod
    def store_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """
        Store documents and their embedding vectors.
        """
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 4) -> List[ResurrectedMemory]:
        """
        Find top_k nearest memories using vector similarity search.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Count total resurrected memories currently indexed.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Exorcise / clear all stored memories.
        """
        pass
