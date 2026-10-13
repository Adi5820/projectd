"""RAG orchestration pipeline combining document extraction, chunking, embeddings, and retrieval."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import structlog

from backend.services.rag.chunker import chunk_text, extract_text
from backend.services.rag.retriever import ChromaRetriever, SearchResult

logger = structlog.get_logger(__name__)


class DocumentResponse(BaseModel):
    """Response returned after ingesting a brand document."""
    filename: str = Field(..., description="Original filename of the ingested file")
    brand_name: str = Field(..., description="Brand identifier the document is associated with")
    chunks_count: int = Field(..., description="Number of text chunks created and indexed")
    total_characters: int = Field(..., description="Total character count of extracted plain text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags associated with document")


class SearchResponse(BaseModel):
    """Semantic search response containing retrieved knowledge chunks."""
    query: str = Field(..., description="Search query string")
    brand_name: Optional[str] = Field(None, description="Brand filter applied during search")
    results_count: int = Field(..., description="Number of relevant chunks found")
    results: List[SearchResult] = Field(default_factory=list, description="List of matched search results")


class RAGPipeline:
    """Unified pipeline orchestrating document ingestion and knowledge context assembly."""

    def __init__(self, retriever: Optional[ChromaRetriever] = None):
        """Initialize the RAG pipeline.
        
        Args:
            retriever: Optional ChromaRetriever instance.
        """
        self.retriever = retriever or ChromaRetriever()

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        brand_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentResponse:
        """Extract, chunk, embed, and store document in vector database.
        
        Args:
            file_bytes: Raw file content bytes.
            filename: Name of the uploaded file.
            content_type: MIME type of the file.
            brand_name: Associated brand name.
            metadata: Optional additional metadata properties.

        Returns:
            DocumentResponse with summary of indexed content.
        """
        logger.info(
            "rag_ingest_document_start",
            filename=filename,
            brand_name=brand_name,
            content_type=content_type,
            bytes=len(file_bytes),
        )

        # 1. Extract plain text
        raw_text = extract_text(file_bytes, content_type)
        total_chars = len(raw_text)

        # 2. Chunk text
        chunks = chunk_text(raw_text, chunk_size=500, overlap=50)

        # 3. Enrich metadata
        doc_metadata = {
            **(metadata or {}),
            "filename": filename,
            "content_type": content_type,
        }

        # 4. Embed and store in Chroma
        chunks_added = await self.retriever.add_documents(
            brand_name=brand_name,
            chunks=chunks,
            metadata=doc_metadata,
        )

        logger.info(
            "rag_ingest_document_completed",
            filename=filename,
            brand_name=brand_name,
            chunks_count=chunks_added,
            total_characters=total_chars,
        )

        return DocumentResponse(
            filename=filename,
            brand_name=brand_name,
            chunks_count=chunks_added,
            total_characters=total_chars,
            metadata=doc_metadata,
        )

    async def search(
        self,
        query: str,
        brand_name: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        """Search knowledge base for relevant chunks.
        
        Args:
            query: Query text.
            brand_name: Optional brand filter.
            top_k: Number of results to return.

        Returns:
            SearchResponse containing matching chunks.
        """
        results = await self.retriever.search(
            query=query,
            brand_name=brand_name,
            top_k=top_k,
            min_score=0.60,
        )

        return SearchResponse(
            query=query,
            brand_name=brand_name,
            results_count=len(results),
            results=results,
        )

    async def get_brand_context(
        self,
        brand_name: str,
        campaign_brief: str,
        top_k: int = 5,
    ) -> str:
        """Retrieve and format brand knowledge context for AI agents.
        
        Args:
            brand_name: Target brand identifier.
            campaign_brief: Campaign brief or prompt to match against.
            top_k: Maximum number of knowledge chunks to include.

        Returns:
            Formatted markdown context block for prompt injection.
        """
        clean_brand = brand_name.strip()
        search_resp = await self.search(
            query=campaign_brief,
            brand_name=clean_brand,
            top_k=top_k,
        )

        if not search_resp.results:
            return (
                f"### Brand Knowledge Context: {clean_brand}\n"
                "No specific brand guideline documents found. Adhere to general brand voice and brief parameters."
            )

        context_lines = [
            f"### Verified Brand Guidelines & Knowledge: {clean_brand.upper()}",
            "Incorporate the following brand voice guidelines, product details, and value props:\n",
        ]

        for i, item in enumerate(search_resp.results, start=1):
            source = item.metadata.get("filename", "Brand Docs")
            context_lines.append(f"[{i}] (Source: {source}, Relevance: {item.score:.2f})")
            context_lines.append(f"{item.content.strip()}\n")

        return "\n".join(context_lines)


# Singleton instance and convenience accessors
_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Retrieve singleton instance of RAGPipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    brand_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> DocumentResponse:
    """Module-level helper to ingest brand documents."""
    return await get_rag_pipeline().ingest_document(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        brand_name=brand_name,
        metadata=metadata,
    )


async def search(
    query: str,
    brand_name: Optional[str] = None,
    top_k: int = 5,
) -> SearchResponse:
    """Module-level helper to search brand knowledge."""
    return await get_rag_pipeline().search(query=query, brand_name=brand_name, top_k=top_k)


async def get_brand_context(brand_name: str, campaign_brief: str) -> str:
    """Module-level helper to get formatted context for AI agents."""
    return await get_rag_pipeline().get_brand_context(brand_name=brand_name, campaign_brief=campaign_brief)
