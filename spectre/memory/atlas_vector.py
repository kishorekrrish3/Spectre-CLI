"""
MongoDB Atlas Vector Search integration for Spectre-CLI.
Targeting prize: 'Best Use of MongoDB Atlas'.
Uses Atlas $vectorSearch aggregation pipeline for semantic retrieval of resurrected code and logs.
"""

import logging
from typing import List, Dict, Any, Optional

from spectre.memory.base import BaseVectorStore, ResurrectedMemory

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

logger = logging.getLogger("spectre.atlas")


class AtlasVectorStore(BaseVectorStore):
    """
    MongoDB Atlas Vector Search backend.
    Stores and retrieves historical artifacts using cosine-distance vector search indexes.
    """

    def __init__(
        self,
        connection_uri: str,
        db_name: str = "spectre_vault",
        collection_name: str = "resurrected_artifacts",
        index_name: str = "vector_index",
    ):
        if not HAS_PYMONGO:
            raise ImportError("pymongo package is required for AtlasVectorStore.")
        if not connection_uri:
            raise ValueError("MongoDB connection URI is required.")

        self.uri = connection_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.index_name = index_name

        self.client: MongoClient = MongoClient(
            self.uri,
            serverSelectionTimeoutMS=3000,
            appName="SpectreSéanceCLI"
        )
        # Test connection ping
        self.client.admin.command("ping")
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        logger.info(f"Connected to MongoDB Atlas: {self.db_name}.{self.collection_name}")

    def store_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """
        Inserts document chunks along with their vector embeddings into MongoDB Atlas.
        """
        if not documents:
            return 0

        records = []
        for doc, emb in zip(documents, embeddings):
            record = {
                "text": doc.get("text", ""),
                "source_file": doc.get("source_file", "unknown"),
                "chunk_index": doc.get("chunk_index", 0),
                "metadata": doc.get("metadata", {}),
                "embedding": emb,
            }
            records.append(record)

        result = self.collection.insert_many(records)
        return len(result.inserted_ids)

    def search(self, query_embedding: List[float], top_k: int = 4) -> List[ResurrectedMemory]:
        """
        Executes MongoDB Atlas $vectorSearch aggregation pipeline.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(top_k * 10, 50),
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "text": 1,
                    "source_file": 1,
                    "chunk_index": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            cursor = self.collection.aggregate(pipeline)
            memories = []
            for doc in cursor:
                memories.append(
                    ResurrectedMemory(
                        id=str(doc.get("_id", "")),
                        text=doc.get("text", ""),
                        source_file=doc.get("source_file", ""),
                        chunk_index=doc.get("chunk_index", 0),
                        metadata=doc.get("metadata", {}),
                        score=float(doc.get("score", 0.0)),
                    )
                )
            return memories
        except PyMongoError as e:
            logger.error(f"Atlas Vector Search query failed: {e}")
            raise

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})
