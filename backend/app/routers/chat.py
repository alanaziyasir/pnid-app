"""
Chat endpoints for LLM integration with Groq
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Groq API configuration - use environment variable
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Model mapping - using valid Groq models
MODEL_MAP = {
    "ALLAM": "llama-3.1-8b-instant",
    "Llama": "llama-3.3-70b-versatile",
    "Qwen": "llama-3.1-8b-instant",
    "GPT-OSS": "llama-3.3-70b-versatile",
}

# GraphML file path - configurable via environment variable
GRAPHML_PATH = Path(os.getenv("GRAPHML_PATH", "data/graph.graphml"))

def load_pnid_graph():
    """Load and parse the P&ID GraphML file into a text representation"""
    try:
        if not GRAPHML_PATH.exists():
            logger.warning(f"GraphML file not found at {GRAPHML_PATH}")
            return "Graph data not available.", {}, {}
            
        tree = ET.parse(GRAPHML_PATH)
        root = tree.getroot()
        
        # Handle namespace
        ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
        
        # Parse nodes
        nodes = {}
        components = []
        for node in root.findall('.//g:node', ns):
            node_id = node.get('id')
            node_data = {}
            for data in node.findall('g:data', ns):
                key = data.get('key')
                if key == 'd2':  # label
                    node_data['label'] = data.text
                elif key == 'd0':  # kind
                    node_data['kind'] = data.text
            nodes[node_id] = node_data
            if node_data.get('kind') == 'component':
                components.append(f"- {node_id}: {node_data.get('label', 'Unknown')}")
        
        # Parse edges (connections)
        connections = []
        for edge in root.findall('.//g:edge', ns):
            source = edge.get('source')
            target = edge.get('target')
            source_label = nodes.get(source, {}).get('label', source)
            target_label = nodes.get(target, {}).get('label', target)
            connections.append(f"- {source_label} ({source}) <-> {target_label} ({target})")
        
        # Build adjacency info for connectivity queries
        adjacency = {}
        for edge in root.findall('.//g:edge', ns):
            source = edge.get('source')
            target = edge.get('target')
            if source not in adjacency:
                adjacency[source] = []
            if target not in adjacency:
                adjacency[target] = []
            adjacency[source].append(target)
            adjacency[target].append(source)
        
        # Create readable adjacency list
        adjacency_text = []
        for node_id, neighbors in adjacency.items():
            node_label = nodes.get(node_id, {}).get('label', node_id)
            neighbor_labels = [f"{nodes.get(n, {}).get('label', n)} ({n})" for n in neighbors]
            adjacency_text.append(f"- {node_label} ({node_id}) connects to: {', '.join(neighbor_labels)}")
        
        graph_description = f"""
P&ID GRAPH DATA:

COMPONENTS ({len(components)} total):
{chr(10).join(components)}

PIPE CONNECTIONS ({len(connections)} total):
{chr(10).join(connections)}

CONNECTIVITY (what each component connects to):
{chr(10).join(adjacency_text)}
"""
        return graph_description, nodes, adjacency
    except Exception as e:
        logger.error(f"Error loading GraphML: {e}")
        return "Graph data not available.", {}, {}

# Load graph at startup
PNID_GRAPH_TEXT, PNID_NODES, PNID_ADJACENCY = load_pnid_graph()

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = "GPT-OSS"

class ChatResponse(BaseModel):
    response: str
    model: str

@router.post("/completions")
async def chat_completion(request: ChatRequest):
    """
    Send a chat completion request to Groq API
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable not set")
    
    try:
        # Get the model name for Groq
        groq_model = MODEL_MAP.get(request.model, "llama-3.3-70b-versatile")
        
        # Prepare messages for Groq API
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Add system message with P&ID graph context
        system_message = {
            "role": "system",
            "content": f"""You are a helpful P&ID assistant. Answer questions about this P&ID diagram concisely (1-3 sentences).

{PNID_GRAPH_TEXT}

When asked about connections:
- Use the CONNECTIVITY section to find direct connections
- Component IDs are like C0, C1, C2, etc.
- Answer directly whether components are connected or not
- If asked about paths, trace through the connectivity data"""
        }
        messages.insert(0, system_message)
        
        # Make request to Groq API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                json={
                    "model": groq_model,
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Groq API error: {response.text}"
                )
            
            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "response": assistant_message,
                    "model": request.model
                }
            )
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to Groq API timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

@router.get("/models")
async def list_models():
    """List available models"""
    return {
        "models": list(MODEL_MAP.keys()),
        "default": "GPT-OSS"
    }

@router.get("/graph-info")
async def get_graph_info():
    """Get the loaded P&ID graph information"""
    return {
        "nodes": len(PNID_NODES),
        "graph_loaded": len(PNID_GRAPH_TEXT) > 50,
        "components": [{"id": k, "label": v.get("label")} for k, v in PNID_NODES.items() if v.get("kind") == "component"]
    }
