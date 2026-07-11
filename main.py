# backend/main.py
"""
LogiSecure AI - FastAPI Application
Unified Enterprise Router API running securely on AMD local infrastructure
"""

import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional

# ============================================
# CONFIGURATION
# ============================================
from config import settings, get_settings, get_cors_origins

# ============================================
# API IMPORTS - All traffic modules
# ============================================
from api.traffic_air import get_flights_by_company_hq
from api.traffic_land import (
    get_land_traffic_by_hq,
    get_asset_tracking_by_id,
    get_route_optimization
)
from api.weather import get_live_weather_by_hq
from api.global_alerts import get_incidents_by_hq
from api.traffic_sea import (
    get_vessels_by_company_hq_async,
    get_vessels_by_bbox_async,
    get_vessel_by_mmsi_async
)

# ============================================
# AI AGENTS
# ============================================
from models import IncidentRequest, HealthResponse
from agents import LogiSecureAgents
from logisecure_ai import LogiSecureAI
from logger import logger

# ============================================
# DATABASE
# ============================================
from ai_agents.database import ENTERPRISE_SHIPMENTS

# ============================================
# CREATE APP
# ============================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified Enterprise Router API running securely on AMD local infrastructure",
    docs_url="/docs"
)

# ============================================
# CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# INITIALIZE AGENTS
# ============================================

try:
    agents = LogiSecureAgents()
    logger.info("Agents ready")
except Exception as e:
    logger.error(f"Agents failed: {str(e)}")
    agents = None

try:
    ai = LogiSecureAI()
    logger.info("AI ready")
except Exception as e:
    logger.error(f"AI failed: {str(e)}")
    ai = None

# ============================================
# INFRASTRUCTURE ENDPOINTS
# ============================================

@app.get("/", tags=["infra"])
async def root():
    """Service identity card. Lets humans and load balancers confirm what is running."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.BACKEND_ENV,
        "provider": "Fireworks AI",
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health", tags=["infra"])
async def health():
    """Liveness probe used by the Docker HEALTHCHECK and orchestrators."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "agents": "ready" if agents else "unavailable"
    }

@app.get("/config", tags=["infra"])
async def get_config():
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Not available")
    return {
        "provider": "Fireworks AI",
        "model": settings.FIREWORKS_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "debug": settings.DEBUG,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD
    }

# ============================================
# AI AGENT ENDPOINTS
# ============================================

@app.post("/agent-analyze", tags=["ai"])
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

@app.get("/agent-status", tags=["ai"])
async def agent_status():
    return {
        "status": "ready" if agents else "unavailable",
        "provider": "Fireworks AI",
        "model": settings.FIREWORKS_MODEL,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD
    }

# ============================================
# AIR TRAFFIC ENDPOINTS
# ============================================

@app.get("/api/air/{hq}", tags=["air"])
async def air_traffic_by_hq(hq: str):
    """Get flights near a headquarters"""
    result = get_flights_by_company_hq(hq)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

# ============================================
# MARITIME ENDPOINTS
# ============================================

@app.get("/api/maritime/bbox", tags=["maritime"])
async def maritime_by_bbox(
    lat: float = Query(..., description="Latitud del centro"),
    lon: float = Query(..., description="Longitud del centro"),
    radius: float = Query(50, description="Radio en km")
):
    """Get vessels in a user-defined area (click/zoom on map)"""
    result = await get_vessels_by_bbox_async(lat, lon, radius)
    return result

@app.get("/api/maritime/{hq}", tags=["maritime"])
async def maritime_by_hq(hq: str):
    """Get vessels in real-time near a headquarters (AISstream WebSocket)"""
    result = await get_vessels_by_company_hq_async(hq)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Error"))
    return result

@app.get("/api/maritime/mmsi/{mmsi}", tags=["maritime"])
async def maritime_by_mmsi(mmsi: str):
    """Search for a specific vessel by its MMSI number"""
    result = await get_vessel_by_mmsi_async(mmsi)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

# ============================================
# LAND TRAFFIC ENDPOINTS
# ============================================

@app.get("/api/land/{hq}", tags=["land"])
async def land_traffic_by_hq(hq: str):
    """Get land traffic near a headquarters"""
    result = get_land_traffic_by_hq(hq)
    return result

