"""ChromaDB vector store retrieval service for brand knowledge and RAG."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import chromadb
from pydantic import BaseModel, Field
import structlog

from backend.config import settings
from backend.services.rag.embeddings import generate_embedding, generate_embeddings_batch

logger = structlog.get_logger(__name__)


class SearchResult(BaseModel):
    """Result item returned from semantic vector search."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary associated with chunk")


class ChromaRetriever:
    """Manages brand knowledge vector embeddings inside persistent ChromaDB."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "brand_knowledge",
    ):
        """Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Path to store Chroma data. Defaults to settings.CHROMA_PERSIST_DIRECTORY.
            collection_name: Name of the vector collection.
        """
        self.persist_directory = persist_directory or getattr(
            settings, "CHROMA_PERSIST_DIRECTORY", str(Path(settings.BASE_DIR) / "data" / "chroma")
        )
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "chroma_retriever_initialized",
            collection=collection_name,
            persist_dir=self.persist_directory,
            total_items=self.collection.count(),
        )

    async def add_documents(
        self,
        brand_name: str,
        chunks: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add brand knowledge document chunks and their embeddings into ChromaDB.
        
        Args:
            brand_name: Target brand identifier.
            chunks: List of extracted text chunks.
            metadata: Optional additional metadata dict to attach to every chunk.

        Returns:
            Number of successfully added chunks.
        """
        if not chunks:
            return 0

        clean_brand = brand_name.strip().lower()
        embeddings = await generate_embeddings_batch(chunks)

        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        base_meta = metadata or {}
        for idx in range(len(chunks)):
            chunk_id = f"{clean_brand}_{uuid.uuid4().hex[:12]}_{idx}"
            ids.append(chunk_id)

            chunk_meta = {
                **base_meta,
                "brand_name": clean_brand,
                "chunk_index": idx,
            }
            # Chroma requires metadata values to be str, int, float, or bool
            sanitized_meta = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in chunk_meta.items()
            }
            metadatas.append(sanitized_meta)

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(
            "chroma_documents_added",
            brand_name=clean_brand,
            chunk_count=len(chunks),
            total_in_collection=self.collection.count(),
        )
        return len(chunks)

    async def search(
        self,
        query: str,
        brand_name: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.7,
    ) -> List[SearchResult]:
        """Perform semantic similarity search over stored document chunks.
        
        Args:
            query: User search query or campaign brief text.
            brand_name: Optional brand filter.
            top_k: Maximum number of relevant results to return.
            min_score: Minimum cosine similarity threshold (0.0 to 1.0).

        Returns:
            List of SearchResult objects sorted by highest relevance score.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        query_embedding = await generate_embedding(clean_query)

        where_filter = None
        if brand_name:
            where_filter = {"brand_name": brand_name.strip().lower()}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        search_results: List[SearchResult] = []

        if results and results.get("ids") and results["ids"][0]:
            ids_list = results["ids"][0]
            docs_list = results["documents"][0] if results.get("documents") else []
            meta_list = results["metadatas"][0] if results.get("metadatas") else []
            dist_list = results["distances"][0] if results.get("distances") else []

            for i in range(len(ids_list)):
                distance = dist_list[i] if i < len(dist_list) else 1.0
                # Cosine distance to similarity: similarity = 1.0 - distance
                similarity = max(0.0, min(1.0, 1.0 - distance))

                if similarity >= min_score:
                    search_results.append(
                        SearchResult(
                            chunk_id=ids_list[i],
                            content=docs_list[i] if i < len(docs_list) else "",
                            score=round(similarity, 4),
                            metadata=meta_list[i] if i < len(meta_list) else {},
                        )
                    )

        search_results.sort(key=lambda x: x.score, reverse=True)
        logger.info(
            "chroma_search_completed",
            brand_name=brand_name,
            results_found=len(search_results),
            top_score=search_results[0].score if search_results else 0.0,
        )
        return search_results

    def delete_brand_documents(self, brand_name: str) -> None:
        """Remove all document chunks belonging to a specific brand.
        
        Args:
            brand_name: Brand identifier to delete.
        """
        clean_brand = brand_name.strip().lower()
        self.collection.delete(where={"brand_name": clean_brand})
        logger.info("chroma_brand_documents_deleted", brand_name=clean_brand)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Retrieve vector collection status and metrics.
        
        Returns:
            Dictionary containing collection metrics.
        """
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count(),
            "persist_directory": str(self.persist_directory),
        }
