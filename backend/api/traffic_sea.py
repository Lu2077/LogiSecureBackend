import time
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import get_settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# We reuse the exact same key coordinates of your global logistics hubs.
AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "range": 1.5},  # Puerto de Róterdam
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.0}, # Hub Marítimo Texas
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 1.5}, # Puerto de Santos (Brasil)
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.0}  # Puerto de Shanghái
    #If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

# Cache and Network Configuration
SHIPS_CACHE = {}
CACHE_DURATION = 30  # 30 seconds symmetry with air traffic
MAX_RETRIES = 2
RETRY_DELAY = 1

# Patterns for marine vessel classification (AIS Ship Types)
# Cargo types 70-79 are Container Ships/Cargo. Types 80-89 are Tankers/LNG.
VESS_PATTERNS = {
    "liners": ["MAERSK", "MSC", "CMA", "COSCO", "ONE", "EVERGREEN", "HAPAG"],
    "heavy_tankers": ["LNG", "TANKER", "OIL", "BULK", "GAS", "PETRO"]
}

def validate_hq(hq_name: str) -> bool:
    return hq_name.lower() in AVAILABLE_LOCATIONS

def classify_vessel(ship_name: str, ship_type_code: int) -> str:
    """Classify marine vessels based on AIS registered name and type codes"""
    if not ship_name:
        ship_name = ""
    
    name_upper = ship_name.upper().strip()
    
    # Rule 1: Code based checking (AIS Standard)
    if 80 <= ship_type_code <= 89:
        return "heavy_tanker"
    if 70 <= ship_type_code <= 79:
        return "container_liner"
        
    # Rule 2: Name pattern matching fallback
    for pattern in VESS_PATTERNS["liners"]:
        if pattern in name_upper:
            return "container_liner"
            
    for pattern in VESS_PATTERNS["heavy_tankers"]:
        if pattern in name_upper:
            return "heavy_tanker"
            
    return "unknown"

def process_vessel_data(raw_ships: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Process and classify raw AIS tracking data into clean JSON for React UI"""
    container_liners = []
    heavy_tankers = []
    all_vessels = []
    
    for ship in raw_ships:
        # Expected index mapping from AIS stream payload parsing
        ship_name = ship.get("name", "UNKNOWN").strip()
        mmsi = ship.get("mmsi", "000000000")
        type_code = ship.get("type_code", 70)
        
        vessel_info = {
            "mmsi": mmsi,
            "name": ship_name or "UNKNOWN",
            "flag": ship.get("flag", "UNKNOWN"),
            "lng": ship.get("lng", 0.0),
            "lat": ship.get("lat", 0.0),
            "vessel_type_code": type_code,
            "speed_knots": ship.get("speed", 0.0),
            "course_deg": ship.get("course", 0.0),
            "destination": ship.get("destination", "OPEN SEA")
        }
        
        all_vessels.append(vessel_info)
        vessel_type = classify_vessel(ship_name, type_code)
        
        # Simplified object ready for Leaflet Map render
        simplified_vessel = {
            "id": mmsi,
            "callsign": ship_name,
            "lng": ship.get("lng", 0.0),
            "lat": ship.get("lat", 0.0),
            "velocity": ship.get("speed", 0.0),
            "heading": ship.get("course", 0.0)
        }
        
        if vessel_type == "container_liner":
            container_liners.append(simplified_vessel)
        elif vessel_type == "heavy_tanker":
            heavy_tankers.append(simplified_vessel)
            
    return {
        "all_vessels": all_vessels,
        "container_liners": container_liners,
        "heavy_tankers": heavy_tankers,
        "total_vessels": len(all_vessels),
        "total_liners": len(container_liners),
        "total_tankers": len(heavy_tankers)
    }

def get_vessels_by_company_hq(hq_name: str) -> Dict[str, Any]:
    """Captures real-time marine AIS traffic scoped inside the corporate HQ perimeter"""
    current_time = time.time()
    hq_name_lower = hq_name.lower().strip()
    
    if not validate_hq(hq_name_lower):
        return {
            "status": "error", 
            "message": f"Headquarter '{hq_name}' not configured for maritime tracking.",
            "available_hqs": list(SEDES_DISPONIBLES.keys())
        }
        
    hq = SEDES_DISPONIBLES[hq_name_lower]
    
    # Check RAM cache memory boundary
    if hq_name_lower in SHIPS_CACHE:
        cache = SHIPS_CACHE[hq_name_lower]
        if (current_time - cache["timestamp"]) < CACHE_DURATION:
            logger.info(f"⚡ Serving cached maritime data for Port HQ [{hq_name_lower}]")
            return {
                "status": "success",
                "location": hq_name_lower,
                "data": cache["data"],
                "cached": True,
                "timestamp": datetime.utcnow().isoformat()
            }

    # Bounding Box calculations for port perimeters
    lat_min = hq["lat"] - hq["range"]
    lon_min = hq["lon"] - hq["range"]
    lat_max = hq["lat"] + hq["range"]
    lon_max = hq["lon"] + hq["range"]
    
    logger.info(f"⚓ Querying Maritime AIS layer for HQ [{hq_name_lower}]")
    
    settings = get_settings()
    
    # For the Hackathon demo, if there is no active API key, the backend will intercept. 
    # a local, geographically redundant REST feed to prevent connection failures (Safe Fallback)
    if not settings.AISSTREAM_API_KEY:
        # Mocking real structure payload to allow frontend work immediately if key isn't registered yet
        mock_ships = [
            {"mmsi": "244130000", "name": "MAERSK MC-KINNEY MOLLER", "flag": "Denmark", "lng": lon_min + 0.4, "lat": lat_min + 0.3, "type_code": 70, "speed": 18.4, "course": 95.0, "destination": hq_name_lower.upper()},
            {"mmsi": "211622000", "name": "MSC OSCAR", "flag": "Panama", "lng": lon_min + 0.6, "lat": lat_min + 0.5, "type_code": 72, "speed": 21.0, "course": 110.0, "destination": hq_name_lower.upper()},
            {"mmsi": "311000123", "name": "AL GHAWRIYA LNG", "flag": "Qatar", "lng": lon_min + 0.2, "lat": lat_min + 0.8, "type_code": 85, "speed": 15.2, "course": 240.0, "destination": "OPEN SEA"}
        ]
        processed_data = process_vessel_data(mock_ships)
        SHIPS_CACHE[hq_name_lower] = {"timestamp": current_time, "data": processed_data}
        return {"status": "success", "location": hq_name_lower, "data": processed_data, "cached": False, "timestamp": datetime.utcnow().isoformat()}

    # In the event that the actual VesselAPI/AISstream key is configured
    url = f"https://vesselapi.com" 
    params = {"lamin": lat_min, "lomin": lon_min, "lamax": lat_max, "lomax": lon_max, "apikey": settings.AISSTREAM_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 200:
            states = response.json().get("vessels", [])
            processed_data = process_vessel_data(states)
            SHIPS_CACHE[hq_name_lower] = {"timestamp": current_time, "data": processed_data}
            return {"status": "success", "location": hq_name_lower, "data": processed_data, "cached": False, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"❌ Maritime external connection failure: {e}")
        
    return {
        "status": "error",
        "message": "AIS marine services unavailable.",
        "data": {"all_vessels": [], "container_liners": [], "heavy_tankers": [], "total_vessels": 0}
    }

