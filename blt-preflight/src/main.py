"""
BLT-Preflight Advisory Server – FastAPI Application

A pre-contribution advisory system that provides security guidance based on:
- Contributor intent
- Code context (files, labels)
- OWASP best practices via RAG retrieval
- Repository metadata

Features:
- Health checks for monitoring
- RAG-based semantic retrieval of OWASP guidance
- Multi-tier LLM support (Gemini, OpenAI, Ollama)
- Learning loop with feedback recording
- Designed for Git pre-commit hooks and GitHub Actions
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.advisory_engine.retriever import RAGRetriever

# ── Configuration ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if not os.getenv("PREFLIGHT_DEBUG") else logging.DEBUG
)
logger = logging.getLogger(__name__)

SERVER_PORT = int(os.getenv("PREFLIGHT_SERVER_PORT", "8000"))
DEBUG_MODE = os.getenv("PREFLIGHT_DEBUG", "false").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# ── Global state ─────────────────────────────────────────────────────────────
_retriever: Optional[RAGRetriever] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    global _retriever
    
    # Startup
    logger.info("=== BLT-Preflight Server Starting ===")
    try:
        logger.info("Initializing RAG Retriever...")
        _retriever = RAGRetriever(similarity_threshold=0.6)
        logger.info("✓ RAG Retriever initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize RAG Retriever: {e}")
        raise
    
    logger.info(f"Server running in {'DEBUG' if DEBUG_MODE else 'PRODUCTION'} mode")
    logger.info(f"Primary LLM: {LLM_PROVIDER}")
    logger.info("=== Server Ready ===")
    
    yield
    
    # Shutdown
    logger.info("Server shutting down...")


# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="BLT-Preflight Advisory Server",
    description="Pre-contribution security advisory system powered by OWASP knowledge base",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for local development and GitHub integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    rag_ready: bool
    embedding_model: str
    llm_provider: str


class RetrievalRequest(BaseModel):
    """Request for RAG retrieval."""
    query: str
    top_k: int = 3
    similarity_threshold: Optional[float] = 0.6


class RetrievalChunk(BaseModel):
    """Retrieved knowledge base chunk."""
    text: str
    similarity: float
    quality_score: float
    source: str


class RetrievalResponse(BaseModel):
    """Response containing retrieved knowledge base chunks."""
    status: str
    query: str
    retrieval_quality: str
    retrieved_chunks: list[RetrievalChunk]
    average_quality_score: Optional[float] = None
    message: str


class AdvisoryRequest(BaseModel):
    """Request for security advisory."""
    contributor_intent: Optional[str] = None
    files_changed: list[str] = []
    labels: list[str] = []
    repository_context: Optional[str] = None


class AdvisoryResponse(BaseModel):
    """Security advisory response."""
    status: str
    advisory: str
    severity: str
    references: list[dict]
    retrieved_knowledge_base_chunks: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring and Docker health probes.
    
    Returns:
    - status: 'healthy' if RAG retriever is ready
    - rag_ready: True if knowledge base is loaded
    - embedding_model: Name of the embedding model
    - llm_provider: Primary LLM provider
    """
    rag_ready = _retriever is not None
    
    return HealthResponse(
        status="healthy" if rag_ready else "unhealthy",
        version="1.0.0",
        rag_ready=rag_ready,
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        llm_provider=LLM_PROVIDER,
    )


