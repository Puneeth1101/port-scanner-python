# backend/api/routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import os
import shutil
import logging
from pydantic import BaseModel

from document_processor.processor import DocumentProcessor
from document_processor.embeddings import EmbeddingGenerator
from search.engine import SearchEngine
import config

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# API Models
class SearchQuery(BaseModel):
    query: str
    top_k: int = config.DEFAULT_TOP_K

class SearchResult(BaseModel):
    text: str
    score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str

# Dependencies
def get_document_processor():
    return DocumentProcessor(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP
    )

def get_embedding_generator():
    return EmbeddingGenerator(model_name=config.EMBEDDING_MODEL)

def get_search_engine():
    return SearchEngine(
        embedding_dim=config.EMBEDDING_DIMENSION,
        index_path=config.INDEX_PATH if os.path.exists(config.INDEX_PATH) else None,
        docs_path=config.DOCS_PATH if os.path.exists(config.DOCS_PATH) else None
    )

# Background task to process uploaded documents
def process_document_task(
    file_path: str,
    document_processor: DocumentProcessor,
    embedding_generator: EmbeddingGenerator,
    search_engine: SearchEngine
):
    try:
        logger.info(f"Processing document: {file_path}")
        # Process document to extract text chunks
        chunks = document_processor.process_document(file_path)
        
        # Generate embeddings for chunks
        chunks_with_embeddings = embedding_generator.generate_embeddings(chunks)
        
        # Add to search index
        search_engine.add_documents(chunks_with_embeddings)
        
        # Save the updated index
        search_engine.save_index(config.INDEX_PATH, config.DOCS_PATH)
        
        logger.info(f"Document processed successfully: {file_path}")
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {str(e)}")

# API Endpoints
@router.get("/")
async def root():
    """API health check endpoint."""
    return {"status": "ok", "message": "Document Search API is running"}

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_processor: DocumentProcessor = Depends(get_document_processor),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """Upload and process a document."""
    try:
        # Check file extension
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension not in document_processor.supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_extension}. Supported types: {list(document_processor.supported_extensions.keys())}"
            )
        
        # Save file to documents directory
        file_path = os.path.join(config.DOCUMENTS_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document in background
        background_tasks.add_task(
            process_document_task, 
            file_path, 
            document_processor, 
            embedding_generator, 
            search_engine
        )
        
        return DocumentUploadResponse(
            filename=filename,
            status="success",
            message="Document uploaded and processing started"
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    search_query: SearchQuery,
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """Search for documents based on a query."""
    try:
        # Generate embedding for query
        query_embedding = embedding_generator.model.encode([search_query.query])[0]
        
        # Search for similar documents
        results = search_engine.search(query_embedding, search_query.top_k)
        
        return SearchResponse(
            results=results,
            query=search_query.query
        )
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=List[Dict])
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """List all indexed documents with metadata."""
    try:
        # Get unique documents (not chunks)
        unique_docs = {}
        for doc in search_engine.documents[:limit]:
            doc_id = doc['metadata']['doc_id']
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    'title': doc['metadata']['title'],
                    'file_type': doc['metadata']['file_type'],
                    'source': doc['metadata']['source'],
                    'created_at': doc['metadata']['created_at'],
                    'modified_at': doc['metadata']['modified_at'],
                    'chunks': 0,
                }
            unique_docs[doc_id]['chunks'] += 1
            
        return list(unique_docs.values())
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summarize")
async def summarize_document(
    doc_id: str,
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """Generate a summary for a specific document."""
    try:
        # Find all chunks for this document
        doc_chunks = [doc for doc in search_engine.documents 
                     if doc['metadata']['doc_id'] == doc_id]
        
        if not doc_chunks:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Sort chunks by chunk_id
        doc_chunks.sort(key=lambda x: x['metadata']['chunk_id'])
        
        # Combine first few chunks as a "summary"
        summary_text = "\n\n".join([chunk['text'] for chunk in doc_chunks[:3]])
        
        return {
            "doc_id": doc_id,
            "title": doc_chunks[0]['metadata']['title'],
            "summary": summary_text[:1000] + "..." if len(summary_text) > 1000 else summary_text
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error summarizing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))