"""
Offline file-backed vector store for Spectre-CLI.
Uses NumPy cosine similarity calculations for zero-dependency local RAG.
Guarantees 100% functionality when disconnected from MongoDB Atlas.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

from spectre.memory.base import BaseVectorStore, ResurrectedMemory


class LocalVectorStore(BaseVectorStore):
    """
    Offline vector memory store stored in a local JSON file.
    """

    def __init__(self, storage_path: Path = Path(".spectre_cache/local_memory.json")):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = []
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.embeddings = data.get("embeddings", [])
            except Exception:
                self.documents = []
                self.embeddings = []

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents, "embeddings": self.embeddings}, f)

    def store_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        for doc, emb in zip(documents, embeddings):
            self.documents.append(doc)
            self.embeddings.append(emb)
        self._save()
        return len(documents)

    def search(self, query_embedding: List[float], top_k: int = 4) -> List[ResurrectedMemory]:
        if not self.documents or not self.embeddings:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        doc_matrix = np.array(self.embeddings, dtype=np.float32)
        doc_norms = np.linalg.norm(doc_matrix, axis=1)
        doc_norms[doc_norms == 0] = 1e-10

        # Cosine similarity dot product
        scores = np.dot(doc_matrix, q_vec) / (doc_norms * q_norm)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            results.append(
                ResurrectedMemory(
                    id=str(idx),
                    text=doc.get("text", ""),
                    source_file=doc.get("source_file", ""),
                    chunk_index=doc.get("chunk_index", 0),
                    metadata=doc.get("metadata", {}),
                    score=float(scores[idx]),
                )
            )
        return results

    def count(self) -> int:
        return len(self.documents)

    def clear(self) -> None:
        self.documents = []
        self.embeddings = []
        if self.storage_path.exists():
            self.storage_path.unlink()