@app.post("/retrieve", response_model=RetrievalResponse)
async def retrieve_knowledge_base(request: RetrievalRequest):
    """
    Retrieve relevant OWASP knowledge base chunks for a query.
    
    This endpoint powers the core RAG retrieval with quality filters.
    
    Args:
        query: Search query or contributor intent
        top_k: Number of chunks to retrieve (1-5)
        similarity_threshold: Confidence threshold (0.0-1.0)
    
    Returns:
        Retrieved chunks with quality scores and source attribution
    """
    if not _retriever:
        raise HTTPException(
            status_code=503,
            detail="RAG retriever not initialized. Knowledge base may not be loaded."
        )
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not 1 <= request.top_k <= 5:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 5")
    
    try:
        logger.info(f"Retrieving for: {request.query[:80]}...")
        
        result = _retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )
        
        # Convert to response model
        chunks = [
            RetrievalChunk(
                text=chunk['text'],
                similarity=chunk['similarity'],
                quality_score=chunk['quality_score'],
                source=chunk['source']
            )
            for chunk in result['retrieved_chunks']
        ]
        
        logger.info(
            f"Retrieved {len(chunks)} chunks | Quality: {result['retrieval_quality']} | "
            f"Avg Score: {result.get('average_quality_score', 0):.3f}"
        )
        
        return RetrievalResponse(
            status=result['status'],
            query=request.query,
            retrieval_quality=result['retrieval_quality'],
            retrieved_chunks=chunks,
            average_quality_score=result.get('average_quality_score'),
            message=result['message']
        )
    
    except Exception as e:
        logger.error(f"Retrieval error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@app.post("/advisory", response_model=AdvisoryResponse)
async def get_advisory(request: AdvisoryRequest):
    """
    Generate a security advisory based on contributor context.
    
    This is a placeholder endpoint that will integrate with:
    - RAG retrieval (already implemented)
    - LLM analysis (Gemini, OpenAI, or Ollama)
    
    Currently demonstrates the retrieval pipeline.
    """
    if not _retriever:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Build context query from contributor intent and files
        intent = request.contributor_intent or "general security review"
        files_context = ", ".join(request.files_changed[:5]) if request.files_changed else "no specific files"
        labels_context = ", ".join(request.labels) if request.labels else "no labels"
        
        context_query = f"{intent} (files: {files_context}, labels: {labels_context})"
        
        logger.info(f"Advisory request: {intent[:60]}...")
        
        # Retrieve relevant knowledge base
        retrieval_result = _retriever.retrieve(
            query=context_query,
            top_k=3
        )
        
        # TODO: Pass retrieved chunks to LLM for advisory generation
        # For now, return structured retrieval results
        
        if retrieval_result['status'] != 'success':
            advisory_text = (
                "Advisory: Unable to retrieve specific guidance. "
                "Please consult the OWASP documentation directly."
            )
            severity = "info"
        else:
            references = [
                {
                    "title": chunk['metadata'].get('title', 'OWASP Document'),
                    "category": chunk['metadata'].get('category', 'General'),
                    "url": chunk['metadata'].get('source_url', '#'),
                    "relevance": chunk['similarity']
                }
                for chunk in retrieval_result['retrieved_chunks']
            ]
            
            advisory_text = (
                f"Security Advisory: Based on your contribution ({intent}), "
                f"we recommend reviewing these security considerations: "
                f"{', '.join(ref['title'] for ref in references)}"
            )
            severity = "warning" if retrieval_result['retrieval_quality'] == 'high' else "info"
        
        return AdvisoryResponse(
            status="success",
            advisory=advisory_text,
            severity=severity,
            references=references if retrieval_result['status'] == 'success' else [],
            retrieved_knowledge_base_chunks=len(retrieval_result['retrieved_chunks'])
        )
    
    except Exception as e:
        logger.error(f"Advisory generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Advisory generation failed: {str(e)}")


@app.get("/")
async def root():
    """API documentation redirect."""
    return {
        "message": "BLT-Preflight Advisory Server",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "GET /health": "Health check",
            "POST /retrieve": "Retrieve OWASP knowledge base chunks",
            "POST /advisory": "Generate security advisory",
        }
    }


# ── Error handlers ───────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Enhanced HTTP exception handler with logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return {
        "status": "error",
        "code": exc.status_code,
        "message": exc.detail
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on 0.0.0.0:{SERVER_PORT} (debug={DEBUG_MODE})")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=DEBUG_MODE,
        log_level="info" if not DEBUG_MODE else "debug"
    )
