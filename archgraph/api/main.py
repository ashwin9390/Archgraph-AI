"""
ArchGraph AI — REST API (FastAPI)
Run: uvicorn archgraph.api.main:app --reload
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Graph is loaded once at startup
_graph: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    from archgraph.graph.graph_manager import create_graph
    from archgraph.graph.seed_data import SEED_TECHNIQUES

    uri = os.getenv("NEO4J_URI", "")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    _graph = create_graph(uri=uri, user=user, password=password)
    _graph.load_seed_data(SEED_TECHNIQUES)
    yield
    _graph.close()


app = FastAPI(
    title="ArchGraph AI",
    description="Citation-backed system design critique engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class CritiqueRequest(BaseModel):
    description: str
    team_size: Optional[int] = None
    domain: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "description": "Self-managed Kafka + Cassandra, 3 backend engineers, 60k writes/sec",
            "team_size": 3,
        }
    }}


class IngestRequest(BaseModel):
    urls: list[str]
    concurrency: int = 5


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "graph": _graph.stats() if _graph else None}


@app.get("/techniques")
def list_techniques(domain: Optional[str] = None):
    if domain:
        return _graph.query_by_domain(domain)
    return _graph.get_all_techniques()


@app.post("/critique")
def critique(req: CritiqueRequest):
    from archgraph.critic.engine import ArchitectureInput, CriticEngine

    arch = ArchitectureInput.from_text(req.description)
    if req.team_size:
        arch.team_size = req.team_size
    if req.domain:
        arch.domain = req.domain

    engine = CriticEngine(_graph)
    report = engine.critique(arch)
    return report.render_dict()


@app.post("/ingest")
async def ingest(req: IngestRequest):
    from archgraph.ingestion.fetcher import IngestionPipeline

    pipeline = IngestionPipeline(concurrency=req.concurrency)
    articles = await pipeline.ingest_batch(req.urls)
    return {
        "ingested": len(articles),
        "articles": [a.to_dict() for a in articles],
    }


@app.get("/stats")
def stats():
    return _graph.stats()
