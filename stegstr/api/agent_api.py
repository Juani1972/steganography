"""
FastAPI server exposing Stegstr AI Agent as REST endpoints.

Run: uvicorn stegstr.api.agent_api:app --host 0.0.0.0 --port 8000
"""

import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object
    BaseModel = object
    Field = lambda *a, **k: None
    HTTPException = Exception

from stegstr.ai_agent.interface import AIAgent


class AgentRequest(BaseModel):
    action: str = Field(..., description="Agent action")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    success: bool
    action: str
    data: Dict[str, Any]
    error: Optional[str] = None


_agent_instance: Optional[AIAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_instance
    _agent_instance = AIAgent()
    yield
    _agent_instance = None

if HAS_FASTAPI:
    app = FastAPI(title="Stegstr AI Agent API", description="REST API for agent operations", version="2.1.5", lifespan=lifespan)

    @app.post("/agent/execute", response_model=AgentResponse)
    async def execute(request: AgentRequest):
        if _agent_instance is None:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        result = _agent_instance.execute({**request.parameters, "action": request.action})
        return AgentResponse(**result)

    @app.get("/agent/actions")
    async def list_actions():
        if _agent_instance is None:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        return _agent_instance.list_actions()

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "2.1.5", "agent_ready": _agent_instance is not None}
else:
    app = None
