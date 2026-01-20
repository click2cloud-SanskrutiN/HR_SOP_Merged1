"""
Unified Agent Classes
Agent 1: SOP Assistant
Agent 2: Human Capital Assistant
"""
import os
from config import settings

# rest of imports

import re
from pathlib import Path
from typing import List, Dict

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate


from prompts import (
    SOP_SYSTEM_PROMPT,
    SOP_RESPONSE_TEMPLATE,
    HC_SYSTEM_PROMPT,
    HC_RESPONSE_TEMPLATE
)


class BaseAgent:
    """Base class for both agents"""
    
    def __init__(self, agent_type: str):
        """Initialize base agent components"""
        self.agent_type = agent_type
        
        # Initialize LLM
        self.llm = AzureChatOpenAI(
            azure_deployment=settings.AZURE_CHAT_DEPLOYMENT,
            openai_api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            timeout=60,
            max_retries=2,
        )
        
        # Initialize embeddings
        self.embeddings = AzureOpenAIEmbeddings(
            model=settings.AZURE_EMBEDDING_DEPLOYMENT,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            chunk_size=16
        )
    
    def _format_context(self, docs: List[Document]) -> str:
        """Format documents as context"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            doc_id = doc.metadata.get('document_id', 'Unknown')
            title = doc.metadata.get('title', 'Unknown')
            
            context_parts.append(f"""
[Source {i}: {doc_id}]
{title}

{doc.page_content}

---""")
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, docs: List[Document]) -> List[Dict]:
        """Extract source metadata"""
        sources = []
        seen = set()
        
        for doc in docs:
            doc_id = doc.metadata.get('document_id', 'Unknown')
            if doc_id not in seen:
                sources.append({
                    'document_id': doc_id,
                    'title': doc.metadata.get('title', 'Unknown'),
                    'doc_type': doc.metadata.get('doc_type', 'Document'),
                    'filename': doc.metadata.get('filename', 'Unknown')
                })
                seen.add(doc_id)
        
        return sources


class SOPAgent(BaseAgent):
    """Agent 1: SOP and Work Procedure Assistant"""
    
    def __init__(self):
        """Initialize SOP Agent"""
        super().__init__("SOP")
        print("Initializing SOP Agent...")
        self.vectorstore = self._load_vectorstore()
        print("SOP Agent initialized\n")
    
    def _load_vectorstore(self) -> FAISS:
        """Load SOP vector store"""
        vectorstore_path = Path(settings.SOP_VECTORSTORE_PATH)
        
        if not vectorstore_path.exists():
            raise FileNotFoundError(
                f"SOP vector store not found at {vectorstore_path}\n"
                f"Please run: python ingest_sop.py"
            )
        
        return FAISS.load_local(
            str(vectorstore_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
    
    def query(self, question: str, verbose: bool = False) -> Dict:
        """Answer SOP-related questions"""
        if verbose:
            print(f"\n{'='*60}")
            print(f"[SOP Agent] Question: {question}")
            print(f"{'='*60}\n")
        
        # Retrieve relevant documents
        docs_with_scores = self.vectorstore.similarity_search_with_score(
            question,
            k=settings.SOP_TOP_K
        )
        
        if verbose:
            print(f"Found {len(docs_with_scores)} relevant SOP chunks\n")
        
        if not docs_with_scores:
            return {
                "answer": f"No relevant SOP information found for: {question}",
                "sources": [],
                "chunks": 0
            }
        
        # Format context and generate answer
        docs = [doc for doc, score in docs_with_scores]
        context = self._format_context(docs)
        answer = self._generate_answer(question, context)
        sources = self._extract_sources(docs)
        
        return {
            "answer": answer,
            "sources": sources,
            "chunks": len(docs)
        }
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate SOP answer using LLM"""
        prompt = SOP_RESPONSE_TEMPLATE.format(
            context=context,
            query=question
        )
        
        messages = [
            SystemMessage(content=SOP_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content


class HCAgent(BaseAgent):
    """Agent 2: Human Capital Assistant"""
    
    def __init__(self, vectorstore_path: str = None):
        """Initialize HC Agent"""
        super().__init__("HC")
        print("Initializing Human Capital Agent...")
        self.vectorstore_path = vectorstore_path or settings.HC_VECTORSTORE_PATH
        self.vectorstore = None
        self.qa_chain = None
        print("Human Capital Agent initialized\n")
    
    def load_vectorstore(self):
        """Load HC vector store"""
        vectorstore_path = Path(self.vectorstore_path)
        
        if not vectorstore_path.exists():
            raise FileNotFoundError(
                f"HC vector store not found at {vectorstore_path}\n"
                f"Please upload and process HR documents first"
            )
        
        self.vectorstore = FAISS.load_local(
            str(vectorstore_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Create retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.HC_TOP_K}
        )
    
    def create_qa_chain(self):
        """Create RAG chain for HC queries"""
        PROMPT = PromptTemplate(
            template=HC_RESPONSE_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
    
    def initialize(self):
        """Initialize complete HC system"""
        self.load_vectorstore()
        self.create_qa_chain()
    
    def query(self, question: str, verbose: bool = False) -> Dict:
        """Answer HC-related questions"""
        if not self.qa_chain:
            raise ValueError("HC Agent not initialized. Call initialize() first.")
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"[HC Agent] Question: {question}")
            print(f"{'='*60}\n")
        
        result = self.qa_chain.invoke({"query": question})
        
        sources = [
            {
                "document_id": doc.metadata.get('document_id', 'Unknown'),
                "title": doc.metadata.get('title', 'Unknown'),
                "doc_type": doc.metadata.get('doc_type', 'Document'),
                "filename": doc.metadata.get('filename', 'Unknown'),
                "content": doc.page_content
            }
            for doc in result["source_documents"]
        ]
        
        return {
            "answer": result["result"],
            "sources": sources,
            "chunks": len(sources)
        }
    
    def ask(self, question: str) -> Dict:
        """Alias for query() for backward compatibility"""
        return self.query(question)