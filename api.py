"""
Unified FastAPI Backend
Provides REST API endpoints for both agents:
- Agent 1: SOP Assistant
- Agent 2: Human Capital Assistant
"""

import os
import shutil
from typing import Optional, List, Dict
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import SOPAgent, HCAgent
from ingest import DocumentIngestor
import os
from config import settings

from dotenv import load_dotenv
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
AZURE_CHAT_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")

# Load environment variables
load_dotenv()

app = FastAPI(
    title="PT Bio Farma Unified Assistant API",
    description="Dual-agent system: SOP Assistant + Human Capital Assistant",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agents
sop_agent: Optional[SOPAgent] = None
hc_agent: Optional[HCAgent] = None

# Pydantic models
class Question(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict]] = None
    chunks: Optional[int] = None
    agent: str


class StatusResponse(BaseModel):
    status: str
    message: str
    chunks_created: Optional[int] = None


class SystemStatus(BaseModel):
    sop_agent_ready: bool
    hc_agent_ready: bool
    sop_index_exists: bool
    hc_index_exists: bool
    env_loaded: bool
    azure_endpoint: str
    embedding_model: str
    chat_model: str


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global sop_agent, hc_agent
    
    print("=" * 60)
    print("🚀 Starting PT Bio Farma Unified Assistant API")
    print("=" * 60)
    
    # Check credentials
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_KEY",
        "AZURE_EMBEDDING_DEPLOYMENT",
        "AZURE_CHAT_DEPLOYMENT"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ WARNING: Missing environment variables: {missing_vars}")
        print("📝 Please create a .env file with all required credentials")
    else:
        print("✅ All credentials loaded from .env file")
        print(f"🔗 Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
        print(f"📊 Embedding: {os.getenv('AZURE_EMBEDDING_DEPLOYMENT')}")
        print(f"💬 Chat: {os.getenv('AZURE_CHAT_DEPLOYMENT')}")
    
    print("\n" + "-" * 60)
    print("Agent Initialization Status:")
    print("-" * 60)
    
    # Try to initialize SOP Agent
    try:
        if os.path.exists(settings.SOP_VECTORSTORE_PATH):
            sop_agent = SOPAgent()
            print("✅ SOP Agent: Ready")
        else:
            print("⚠️ SOP Agent: No index found (run: python ingest_unified.py sop)")
    except Exception as e:
        print(f"❌ SOP Agent: Initialization failed - {str(e)}")
    
    # Try to initialize HC Agent (optional, initialized on demand)
    try:
        if os.path.exists(settings.HC_VECTORSTORE_PATH):
            hc_agent = HCAgent()
            hc_agent.initialize()
            print("✅ HC Agent: Ready")
        else:
            print("⚠️ HC Agent: No index found (will initialize after document upload)")
    except Exception as e:
        print(f"⚠️ HC Agent: {str(e)}")
    
    print("=" * 60 + "\n")


# ==================== SOP Agent Endpoints ====================

@app.post("/sop/ask", response_model=AnswerResponse)
async def ask_sop_question(question: Question):
    """
    Agent 1: SOP Assistant Endpoint
    Ask questions about SOPs, Work Instructions, and procedures
    """
    global sop_agent
    
    if not sop_agent:
        raise HTTPException(
            status_code=400,
            detail="SOP Agent not initialized. Please run: python ingest_unified.py sop"
        )
    
    try:
        print(f"\n[SOP Agent] ❓ Question: {question.question}")
        result = sop_agent.query(question.question)
        print(f"[SOP Agent] ✅ Answer generated\n")
        
        return AnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            chunks=result["chunks"],
            agent="SOP Assistant"
        )
    
    except Exception as e:
        print(f"[SOP Agent] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HC Agent Endpoints ====================

@app.post("/hc/upload", response_model=StatusResponse)
async def upload_hc_document(file: UploadFile = File(...)):
    """
    Agent 2: HC Assistant - Upload Document Endpoint
    Upload and process HR document (PDF/DOCX)
    """
    global hc_agent
    
    # Validate file type
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported"
        )
    
    # Check credentials
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        raise HTTPException(
            status_code=400,
            detail="Azure credentials not found. Please create a .env file."
        )
    
    try:
        # Save uploaded file
        upload_dir = settings.HC_UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"\n[HC Agent] 📄 Processing document: {file.filename}")
        
        # Process document and create index
        ingestor = DocumentIngestor(agent_type="HC")
        chunks_created = ingestor.process_document(file_path, settings.HC_VECTORSTORE_PATH)
        
        print(f"[HC Agent] ✅ Created {chunks_created} chunks")
        
        # Initialize HC agent
        print("[HC Agent] 🔧 Initializing agent...")
        hc_agent = HCAgent()
        hc_agent.initialize()
        
        print("[HC Agent] ✅ Ready!\n")
        
        return StatusResponse(
            status="success",
            message=f"Document processed successfully. Created {chunks_created} chunks.",
            chunks_created=chunks_created
        )
    
    except Exception as e:
        print(f"[HC Agent] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hc/ask", response_model=AnswerResponse)
async def ask_hc_question(question: Question):
    """
    Agent 2: HC Assistant Endpoint
    Ask questions about HR policies, leave, benefits, etc.
    """
    global hc_agent
    
    if not hc_agent:
        raise HTTPException(
            status_code=400,
            detail="HC Agent not initialized. Please upload a document first."
        )
    
    try:
        print(f"\n[HC Agent] ❓ Question: {question.question}")
        result = hc_agent.query(question.question)
        print(f"[HC Agent] ✅ Answer generated\n")
        
        return AnswerResponse(
            answer=result["answer"],
            sources=result["sources"],
            chunks=result["chunks"],
            agent="Human Capital Assistant"
        )
    
    except Exception as e:
        print(f"[HC Agent] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== System Endpoints ====================

@app.get("/status", response_model=SystemStatus)
async def get_status():
    """Check system status for both agents"""
    env_loaded = bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
    
    return SystemStatus(
        sop_agent_ready=sop_agent is not None,
        hc_agent_ready=hc_agent is not None,
        sop_index_exists=os.path.exists(settings.SOP_VECTORSTORE_PATH),
        hc_index_exists=os.path.exists(settings.HC_VECTORSTORE_PATH),
        env_loaded=env_loaded,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "Not set"),
        embedding_model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "Not set"),
        chat_model=os.getenv("AZURE_CHAT_DEPLOYMENT", "Not set")
    )


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "PT Bio Farma Unified Assistant API",
        "version": "2.0.0",
        "status": "running",
        "agents": [
            {
                "name": "SOP Assistant",
                "persona": "Filman Galuh Purnawidjaya (AVP Kepatuhan)",
                "description": "Answers questions about SOPs and Work Procedures",
                "endpoints": {
                    "POST /sop/ask": "Ask SOP questions"
                }
            },
            {
                "name": "Human Capital Assistant",
                "persona": "Ditya Handayani (VP Layanan Human Capital)",
                "description": "Answers questions about HR policies and regulations",
                "endpoints": {
                    "POST /hc/upload": "Upload HR document",
                    "POST /hc/ask": "Ask HC questions"
                }
            }
        ],
        "system_endpoints": {
            "GET /status": "Check system status",
            "GET /docs": "API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting Unified FastAPI server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📖 API docs available at: http://localhost:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)