import time
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings, get_cors_origins

# 🛰️ CLEAN SYMMETRIC ARCHITECTURE IMPORTS
from api.traffic_air import get_flights_by_company_hq
from api.traffic_sea import get_vessels_by_company_hq
from api.traffic_land import get_land_traffic_by_hq, get_asset_tracking_by_id  # Combined predictive logic
from api.weather import get_live_weather_by_hq
from api.global_alerts import get_incidents_by_hq

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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

@app.get("/api/dashboard/sync")
async def sync_dashboard_by_hq(hq: str = Query("roterdam")):
    """
    THE MASTER ENDPOINT: With a single call, the React Frontend
    receives absolutely everything about the headquarters' state to paint the complete map.
    """
    return {
        "location": hq,
        "timestamp": time.time(),
        "air_traffic": get_flights_by_company_hq(hq),
        "maritime_traffic": get_vessels_by_company_hq(hq),
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

