"""
Unified Streamlit Web Interface for PT Bio Farma
Dual-Agent System:
- Agent 1: SOP Assistant (Filman Galuh Purnawidjaya - AVP Kepatuhan)
- Agent 2: Human Capital Assistant (Ditya Handayani - VP Layanan Human Capital)
"""
import streamlit as st
import requests
import time
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="PT Bio Farma Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e293b;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
        cursor: pointer;
    }
    .agent-card-hc {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .agent-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .chat-message {
        padding: 1.2rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: #f1f5f9;
        color: #1e293b;
        margin-right: 20%;
        border-left: 4px solid #3b82f6;
    }
    .source-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .badge-sop {
        background-color: #e3f2fd;
        color: #1565c0;
    }
    .badge-hc {
        background-color: #fce4ec;
        color: #c2185b;
    }
    </style>
""", unsafe_allow_html=True)

# Agent configurations
AGENT_CONFIGS = {
    "SOP Assistant": {
        "key": "sop",
        "persona": "",
        "position": "",
        "icon": "📋",
        "description": "Specialized in SOPs, Work Instructions, and Compliance Procedures",
        "badge_class": "badge-sop",
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "example_questions": [
            "What is the temperature for aseptic filling?",
            "How do I perform LAL endotoxin testing?",
            "What are the gowning requirements for Grade A?",
            "What is the timeline for investigating a major deviation?",
            "How do I handle a vial breakage during filling?",
            "What are the differential pressure requirements?",
        ],
        "endpoint": "/sop/ask",
        "upload_endpoint": None
    },
    "Human Capital Assistant": {
        "key": "hc",
        "persona": "",
        "position": "",
        "icon": "👥",
        "description": "Specialized in HR Policies, Employee Benefits, and Regulations",
        "badge_class": "badge-hc",
        "gradient": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "example_questions": [
            "What is the notice period?",
            "How many sick leaves do I get?",
            "What happens if I'm late?",
            "Tell me about exit formalities",
            "What is the reimbursement policy?",
            "What are the working hours?",
        ],
        "endpoint": "/hc/ask",
        "upload_endpoint": "/hc/upload"
    }
}

# Initialize session state
if 'current_agent' not in st.session_state:
    st.session_state.current_agent = "SOP Assistant"

if 'chat_histories' not in st.session_state:
    st.session_state.chat_histories = {key: [] for key in AGENT_CONFIGS.keys()}

if 'api_status' not in st.session_state:
    st.session_state.api_status = None

# Check API status
try:
    status_response = requests.get(f"{API_URL}/status", timeout=3)
    st.session_state.api_status = status_response.json()
    api_ready = True
except Exception as e:
    st.error("⚠️ **Backend API is not running**")
    st.info("Please start the API server:\n```bash\npython api_unified.py\n```")
    st.stop()

# Header
st.markdown('<div class="main-header">🏢 PT Bio Farma AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Dual-Agent System for SOP & Human Capital Support</div>', unsafe_allow_html=True)

# Agent Selector
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("📋 SOP Assistant\n", use_container_width=True, type="primary" if st.session_state.current_agent == "SOP Assistant" else "secondary"):
        st.session_state.current_agent = "SOP Assistant"
        st.rerun()

with col2:
    if st.button("👥 Human Capital Assistant\n", use_container_width=True, type="primary" if st.session_state.current_agent == "Human Capital Assistant" else "secondary"):
        st.session_state.current_agent = "Human Capital Assistant"
        st.rerun()

# Current agent info
current_config = AGENT_CONFIGS[st.session_state.current_agent]
st.markdown(f"""
<div style='background: {current_config["gradient"]}; padding: 1.5rem; border-radius: 10px; color: white; margin: 1rem 0;'>
    <div style='font-size: 1.5rem; font-weight: 600; margin-bottom: 0.5rem;'>
        {current_config["icon"]} {st.session_state.current_agent}
    </div>
    <div style='font-size: 1rem; opacity: 0.9; margin-bottom: 0.25rem;'>
        {current_config["persona"]} - {current_config["position"]}
    </div>
    <div style='font-size: 0.9rem; opacity: 0.8;'>
        {current_config["description"]}
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Show credential status
    if st.session_state.api_status and st.session_state.api_status.get("env_loaded"):
        st.success("✅ Credentials loaded")
    else:
        st.error("❌ .env file not found")
    
    st.divider()
    
    # Document upload for HC Agent
    if st.session_state.current_agent == "Human Capital Assistant":
        st.subheader("📄 Upload HR Document")
        uploaded_file = st.file_uploader(
            "Employee Manual (PDF/DOCX)",
            type=['pdf', 'docx', 'doc'],
            help="Upload your HR policy document"
        )
        
        if uploaded_file:
            if st.button("🔄 Build Index", type="primary", use_container_width=True):
                with st.spinner("Processing document..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = requests.post(f"{API_URL}/hc/upload", files=files)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Ready! {result.get('chunks_created', 0)} chunks created")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {response.json().get('detail', 'Upload failed')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.divider()
    
    # Example questions
    st.header("💡 Example Questions")
    
    for i, example in enumerate(current_config["example_questions"]):
        if st.button(example, key=f"example_{current_config['key']}_{i}", use_container_width=True):
            st.session_state.example_question = example
            st.rerun()
    
    st.divider()
    
    # Clear chat
    if st.button("🗑️ Clear Current Chat", use_container_width=True):
        st.session_state.chat_histories[st.session_state.current_agent] = []
        if 'example_question' in st.session_state:
            del st.session_state.example_question
        st.rerun()
    
    if st.button("🗑️ Clear All Chats", use_container_width=True):
        st.session_state.chat_histories = {key: [] for key in AGENT_CONFIGS.keys()}
        if 'example_question' in st.session_state:
            del st.session_state.example_question
        st.rerun()
    
    st.divider()
    
    # System status
    st.header("📊 System Status")
    if st.session_state.api_status:
        status = st.session_state.api_status
        
        if current_config["key"] == "sop":
            if status.get("sop_agent_ready"):
                st.success("✅ SOP Agent Ready")
            else:
                st.warning("⚠️ SOP Agent Not Ready")
                st.info("Run: python ingest_unified.py sop")
        else:
            if status.get("hc_agent_ready"):
                st.success("✅ HC Agent Ready")
            else:
                st.info("📋 Upload document to start")
        
        # Statistics
        current_history = st.session_state.chat_histories[st.session_state.current_agent]
        st.metric("Questions (Current)", len([m for m in current_history if m["role"] == "user"]))
        
        total_questions = sum(len([m for m in hist if m["role"] == "user"]) 
                            for hist in st.session_state.chat_histories.values())
        st.metric("Questions (All Agents)", total_questions)

# Main chat area
st.markdown("---")

# Get current chat history
current_history = st.session_state.chat_histories[st.session_state.current_agent]

# Display chat history
if current_history:
    for msg in current_history:
        if msg["role"] == "user":
            st.markdown(f"""
                <div class="chat-message user-message">
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">👤 You</div>
                    <div>{msg["content"]}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-message assistant-message">
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">{current_config["icon"]} {st.session_state.current_agent}</div>
                    <div>{msg["content"]}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Show sources
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 View Sources", expanded=False):
                    for source in msg["sources"]:
                        st.markdown(f"""
                        <div class="source-box">
                            <strong>{source.get('doc_type', 'Document')}</strong><br>
                            <strong>ID:</strong> {source.get('document_id', 'Unknown')}<br>
                            <strong>Title:</strong> {source.get('title', 'Unknown')}
                        </div>
                        """, unsafe_allow_html=True)
else:
    # Welcome message
    st.info(f"""
    👋 **Welcome to the {st.session_state.current_agent}!**
    
    **Current Agent:** {current_config["persona"]} ({current_config["position"]})
    
    **I can help you with:**
    {chr(10).join(['- ' + q for q in current_config["example_questions"][:3]])}
    
    **Get started:**
    {"1. Upload an HR document in the sidebar" if current_config["key"] == "hc" else "1. SOP documents are already loaded"}
    2. Ask your questions below!
    """)

# Handle example question
prompt_input = None
if 'example_question' in st.session_state:
    prompt_input = st.session_state.example_question
    del st.session_state.example_question

# Chat input
user_input = st.chat_input(f"💬 Ask {st.session_state.current_agent} a question...")

# Process input
if user_input or prompt_input:
    actual_input = prompt_input if prompt_input else user_input
    
    # Add user message
    current_history.append({
        "role": "user",
        "content": actual_input
    })
    
    # Check if agent is ready
    if current_config["key"] == "sop":
        agent_ready = st.session_state.api_status.get("sop_agent_ready", False)
    else:
        agent_ready = st.session_state.api_status.get("hc_agent_ready", False)
    
    if not agent_ready:
        error_msg = f"❌ {st.session_state.current_agent} is not ready. "
        if current_config["key"] == "sop":
            error_msg += "Please run: python ingest_unified.py sop"
        else:
            error_msg += "Please upload an HR document first."
        
        current_history.append({
            "role": "assistant",
            "content": error_msg,
            "sources": []
        })
        st.rerun()
    
    # Get AI response
    with st.spinner(f"🤔 {current_config['persona']} is thinking..."):
        try:
            response = requests.post(
                f"{API_URL}{current_config['endpoint']}",
                json={"question": actual_input},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                current_history.append({
                    "role": "assistant",
                    "content": result.get("answer", "No answer received"),
                    "sources": result.get("sources", [])
                })
            else:
                error_msg = response.json().get("detail", "Unknown error")
                current_history.append({
                    "role": "assistant",
                    "content": f"❌ Error: {error_msg}",
                    "sources": []
                })
        
        except Exception as e:
            current_history.append({
                "role": "assistant",
                "content": f"❌ Connection error: {str(e)}",
                "sources": []
            })
    
    st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #94a3b8; font-size: 0.9rem;">
    <p>PT Bio Farma AI Assistant | Powered by Azure OpenAI</p>
    <p>Currently using: <strong>{st.session_state.current_agent}</strong> ({current_config["persona"]})</p>
    <p>⚠️ Always verify critical information with official documentation</p>
</div>
""", unsafe_allow_html=True)