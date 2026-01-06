from fastapi import FastAPI, HTTPException, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
import uuid
from rag_engine import HebrewRAGEngine, RetrievedChunk, RAGSearchResponse

# --- Pydantic Models from Spec ---

class DocumentMetadata(BaseModel):
    doc_id: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None

class UploadRequest(BaseModel):
    filename: str
    content: str  # Raw text content as per spec
    metadata: Optional[DocumentMetadata] = None
    chunk_size: int = 500
    chunk_overlap: int = 50

class UploadResponse(BaseModel):
    status: str
    total_chunks: int
    doc_id: str

class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 7
    include_sources: bool = True
    metadata_filters: Optional[dict] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    top_k: int = 7

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    history: List[dict]
    sources: Optional[List[RetrievedChunk]] = None

# --- API Application ---

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Hebrew RAG API", description="Comprehensive RAG API for Hebrew Documents")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML, CSS, JS)
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

# Also mount the current directory to serve script.js and style.css
# We do this at the end to not shadow other routes

# Global engine instance
engine = HebrewRAGEngine()
# Load existing index if available
if os.path.exists("hebrew_rag_index.index"):
    engine.load_index("hebrew_rag_index")

# In-memory session store for chat (In production, use MongoDB as per spec)
sessions: Dict[str, List[dict]] = {}

from fastapi import FastAPI, HTTPException, Body, File, UploadFile
import shutil

@app.post("/upload", response_model=UploadResponse)
async def upload_document(request: UploadRequest):
    """
    Uploads raw text content to the RAG system using the engine's processing logic.
    """
    try:
        doc_id = request.metadata.doc_id if request.metadata else str(uuid.uuid4())
        
        # Determine number of chunks before adding
        # (This is just for the response, since add_text handles the logic)
        temp_chunks = engine.chunk_content(request.content, request.chunk_size, request.chunk_overlap)
        
        engine.add_text(
            text=request.content,
            doc_id=doc_id,
            metadata=request.metadata.dict() if request.metadata else None,
            chunk_size=request.chunk_size,
            overlap=request.chunk_overlap
        )
        
        return UploadResponse(
            status="success",
            total_chunks=len(temp_chunks),
            doc_id=doc_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-file", response_model=UploadResponse)
async def upload_pdf_file(file: UploadFile = File(...)):
    """
    Original logic for PDF files: Handles reversal and layout preservation.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        doc_id = file.filename
        temp_path = f"temp_{doc_id}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        engine.add_document(temp_path, doc_id)
        os.remove(temp_path)
        
        return UploadResponse(
            status="success",
            total_chunks=0, # total_chunks calculation happens inside engine, returning 0 for now
            doc_id=doc_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=RAGSearchResponse)
async def search(request: RAGSearchRequest):
    """
    Performs a single-turn RAG search.
    """
    try:
        results = engine.search(request.query, top_k=request.top_k)
        if not request.include_sources:
            results.sources = []
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Performs a multi-turn chat session with RAG context.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        if session_id not in sessions:
            sessions[session_id] = []
            
        # Get history
        history = sessions[session_id]
        
        # For RAG with history, we usually embed the query or a reformulated one.
        # Simple approach: Search based on current message.
        results = engine.search(request.message, top_k=request.top_k)
        
        # Add to history
        history.append({"role": "user", "content": request.message})
        history.append({"role": "assistant", "content": results.answer})
        
        return ChatResponse(
            session_id=session_id,
            answer=results.answer,
            history=history,
            sources=results.sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "provider": engine.llm_provider}

if __name__ == "__main__":
    import uvicorn
    # Mount static files to serve assets like script.js and style.css
    app.mount("/", StaticFiles(directory="."), name="static")
    uvicorn.run(app, host="0.0.0.0", port=8000)
