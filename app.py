import os
import json
import streamlit as st
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import pandas as pd
import time
import logging
from openai import AzureOpenAI
from dotenv import load_dotenv
import instructor
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
# Set page configuration
st.set_page_config(
    page_title="Badevel Living Lab Assistant",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Placeholder for Neo4jService (assumed to be implemented elsewhere)
class Neo4jService:
    @staticmethod
    def get_schema():
        # Replace with actual implementation
        return {"status": "success", "nodeLabels": [{"label": "Sensor", "properties": ["id", "type"]}]}
    
    @staticmethod
    def count_nodes_by_type():
        # Replace with actual implementation
        return {"status": "success", "results": [{"label": "Sensor", "count": 10}]}

# Initialize Azure OpenAI client
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

# Create an instructor-enabled client
instructor_client = instructor.from_openai(openai_client)

# Cache the assistant
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")
@st.cache_resource
def load_assistant():
    assistant = openai_client.beta.assistants.retrieve(ASSISTANT_ID)
    logger.info(f"Assistant loaded: {assistant.name}")
    return assistant

assistant = load_assistant()

# Cache Neo4j schema and node counts
@st.cache_data
def get_cached_schema():
    result = Neo4jService.get_schema()
    return result if result["status"] == "success" else None

@st.cache_data
def get_cached_node_counts():
    result = Neo4jService.count_nodes_by_type()
    return result if result["status"] == "success" else None



# Custom CSS for the beautiful theme
st.markdown("""
<style>
    :root {
        --primary-color: #8c6ef2;
        --secondary-color: #e0d539;
        --background-color: #f9fafd;
        --text-color: #333;
        --chat-user-bg: #f0f2f6;
        --chat-assistant-bg: rgba(140, 110, 242, 0.1);
        --border-radius: 12px;
        --box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    
    body {
        background-color: var(--background-color);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: var(--text-color);
    }
    
    /* Main container styling */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0;
    }
    
    /* Header styling */
    .app-header {
        display: flex;
        align-items: center;
        background: linear-gradient(90deg, var(--primary-color), var(--primary-color) 70%, var(--secondary-color));
        padding: 1rem 2rem;
        border-radius: var(--border-radius);
        margin-bottom: 2rem;
        box-shadow: var(--box-shadow);
        color: white;
    }
    
    .header-logo {
        font-size: 2.5rem;
        margin-right: 1rem;
    }
    
    .header-text {
        display: flex;
        flex-direction: column;
    }
    
    .header-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
    }
    
    .header-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
    }
    
    /* Chat container */
    .chat-container {
        height: 65vh;
        overflow-y: auto;
        padding: 1rem;
        border-radius: var(--border-radius);
        background-color: white;
        box-shadow: var(--box-shadow);
        margin-bottom: 1rem;
    }
    
    /* Button styling for suggestion cards */
    .stButton > button {
        background-color: white;
        border-radius: var(--border-radius);
        padding: 0.75rem 1rem;
        box-shadow: var(--box-shadow);
        border-left: 3px solid var(--secondary-color);
        width: 100%;
        text-align: left;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Example section */
    .example-section {
        margin-top: 2rem;
    }
    
    .example-title {
        color: var(--primary-color);
        margin-bottom: 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header section
st.markdown("""
<div class="app-header">
    <div class="header-logo">🏙️</div>
    <div class="header-text">
        <h1 class="header-title">Badevel Living Lab Assistant</h1>
        <p class="header-subtitle">Explorez les données du village intelligent de Badevel</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    thread = openai_client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "db_schema" not in st.session_state:
    st.session_state.db_schema = get_cached_schema()

if "node_counts" not in st.session_state:
    st.session_state.node_counts = get_cached_node_counts()

# Pydantic model for Cypher query extraction
class CypherQuery(BaseModel):
    query: str = Field(..., description="The Cypher query to visualize the graph")
    description: Optional[str] = Field(None, description="Description of what this query is showing")
    
    @classmethod
    def extract_from_text(cls, text: str) -> Optional['CypherQuery']:
        try:
            if "MATCH" in text and "RETURN" in text:
                lines = text.split("\n")
                query_lines = []
                in_query = False
                for line in lines:
                    if "MATCH" in line and not in_query:
                        in_query = True
                        query_lines.append(line)
                    elif in_query and any(keyword in line for keyword in ["RETURN", "WHERE", "WITH", "ORDER", "LIMIT"]):
                        query_lines.append(line)
                    elif in_query and not any(keyword in line for keyword in ["MATCH", "RETURN", "WHERE", "WITH", "ORDER", "LIMIT"]):
                        in_query = False
                if query_lines:
                    return cls(query=" ".join(query_lines).strip(), description="Automatically extracted query")
            return None
        except Exception as e:
            logger.error(f"Error extracting query: {str(e)}")
            return None

def extract_cypher_query(text: str) -> Optional[CypherQuery]:
    query = CypherQuery.extract_from_text(text)
    if query:
        return query
    return None

# Placeholder helper functions (replace with actual implementations)
def display_neovis(cypher_query, title="Graph Visualization"):
    st.write(f"Displaying NeoVis: {title} with query: {cypher_query}")

def process_run_with_tools(thread_id, run_id):
    # Placeholder: assumes tool processing returns run, tool_results, elements, debug_info
    return openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id), [], [], {}

# Display chat history
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "elements" in msg:
            for element in msg["elements"]:
                if element["type"] == "image":
                    st.image(base64.b64decode(element["content"]), caption=element.get("name", ""))
                elif element["type"] == "neovis":
                    if st.button("Show Visualization", key=f"vis_{idx}_{msg['role']}"):
                        display_neovis(element["query"], element.get("description", "Graph Visualization"))

# Process unprocessed user messages
if st.session_state.messages:
    last_msg = st.session_state.messages[-1]
    if last_msg["role"] == "user" and not last_msg.get("processed", False):
        with st.spinner("Processing..."):
            user_message = last_msg["content"]
            # Send message to the thread
            openai_client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=user_message
            )
            # Create a run
            run = openai_client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=ASSISTANT_ID
            )
            # Poll run status
            while run.status in ["queued", "in_progress"]:
                time.sleep(0.5)
                run = openai_client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
            # Handle tool calls if applicable
            tool_results, elements = [], []
            if run.status == "requires_action":
                run, tool_results, elements, _ = process_run_with_tools(st.session_state.thread_id, run.id)
            # Get assistant response
            messages = openai_client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
            for message in messages.data:
                if message.role == "assistant" and message.created_at > run.created_at:
                    content = "".join(part.text.value for part in message.content if part.type == "text")
                    assistant_message = {"role": "assistant", "content": content}
                    if elements:
                        assistant_message["elements"] = elements
                    elif cypher_query := extract_cypher_query(content):
                        assistant_message["elements"] = [{"type": "neovis", "query": cypher_query.query, "description": cypher_query.description}]
                    st.session_state.messages.append(assistant_message)
                    break
            # Mark the user message as processed
            last_msg["processed"] = True

# Chat input
user_input = st.chat_input("Posez une question sur le village intelligent...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input, "processed": False})

# Suggestion buttons
st.markdown('<div class="example-section">', unsafe_allow_html=True)
st.markdown('<div class="example-title">Suggestions de questions:</div>', unsafe_allow_html=True)

examples = [
    "Quels sont les capteurs présents à l'école maternelle?",
    "Quelle est la température actuelle dans la mairie?",
    "Montre-moi la consommation d'énergie de tous les bâtiments",
    "Quelles sont les relations entre les capteurs et les bâtiments?",
    "Quelle est la production d'énergie solaire actuelle?"
]

cols = st.columns(len(examples))
for i, example in enumerate(examples):
    with cols[i]:
        if st.button(example, key=f"example_{i}"):
            st.session_state.messages.append({"role": "user", "content": example, "processed": False})
            st.rerun()

