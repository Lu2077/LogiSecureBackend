<<<<<<< HEAD
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
=======
import time
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings, get_cors_origins

# 🛰️ CLEAN SYMMETRIC ARCHITECTURE IMPORTS
from api.traffic_air import get_flights_by_company_hq

from api.traffic_land import get_land_traffic_by_hq, get_asset_tracking_by_id  # Combined predictive logic
from api.weather import get_live_weather_by_hq
from api.global_alerts import get_incidents_by_hq

from api.traffic_sea import (
    get_vessels_by_company_hq_async,
    get_vessels_by_bbox_async,
    get_vessel_by_mmsi_async
)



# 🔒 CONFIDENTIAL IN-MEMORY TMS DATABASE
from ai_agents.database import ENTERPRISE_SHIPMENTS

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified Enterprise Router API running securely on AMD local infrastructure"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
>>>>>>> 0436cee945067eb9dda6c9d62f2903ba4a7cb103
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
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
=======


@app.get("/", tags=["infra"])
async def root():
    """Service identity card. Lets humans and load balancers confirm what is running."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.BACKEND_ENV,
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health", tags=["infra"])
async def health():
    """Liveness probe used by the Docker HEALTHCHECK and orchestrators."""
    return {"status": "ok", "timestamp": time.time()}
    
#--------------$$$$TESTING_API_ENDPOINTS_FOR_VISALIZATION_&_DEBBUGIND!!$$$$$$$$$$$$$------------------

# 🚢 ENPOINTS MARÍTIMOS CONECTADOS AL SWAGGER UI DE TU DEVOPS
@app.get("/api/maritime/bbox", tags=["maritime"])
async def maritime_by_bbox(
    lat: float = Query(..., description="Latitud del centro"),
    lon: float = Query(..., description="Longitud del centro"),
    radius: float = Query(50, description="Radio en km")
):
    """🗺️ Buques en un área definida por el usuario (click/zoom en mapa)"""
    result = await get_vessels_by_bbox_async(lat, lon, radius)
    return result

# 🏁 2. COLOCAR EL ENDPOINT DE VARIABLE {hq} DESPUÉS
@app.get("/api/maritime/{hq}", tags=["maritime"])
async def maritime_by_hq(hq: str):
    """🚢 Buques en tiempo real cerca de una sede (AISstream WebSocket)"""
    result = await get_vessels_by_company_hq_async(hq)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Error"))
    return result

@app.get("/api/maritime/mmsi/{mmsi}", tags=["maritime"])
async def maritime_by_mmsi(mmsi: str):
    """🔍 Busca un buque específico por su MMSI"""
    result = await get_vessel_by_mmsi_async(mmsi)  # ✅ Sincronizado
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result
    
#-----------$$$$TRAFFIC_SEA_&_VESSELS$$$$----------------------------------$$$$

@app.get("/api/dashboard/sync", tags=["core_dashboard"])
async def sync_dashboard_by_hq(hq: str = Query("roterdam")):
    """
    EL ENDPOINT MAESTRO: Con una sola llamada, el Frontend de React 
    recibe absolutamente todo el estado de la sede para pintar el mapa completo.
    """
    # Como la consulta a AISstream es asíncrona nativa, la ejecutamos primero con await
    try:
        maritime_data = await get_vessels_by_company_hq_async(hq)
    except Exception as e:
        maritime_data = {"status": "error", "message": f"Maritime stream offline: {e}"}

    # El resto de las APIs (OpenSky, Open-Meteo, OSINT) corren sobre HTTP tradicional;
    # FastAPI las procesará de forma segura sin congelar el hilo de red.
    return {
        "location": hq.lower(),
        "timestamp": time.time(),
        "air_traffic": get_flights_by_company_hq(hq),
        "maritime_traffic": maritime_data,  # ✅ CONECTADO LOS 17 BARCOS REALES AQUÍ
        "land_traffic": get_land_traffic_by_hq(hq),
        "weather_telemetry": get_live_weather_by_hq(hq),
        "geopolitical_threats": get_incidents_by_hq(hq)
    }
    
@app.get("/api/shipment/track/{tracking_id}")
async def track_shipment_by_industry_id(tracking_id: str):
    """
    THE UNIFIED SEARCHER FOR THE FRONTEND.
    React sends any ID (AWB, MBL, BKG) and the backend resolves it intermodally.
    """
    id_upper = tracking_id.upper().strip()
    
    # 1. Check if the commercial document exists in our in-memory "ERP/TMS"
    if id_upper not in ENTERPRISE_SHIPMENTS:
        raise HTTPException(
            status_code=404, 
            detail=f"Tracking ID '{tracking_id}' not found in corporate records. Try: AWB-FEDEX-9942, MBL-MAERSK-2077 or BKG-LAND-04B"
        )
        
    shipment_meta = ENTERPRISE_SHIPMENTS[id_upper]
    mode = shipment_meta["mode"]
    
    # ✈️ CASE A: USER LOOKS FOR AN AIR WAYBILL (AWB) -> LIVE AIR TRACKING
    if mode == "AIR_LIVE":
        air_data = get_flights_by_company_hq("houston")
        couriers = air_data.get("data", {}).get("couriers", [])
        
        for flight in couriers:
            if flight["callsign"] == shipment_meta["carrier_callsign"]:
                return {
                    "tracking_id": id_upper,
                    "metadata": shipment_meta,
                    "tracking_mode": "LIVE_SATELLITE_AIR_TRACKING",
                    "display_color": "green",
                    "position": {"lat": flight["lat"], "lng": flight["lng"]},
                    "telemetry": flight
                }
        return {"tracking_id": id_upper, "metadata": shipment_meta, "tracking_mode": "AIR_FLEET_GATEWAY_PENDING", "display_color": "amber", "position": {"lat": 29.7604, "lng": -95.3698}}

    # 🚢 CASE B: USER LOOKS FOR A MASTER BILL OF LADING (MBL) -> LIVE MARITIME TRACKING
    elif mode == "OCEAN_LIVE":
        sea_data = get_vessels_by_company_hq("roterdam")
        liners = sea_data.get("data", {}).get("container_liners", [])
        
        for ship in liners:
            if ship["id"] == shipment_meta["vessel_mmsi"]:
                return {
                    "tracking_id": id_upper,
                    "metadata": shipment_meta,
                    "tracking_mode": "LIVE_AIS_MARITIME_TRACKING",
                    "display_color": "green",
                    "position": {"lat": ship["lat"], "lng": ship["lng"]},
                    "telemetry": ship
                }
        return {"tracking_id": id_upper, "metadata": shipment_meta, "tracking_mode": "PORT_ANCHORAGE_WAITING", "display_color": "amber", "position": {"lat": 51.9225, "lng": 4.4791}}

    # 🚛 CASE C: USER LOOKS FOR A LAND SHIPMENT -> ACTIVATES PREDICTIVE / ESTIMATED DISPLAY
    else:
        land_result = get_asset_tracking_by_id(id_upper)
        return land_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.BACKEND_ENV == "development",
    )

>>>>>>> 0436cee945067eb9dda6c9d62f2903ba4a7cb103
