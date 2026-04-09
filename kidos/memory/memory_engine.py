"""
KidOS Memory Engine — Persistent Vector Memory Layer

Uses ChromaDB for local vector storage and Ollama's nomic-embed-text
model for generating embeddings. This gives KidOS the ability to
remember past interactions, store knowledge, and retrieve relevant
context for future tasks.

Architecture:
  User Input → generate_embedding() → store_memory()
  User Query → generate_embedding() → search_memory() → relevant context
"""

import hashlib
import time
from typing import Any

import chromadb
import httpx

from kidos.core.logger import get_logger

logger = get_logger("kidos.memory")

# ── Configuration ────────────────────────────────────────────────────────
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "kidos_memory"


class MemoryEngine:
    """KidOS Core: Vector Memory Subsystem.

    Provides store/search/recall capabilities backed by ChromaDB
    and Ollama embedding generation.
    """

    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )
        logger.info(
            f"MemoryEngine initialized. Collection '{COLLECTION_NAME}' "
            f"loaded with {self.collection.count()} existing records."
        )

    # ── Embedding Generation ─────────────────────────────────────────────

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text via Ollama.

        Uses the nomic-embed-text model which produces 768-dim vectors
        optimized for semantic search and retrieval.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OLLAMA_EMBED_URL,
                json={"model": EMBED_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            embedding = resp.json()["embedding"]
            logger.info(
                f"Generated embedding ({len(embedding)} dims) "
                f"for: \"{text[:50]}...\""
            )
            return embedding

    # ── Store ────────────────────────────────────────────────────────────

    async def store(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a piece of information in KidOS memory.

        Args:
            text: The content to remember.
            metadata: Optional metadata (source agent, type, timestamp, etc.)

        Returns:
            The unique memory ID assigned to this record.
        """
        embedding = await self.generate_embedding(text)

        # Create a deterministic but unique ID
        memory_id = hashlib.sha256(
            f"{text}:{time.time()}".encode()
        ).hexdigest()[:16]

        # Build metadata
        meta = {
            "timestamp": time.time(),
            "source": "kidos",
            **(metadata or {}),
        }

        self.collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[memory_id],
        )

        logger.info(
            f"Stored memory [{memory_id}]: \"{text[:60]}...\" "
            f"(total: {self.collection.count()})"
        )
        return memory_id

    # ── Search / Recall ──────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        n_results: int = 3,
    ) -> list[dict[str, Any]]:
        """Search KidOS memory for information relevant to the query.

        Args:
            query: The search query text.
            n_results: Number of results to return.

        Returns:
            List of dicts with keys: text, distance, metadata
        """
        if self.collection.count() == 0:
            logger.info("Memory search skipped — collection is empty.")
            return []

        query_embedding = await self.generate_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "text": doc,
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "id": results["ids"][0][i] if results.get("ids") else None,
                })

        logger.info(
            f"Memory search for \"{query[:40]}...\" "
            f"returned {len(memories)} results."
        )
        return memories

    # ── Convenience Methods ──────────────────────────────────────────────

    async def remember(self, text: str, source: str = "chat") -> str:
        """Quick-store a piece of information with a source tag."""
        return await self.store(text, metadata={"source": source})

    async def recall(self, query: str, n: int = 3) -> str:
        """Quick-search and return results as a formatted context string."""
        memories = await self.search(query, n_results=n)
        if not memories:
            return ""

        context_parts = []
        for i, mem in enumerate(memories, 1):
            context_parts.append(f"[Memory {i}] {mem['text']}")

        return "\n".join(context_parts)

    def count(self) -> int:
        """Return the total number of stored memories."""
        return self.collection.count()

    def clear(self) -> None:
        """Wipe all memories (development/testing use)."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("All memories cleared.")


# ── Singleton ────────────────────────────────────────────────────────────
memory_engine = MemoryEngine()