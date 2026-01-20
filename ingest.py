"""
Unified Document Ingestion
Supports both SOP and HC document processing
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import settings


load_dotenv()


class DocumentIngestor:
    """Handles document processing for both agents"""
    
    def __init__(self, agent_type: str = "HC"):
        """
        Initialize ingestor
        
        Args:
            agent_type: "SOP" or "HC"
        """
        self.agent_type = agent_type
        
        # Set paths based on agent type
        if agent_type == "SOP":
            self.documents_path = settings.SOP_DOCUMENTS_PATH
            self.vectorstore_path = settings.SOP_VECTORSTORE_PATH
            self.chunk_size = settings.SOP_CHUNK_SIZE
            self.chunk_overlap = settings.SOP_CHUNK_OVERLAP
        else:  # HC
            self.documents_path = settings.HC_DOCUMENTS_PATH
            self.vectorstore_path = settings.HC_VECTORSTORE_PATH
            self.chunk_size = settings.HC_CHUNK_SIZE
            self.chunk_overlap = settings.HC_CHUNK_OVERLAP
        
        # Initialize embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            model=settings.AZURE_EMBEDDING_DEPLOYMENT,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            chunk_size=16
        )
        
        # Initialize text splitter
        if agent_type == "SOP":
            separators = [
                "\n================================================================================\n",
                "\n## ",
                "\n### ",
                "\n\n",
                "\n",
                " ",
                ""
            ]
        else:  # HC
            separators = ["\n\n", "\n", ". ", " ", ""]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators
        )
        
        self.vectorstore = None
    
    def load_document(self, file_path: str) -> List[Document]:
        """Load document based on file extension"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension in ['.docx', '.doc']:
            loader = Docx2txtLoader(file_path)
        elif file_extension == '.md':
            # For markdown files (SOP documents)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            metadata = self._extract_metadata(content, Path(file_path))
            return [Document(page_content=content, metadata=metadata)]
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        documents = loader.load()
        return documents
    
    def load_documents_from_folder(self) -> List[Document]:
        """Load all documents from the agent's folder"""
        documents = []
        
        if self.agent_type == "SOP":
            # Load markdown files for SOP
            md_files = list(self.documents_path.glob("*.md"))
            print(f"Loading {len(md_files)} SOP documents...")
            
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = self._extract_metadata(content, md_file)
                    doc = Document(page_content=content, metadata=metadata)
                    documents.append(doc)
                    print(f"  ✓ {md_file.name}")
                except Exception as e:
                    print(f"  ✗ Error loading {md_file.name}: {e}")
        else:
            # Load PDF/DOCX for HC
            file_patterns = ['*.pdf', '*.docx', '*.doc']
            files = []
            for pattern in file_patterns:
                files.extend(list(self.documents_path.glob(pattern)))
            
            print(f"Loading {len(files)} HC documents...")
            
            for file in files:
                try:
                    docs = self.load_document(str(file))
                    documents.extend(docs)
                    print(f"  ✓ {file.name}")
                except Exception as e:
                    print(f"  ✗ Error loading {file.name}: {e}")
        
        print(f"Loaded {len(documents)} documents\n")
        return documents
    
    def _extract_metadata(self, content: str, file_path: Path) -> Dict:
        """Extract metadata from document"""
        metadata = {
            "source": str(file_path),
            "filename": file_path.name
        }
        
        # Extract document ID
        doc_id_match = re.search(r'Document ID:\s*([\w-]+)', content)
        if doc_id_match:
            metadata["document_id"] = doc_id_match.group(1)
        
        # Extract title
        title_match = re.search(r'Title:\s*(.+)', content)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        # Extract version
        version_match = re.search(r'Version:\s*([\d.]+)', content)
        if version_match:
            metadata["version"] = version_match.group(1)
        
        # Set document type
        doc_id = metadata.get("document_id", "")
        if "SOP" in doc_id:
            metadata["doc_type"] = "Standard Operating Procedure"
        elif "WI" in doc_id:
            metadata["doc_type"] = "Work Instruction"
        elif "QA" in doc_id:
            metadata["doc_type"] = "Quality Assurance Document"
        else:
            metadata["doc_type"] = "Document"
        
        return metadata
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks"""
        print(f"Splitting documents into chunks...")
        print(f"Chunk size: {self.chunk_size} | Overlap: {self.chunk_overlap}")
        
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk IDs
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
        
        print(f"Created {len(chunks)} chunks\n")
        return chunks
    
    def create_vectorstore(self, chunks: List[Document]) -> FAISS:
        """Create FAISS vectorstore from document chunks"""
        print(f"Creating FAISS vector store...")
        print(f"Embedding {len(chunks)} chunks...")
        
        self.vectorstore = FAISS.from_documents(
            documents=chunks,
            embedding=self.embeddings
        )
        
        return self.vectorstore
    
    def save_vectorstore(self, save_path: str = None):
        """Save FAISS index to disk"""
        if save_path is None:
            save_path = self.vectorstore_path
        
        if self.vectorstore:
            # Create directory if doesn't exist
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(save_path)
            print(f"Vector store saved to: {save_path}\n")
    
    def load_vectorstore(self, load_path: str = None) -> FAISS:
        """Load FAISS index from disk"""
        if load_path is None:
            load_path = self.vectorstore_path
        
        self.vectorstore = FAISS.load_local(
            load_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        return self.vectorstore
    
    def process_document(self, file_path: str, save_path: str = None) -> int:
        """Process single document: load, chunk, embed, and save"""
        print(f"📄 Processing document: {file_path}")
        documents = self.load_document(file_path)
        
        print(f"✅ Loaded {len(documents)} document(s)")
        chunks = self.chunk_documents(documents)
        
        print(f"✅ Created {len(chunks)} chunks")
        self.create_vectorstore(chunks)
        
        if save_path is None:
            save_path = self.vectorstore_path
        
        print(f"💾 Saving vectorstore to {save_path}")
        self.save_vectorstore(save_path)
        
        print("✅ Document processing complete!")
        return len(chunks)
    
    def process_folder(self):
        """Process all documents in folder"""
        print("\n" + "="*60)
        print(f"{self.agent_type} Document Ingestion")
        print("="*60 + "\n")
        
        # Load documents
        print("STEP 1: Loading documents")
        print("-" * 60)
        documents = self.load_documents_from_folder()
        
        if not documents:
            print("❌ No documents found")
            return
        
        # Split into chunks
        print("STEP 2: Splitting into chunks")
        print("-" * 60)
        chunks = self.chunk_documents(documents)
        
        # Delete old vector store
        vectorstore_path = Path(self.vectorstore_path)
        if vectorstore_path.exists():
            shutil.rmtree(vectorstore_path)
            print("🗑️ Deleted old vector store")
        
        # Create vector store
        print("STEP 3: Creating vector store")
        print("-" * 60)
        self.create_vectorstore(chunks)
        self.save_vectorstore()
        
        print("="*60)
        print("✅ Ingestion complete!")
        print("="*60)
        print(f"\nStatistics:")
        print(f"  Documents: {len(documents)}")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Location: {self.vectorstore_path}")
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ingest_unified.py sop    # Process SOP documents")
        print("  python ingest_unified.py hc     # Process HC documents")
        sys.exit(1)
    
    agent_type = sys.argv[1].upper()
    
    if agent_type not in ["SOP", "HC"]:
        print("Error: agent_type must be 'sop' or 'hc'")
        sys.exit(1)
    
    # Validate settings
    try:
        settings.validate()
        settings.create_directories()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    
    # Process documents
    ingestor = DocumentIngestor(agent_type=agent_type)
    ingestor.process_folder()