# backend/main.py
"""
LogiSecure AI - FastAPI Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from config import settings
from models import IncidentRequest, HealthResponse
from agents import LogiSecureAgents
from logisecure_ai import LogiSecureAI
from logger import logger

# ============================================
# Create App
# ============================================

app = FastAPI(
    title="LogiSecure AI",
    description="Autonomous Logistics AI with Fireworks",
    version="3.0.0",
    docs_url="/docs",
    debug=settings.DEBUG
)

# ============================================
# CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Initialize
# ============================================

try:
    agents = LogiSecureAgents()
    logger.info("✅ Agents ready")
except Exception as e:
    logger.error(f"❌ Agents failed: {str(e)}")
    agents = None

try:
    ai = LogiSecureAI()
    logger.info("✅ AI ready")
except Exception as e:
    logger.error(f"❌ AI failed: {str(e)}")
    ai = None

# ============================================
# Endpoints
# ============================================

@app.get("/")
async def root():
    return {
        "message": "LogiSecure AI",
        "version": "3.0.0",
        "provider": "Fireworks AI",
        "status": "online"
    }

@app.post("/agent-analyze")
async def agent_analyze(request: IncidentRequest):
    if agents is None:
        raise HTTPException(status_code=503, detail="Agent system unavailable")
    
    try:
        result = agents.run(request.dict())
        return {
            "status": "success",
            "provider": "Fireworks AI",
            "analysis": result,
            "summary": agents.get_summary(result),
            "alerts": result.get("alerts", []),
            "affected_shipments": result.get("affected_shipments", []),
            "alternative_routes": result.get("alternative_routes", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return HealthResponse(
        status="healthy" if agents else "degraded",
        agents="ready" if agents else "unavailable",
        version="3.0.0"
    )

@app.get("/agent-status")
async def agent_status():
    return {
        "status": "ready" if agents else "unavailable",
        "provider": "Fireworks AI",
        "model": settings.FIREWORKS_MODEL,  # ← CHANGED
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD
    }

@app.get("/config")
async def get_config():
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Not available")
    return {
        "provider": "Fireworks AI",
        "model": settings.FIREWORKS_MODEL,  # ← CHANGED
        "temperature": settings.LLM_TEMPERATURE,
        "debug": settings.DEBUG,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 Starting on {settings.HOST}:{settings.PORT}")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)