@app.get("/api/land/track/{tracking_id}", tags=["land"])
async def land_track_by_id(tracking_id: str):
    """Track a specific land vehicle"""
    result = get_asset_tracking_by_id(tracking_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result)
    return result

@app.get("/api/land/route", tags=["land"])
async def land_route_optimization(
    origin: str = Query(..., description="Origin city"),
    destination: str = Query(..., description="Destination city"),
    shipment_type: Optional[str] = Query(None, description="Type of shipment")
):
    """Get optimized route between two points"""
    result = get_route_optimization(origin, destination, shipment_type)
    return result

# ============================================
# DASHBOARD - MASTER ENDPOINT
# ============================================

@app.get("/api/dashboard/sync", tags=["core_dashboard"])
async def sync_dashboard_by_hq(hq: str = Query("rotterdam")):
    """
    MASTER ENDPOINT: One call, React Frontend receives ALL HQ state to paint the full map.
    """
    try:
        maritime_data = await get_vessels_by_company_hq_async(hq)
    except Exception as e:
        maritime_data = {"status": "error", "message": f"Maritime stream offline: {e}"}

    return {
        "location": hq.lower(),
        "timestamp": time.time(),
        "air_traffic": get_flights_by_company_hq(hq),
        "maritime_traffic": maritime_data,
        "land_traffic": get_land_traffic_by_hq(hq),
        "weather_telemetry": get_live_weather_by_hq(hq),
        "geopolitical_threats": get_incidents_by_hq(hq)
    }

# ============================================
# SHIPMENT TRACKING
# ============================================

@app.get("/api/shipment/track/{tracking_id}", tags=["tracking"])
async def track_shipment_by_industry_id(tracking_id: str):
    """
    THE UNIFIED SEARCHER FOR THE FRONTEND.
    React sends any ID (AWB, MBL, BKG) and the backend resolves it intermodally.
    """
    id_upper = tracking_id.upper().strip()
    
    if id_upper not in ENTERPRISE_SHIPMENTS:
        raise HTTPException(
            status_code=404, 
            detail=f"Tracking ID '{tracking_id}' not found. Try: AWB-FEDEX-9942, MBL-MAERSK-2077 or BKG-LAND-04B"
        )
        
    shipment_meta = ENTERPRISE_SHIPMENTS[id_upper]
    mode = shipment_meta["mode"]
    
    if mode == "AIR_LIVE":
        air_data = get_flights_by_company_hq("houston")
        flights = air_data.get("flights", [])
        
        for flight in flights:
            if flight.get("callsign", "").upper() == shipment_meta["carrier_callsign"].upper():
                return {
                    "tracking_id": id_upper,
                    "metadata": shipment_meta,
                    "tracking_mode": "LIVE_SATELLITE_AIR_TRACKING",
                    "display_color": "green",
                    "position": {"lat": flight["latitude"], "lng": flight["longitude"]},
                    "telemetry": flight
                }
        return {
            "tracking_id": id_upper,
            "metadata": shipment_meta,
            "tracking_mode": "AIR_FLEET_GATEWAY_PENDING",
            "display_color": "amber",
            "position": {"lat": 29.7604, "lng": -95.3698}
        }

    elif mode == "OCEAN_LIVE":
        sea_data = await get_vessels_by_company_hq_async("rotterdam")
        vessels = sea_data.get("data", {}).get("all_vessels", [])
        
        for ship in vessels:
            if ship.get("mmsi") == shipment_meta["vessel_mmsi"]:
                return {
                    "tracking_id": id_upper,
                    "metadata": shipment_meta,
                    "tracking_mode": "LIVE_AIS_MARITIME_TRACKING",
                    "display_color": "green",
                    "position": {"lat": ship["lat"], "lng": ship["lon"]},
                    "telemetry": ship
                }
        return {
            "tracking_id": id_upper,
            "metadata": shipment_meta,
            "tracking_mode": "PORT_ANCHORAGE_WAITING",
            "display_color": "amber",
            "position": {"lat": 51.9225, "lng": 4.4791}
        }

    else:
        land_result = get_asset_tracking_by_id(id_upper)
        return land_result

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.BACKEND_ENV == "development",
    )
