"""
Unified Configuration for Both Agents
SOP Assistant + Human Capital Assistant
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Unified settings for both agents"""
    
    # ==================== Azure OpenAI Configuration ====================
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    
    # Deployment names
    AZURE_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    AZURE_CHAT_DEPLOYMENT: str = os.getenv("AZURE_CHAT_DEPLOYMENT", "gpt-4.1-mini")
    
    # For backward compatibility with Krutika's code
    AZURE_OPENAI_DEPLOYMENT_NAME: str = AZURE_CHAT_DEPLOYMENT
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = AZURE_EMBEDDING_DEPLOYMENT
    AZURE_OPENAI_API_KEY: str = AZURE_OPENAI_KEY
    
    # ==================== Agent 1: SOP Assistant ====================
    # Paths for SOP documents
    SOP_DOCUMENTS_PATH: Path = Path("Data/Documents")
    SOP_VECTORSTORE_PATH: str = "data/vectorstore/sop_faiss_index"
    
    # SOP Agent settings
    SOP_CHUNK_SIZE: int = 800
    SOP_CHUNK_OVERLAP: int = 120
    SOP_TOP_K: int = 4
    
    # ==================== Agent 2: Human Capital Assistant ====================
    # Paths for HR documents
    HC_DOCUMENTS_PATH: Path = Path("data/HR_Doc")
    HC_VECTORSTORE_PATH: str = "data/vectorstore/hc_faiss_index"
    HC_UPLOAD_DIR: str = "uploads/hc"
    
    # HC Agent settings
    HC_CHUNK_SIZE: int = 800
    HC_CHUNK_OVERLAP: int = 120
    HC_TOP_K: int = 4
    
    # ==================== LLM Configuration ====================
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 1000
    
    # ==================== General Settings ====================
    CHUNK_SIZE: int = 800  # Default
    CHUNK_OVERLAP: int = 120  # Default
    TOP_K: int = 4  # Default
    
    # Backward compatibility
    VECTORSTORE_PATH: str = SOP_VECTORSTORE_PATH
    DOCUMENTS_PATH: Path = SOP_DOCUMENTS_PATH
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        if not cls.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT not set in .env file")
        if not cls.AZURE_OPENAI_KEY:
            raise ValueError("AZURE_OPENAI_KEY not set in .env file")
        if not cls.AZURE_EMBEDDING_DEPLOYMENT:
            raise ValueError("AZURE_EMBEDDING_DEPLOYMENT not set in .env file")
        if not cls.AZURE_CHAT_DEPLOYMENT:
            raise ValueError("AZURE_CHAT_DEPLOYMENT not set in .env file")
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        cls.SOP_DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
        cls.HC_DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
        Path(cls.SOP_VECTORSTORE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.HC_VECTORSTORE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.HC_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()