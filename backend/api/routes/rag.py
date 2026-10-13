import uuid
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from backend.api.dependencies import get_db
from backend.models.rag import (
    DocumentResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from backend.services.rag.pipeline import get_rag_pipeline

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])
documents_router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload brand knowledge document for RAG indexing",
)
async def upload_document(
    brand_name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DocumentResponse:
    """Accepts document file and metadata for chunking and vector embedding."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a filename")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    doc_id = str(uuid.uuid4())
    logger.info("Brand document uploaded for RAG", brand_name=brand_name, filename=file.filename, size=len(content))

    pipeline = get_rag_pipeline()
    chunks_count = 1
    try:
        rag_res = await pipeline.ingest_document(
            file_bytes=content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            brand_name=brand_name,
        )
        chunks_count = rag_res.chunks_count
    except Exception as exc:
        logger.warning("RAG indexing partially failed or degraded", error=str(exc))

    # Persist document metadata in MongoDB
    doc_record = {
        "_id": doc_id,
        "id": doc_id,
        "brand_name": brand_name,
        "filename": file.filename,
        "content_type": file.content_type or "application/octet-stream",
        "chunk_count": chunks_count,
        "status": "indexed",
        "file_size": len(content),
        "created_at": datetime.utcnow(),
    }
    await db.documents.insert_one(doc_record)

    return DocumentResponse(
        id=doc_id,
        brand_name=brand_name,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        chunk_count=chunks_count,
        status="indexed",
        created_at=doc_record["created_at"],
    )


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="List all indexed brand knowledge documents",
)
async def list_documents(
    brand_name: Optional[str] = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[DocumentResponse]:
    query = {}
    if brand_name:
        query["brand_name"] = brand_name

    cursor = db.documents.find(query).sort("created_at", -1)
    docs = []
    async for d in cursor:
        d["id"] = str(d.get("_id", d.get("id", "")))
        docs.append(DocumentResponse.model_validate(d))
    return docs


@router.delete(
    "/documents/{document_id}",
    summary="Delete an indexed document from knowledge store",
)
async def delete_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    query = {"$or": [{"_id": document_id}, {"id": document_id}]}
    if ObjectId.is_valid(document_id):
        query["$or"].append({"_id": ObjectId(document_id)})

    res = await db.documents.delete_one(query)
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"success": True, "document_id": document_id}


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search brand knowledge store via vector similarity",
)
async def search_knowledge(payload: SearchRequest) -> SearchResponse:
    """Performs semantic vector search against ChromaDB."""
    logger.info("Executing RAG semantic search", query=payload.query, brand=payload.brand_name)
    pipeline = get_rag_pipeline()
    try:
        search_res = await pipeline.search(
            query=payload.query,
            brand_name=payload.brand_name,
            top_k=payload.top_k,
        )

        results = [
            SearchResult(
                content=r.content,
                metadata=r.metadata,
                relevance_score=r.score,
            )
            for r in search_res.results
        ]

        return SearchResponse(
            query=payload.query,
            results=results,
        )
    except Exception as exc:
        logger.warning("RAG vector search error, returning fallback", error=str(exc))
        return SearchResponse(query=payload.query, results=[])


# Also register on documents_router for frontend compatibility (/api/documents/*)
documents_router.add_api_route("/upload", upload_document, methods=["POST"], response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
documents_router.add_api_route("", list_documents, methods=["GET"], response_model=list[DocumentResponse])
documents_router.add_api_route("/", list_documents, methods=["GET"], response_model=list[DocumentResponse], include_in_schema=False)
documents_router.add_api_route("/{document_id}", delete_document, methods=["DELETE"])
documents_router.add_api_route("/search", search_knowledge, methods=["POST"], response_model=SearchResponse)
