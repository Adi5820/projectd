from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUpload(BaseModel):
    """Metadata payload accompanying file upload for RAG indexing."""
    brand_name: str = Field(..., min_length=1, max_length=100, description="Brand name for knowledge isolation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom document attributes")


class DocumentResponse(BaseModel):
    """Response returned after processing and indexing brand knowledge document."""
    id: str = Field(..., description="Unique document ID in knowledge store")
    brand_name: str = Field(..., description="Brand name")
    filename: str = Field(..., description="Uploaded file name")
    content_type: str = Field(..., description="MIME type or file extension")
    chunk_count: int = Field(default=0, ge=0, description="Number of text chunks embedded in vector store")
    status: str = Field(default="indexed", description="Indexing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Uploaded timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class SearchRequest(BaseModel):
    """Vector similarity search query for brand documents."""
    query: str = Field(..., min_length=1, description="Query text to search for relevant knowledge")
    brand_name: Optional[str] = Field(default=None, description="Optional brand filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top matches to retrieve")


class SearchResult(BaseModel):
    """Single matching chunk retrieved from ChromaDB."""
    content: str = Field(..., description="Extracted document chunk content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata tags")
    relevance_score: float = Field(..., description="Similarity or relevance score")


class SearchResponse(BaseModel):
    """Vector search response containing matching chunks."""
    query: str = Field(..., description="Query performed")
    results: list[SearchResult] = Field(default_factory=list, description="Retrieved matching document chunks")
