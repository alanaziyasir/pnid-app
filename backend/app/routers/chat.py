"""
Chat endpoints for LLM integration with Groq
"""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

import httpx
from config import ENABLE_CHAT
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.logging import request_id
from app.resilience import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Groq API configuration - use environment variable
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
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
provider_circuit = CircuitBreaker()


def load_pnid_graph() -> tuple[str, dict[str, dict[str, str]], dict[str, list[str]]]:
    """Load and parse the P&ID GraphML file into a text representation"""
    try:
        if not GRAPHML_PATH.exists():
            logger.warning("graph_unavailable")
            return "Graph data not available.", {}, {}

        tree = ET.parse(GRAPHML_PATH)
        root = tree.getroot()

        # Handle namespace
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

        # Parse nodes
        nodes: dict[str, dict[str, str]] = {}
        components = []
        for node in root.findall(".//g:node", ns):
            node_id = node.get("id", "")
            node_data = {}
            for data in node.findall("g:data", ns):
                key = data.get("key")
                if key == "d2":  # label
                    node_data["label"] = data.text or "Unknown"
                elif key == "d0":  # kind
                    node_data["kind"] = data.text or ""
            nodes[node_id] = node_data
            if node_data.get("kind") == "component":
                components.append(f"- {node_id}: {node_data.get('label', 'Unknown')}")

        # Parse edges (connections)
        connections = []
        for edge in root.findall(".//g:edge", ns):
            source = edge.get("source", "")
            target = edge.get("target", "")
            source_label = nodes.get(source, {}).get("label", source)
            target_label = nodes.get(target, {}).get("label", target)
            connections.append(f"- {source_label} ({source}) <-> {target_label} ({target})")

        # Build adjacency info for connectivity queries
        adjacency: dict[str, list[str]] = {}
        for edge in root.findall(".//g:edge", ns):
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source not in adjacency:
                adjacency[source] = []
            if target not in adjacency:
                adjacency[target] = []
            adjacency[source].append(target)
            adjacency[target].append(source)

        # Create readable adjacency list
        adjacency_text = []
        for node_id, neighbors in adjacency.items():
            node_label = nodes.get(node_id, {}).get("label", node_id)
            neighbor_labels = [f"{nodes.get(n, {}).get('label', n)} ({n})" for n in neighbors]
            adjacency_text.append(
                f"- {node_label} ({node_id}) connects to: {', '.join(neighbor_labels)}"
            )

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
    except (ET.ParseError, OSError):
        logger.error("graph_load_failed")
        return "Graph data not available.", {}, {}


# Load graph at startup
PNID_GRAPH_TEXT, PNID_NODES, PNID_ADJACENCY = load_pnid_graph()


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16_000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=100)
    model: str = "GPT-OSS"


class ChatResponse(BaseModel):
    success: bool = True
    response: str
    model: str


class ModelsResponse(BaseModel):
    models: list[str]
    default: str


class GraphComponent(BaseModel):
    id: str
    label: str | None


class GraphInfoResponse(BaseModel):
    nodes: int
    graph_loaded: bool
    components: list[GraphComponent]


@router.post("/completions")
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """
    Send a chat completion request to Groq API
    """
    if not ENABLE_CHAT:
        raise HTTPException(status_code=503, detail="Chat is temporarily disabled")
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="Chat provider is not configured")

    try:
        provider_circuit.acquire()
    except CircuitOpenError as error:
        raise HTTPException(
            status_code=503,
            detail="Chat provider is temporarily unavailable",
            headers={"Retry-After": "30"},
        ) from error

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
- If asked about paths, trace through the connectivity data""",
        }
        messages.insert(0, system_message)

        # Make request to Groq API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "X-Request-ID": request_id.get(),
                },
                json={
                    "model": groq_model,
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.3,
                },
            )

            if response.status_code != 200:
                if response.status_code == 429 or response.status_code >= 500:
                    provider_circuit.failure()
                else:
                    provider_circuit.success()
                logger.warning("chat_provider_rejected", extra={"status": response.status_code})
                raise HTTPException(status_code=502, detail="Chat provider rejected the request")

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            if not isinstance(assistant_message, str) or not assistant_message.strip():
                raise ValueError("Invalid provider content")
            provider_circuit.success()

            return ChatResponse(response=assistant_message, model=request.model)

    except httpx.TimeoutException as error:
        provider_circuit.failure()
        raise HTTPException(status_code=504, detail="Chat provider timed out") from error
    except httpx.RequestError as error:
        provider_circuit.failure()
        raise HTTPException(status_code=502, detail="Chat provider is unavailable") from error
    except HTTPException:
        raise
    except (ValueError, KeyError, IndexError, TypeError) as error:
        provider_circuit.failure()
        logger.error("invalid_provider_response", extra={"error_type": type(error).__name__})
        raise HTTPException(status_code=502, detail="Invalid chat provider response") from error


@router.get("/models")
async def list_models() -> ModelsResponse:
    """List available models"""
    return ModelsResponse(models=list(MODEL_MAP.keys()), default="GPT-OSS")


@router.get("/graph-info")
async def get_graph_info() -> GraphInfoResponse:
    """Get the loaded P&ID graph information"""
    return GraphInfoResponse(
        nodes=len(PNID_NODES),
        graph_loaded=len(PNID_GRAPH_TEXT) > 50,
        components=[
            GraphComponent(id=k, label=v.get("label"))
            for k, v in PNID_NODES.items()
            if v.get("kind") == "component"
        ],
    )
