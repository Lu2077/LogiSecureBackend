import time
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import get_settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pre-configured coordinates of the world's most important logistics hubs.
AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "range": 2.0},  # Róterdam (Europe)
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.5}, # Logistic Hub Texas (USA)
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 2.0}, # Logistic center SaoPaulo (Brazil)
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.5},  # Shanghái port (Asia)
    #If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

# Cache configuration
FLIGHTS_CACHE = {}
CACHE_DURATION = 30  # 30 seconds for optimal hackathon performance
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Known cargo airlines patterns for classification
CARGO_PATTERNS = {
    "couriers": ["DHX", "FDX", "UPS", "DHL", "FEDEX"],
    "heavy_cargo": ["TAY", "BOX", "CLX", "GTI", "CARGOLUX", "KAL", "SIA", "CARGO"]
}

def validate_hq(hq_name: str) -> bool:
    """Validate if HQ exists in configuration"""
    return hq_name.lower() in AVAILABLE_LOCATIONS

def get_hq_coordinates(hq_name: str) -> Optional[Dict[str, float]]:
    """Get HQ coordinates and range"""
    if not validate_hq(hq_name):
        return None
    return AVAILABLE_LOCATIONS[hq_name.lower()]

def classify_flight(callsign: str) -> str:
    """Classify flight type based on callsign patterns"""
    if not callsign:
        return "unknown"
    
    callsign_upper = callsign.upper().strip()
    
    for pattern in CARGO_PATTERNS["couriers"]:
        if callsign_upper.startswith(pattern):
            return "courier"
    
    for pattern in CARGO_PATTERNS["heavy_cargo"]:
        if callsign_upper.startswith(pattern):
            return "heavy_cargo"
    
    return "unknown"

def process_flight_data(states: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process and classify flight data from OpenSky API
    Returns categorized flights with enriched information for backend and UI
    """
    couriers = []
    heavy_cargo = []
    all_flights = []
    
    for flight in states:
        if len(flight) < 11:
            continue
            
        callsign = flight[1].strip() if flight[1] else ""
        
        # Enriched object for internal processing / database / AI agents
        flight_info = {
            "icao24": flight[0],
            "callsign": callsign or "UNKNOWN",
            "origin_country": flight[2] or "UNKNOWN",
            "time_position": flight[3],
            "last_contact": flight[4],
            "longitude": flight[5],
            "latitude": flight[6],
            "baro_altitude": flight[7],
            "on_ground": flight[8],
            "velocity": flight[9],
            "true_track": flight[10],
            "vertical_rate": flight[11] if len(flight) > 11 else None,
            "sensors": flight[12] if len(flight) > 12 else None,
            "geo_altitude": flight[13] if len(flight) > 13 else None,
            "squawk": flight[14] if len(flight) > 14 else None,
            "spi": flight[15] if len(flight) > 15 else None,
            "position_source": flight[16] if len(flight) > 16 else None
        }
        
        all_flights.append(flight_info)
        flight_type = classify_flight(callsign)
        
        # Safe structure for Frontend UI to prevent rendering crashes
        simplified_flight = {
            "id": flight[0],
            "callsign": callsign or "UNKNOWN",
            "lng": flight[5] if flight[5] is not None else 0.0,
            "lat": flight[6] if flight[6] is not None else 0.0,
            "alt": flight[7] if flight[7] is not None else 0.0,
            "velocity": flight[9] if flight[9] is not None else 0.0,
            "heading": flight[10] if flight[10] is not None else 0.0
        }
        
        if flight_type == "courier":
            couriers.append(simplified_flight)
        elif flight_type == "heavy_cargo":
            heavy_cargo.append(simplified_flight)
    
    return {
        "all_flights": all_flights,
        "couriers": couriers,
        "heavy_cargo": heavy_cargo,
        "total_flights": len(all_flights),
        "total_couriers": len(couriers),
        "total_heavy_cargo": len(heavy_cargo)
    }

def get_flights_by_company_hq(hq_name: str) -> Dict[str, Any]:
    """
    Captura tráfico aéreo REAL e interactivo basándose exclusivamente 
    en la ubicación operativa seleccionada por la empresa.
    """
    current_time = time.time()
    hq_name_lower = hq_name.lower().strip()
    
    if not validate_hq(hq_name_lower):
        return {
            "status": "error", 
            "message": f"Headquarter '{hq_name}' not configured.",
            "available_hqs": list(AVAILABLE_LOCATIONS.keys())
        }
    
    hq = AVAILABLE_LOCATIONS[hq_name_lower]
    
    # Check RAM Cache
    if hq_name_lower in FLIGHTS_CACHE:
        cache_entry = FLIGHTS_CACHE[hq_name_lower]
        if (current_time - cache_entry["timestamp"]) < CACHE_DURATION:
            logger.info(f"⚡ Serving cached flight data for HQ [{hq_name_lower}]")
            return {
                "status": "success", 
                "location": hq_name_lower, 
                "data": cache_entry["data"],
                "cached": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Calculate bounding box geography
    lat_min = hq["lat"] - hq["range"]
    lon_min = hq["lon"] - hq["range"]
    lat_max = hq["lat"] + hq["range"]
    lon_max = hq["lon"] + hq["range"]
    
    logger.info(f"📡 Querying OpenSky for HQ [{hq_name_lower}] - BBox: ({lat_min:.2f}, {lon_min:.2f})")
    
    settings = get_settings()
    url = "https://opensky-network.org/api/states/all"
    
    params = {
        "lamin": lat_min,
        "lomin": lon_min,
        "lamax": lat_max,
        "lomax": lon_max
    }
    
    # Advanced Retry loop execution
    for attempt in range(MAX_RETRIES):
        try:
            auth = None
            if settings.OPENSKY_USERNAME and settings.OPENSKY_PASSWORD:
                auth = (settings.OPENSKY_USERNAME, settings.OPENSKY_PASSWORD)
            
            response = requests.get(url, params=params, auth=auth, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                states = data.get("states", []) or []
                processed_data = process_flight_data(states)
                
                FLIGHTS_CACHE[hq_name_lower] = {
                    "timestamp": current_time,
                    "data": processed_data
                }
                
                return {
                    "status": "success",
                    "location": hq_name_lower,
                    "data": processed_data,
                    "cached": False,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            elif response.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(f"⚠️ Rate limited (429). Attempt {attempt+1}/{MAX_RETRIES}. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ API Error {response.status_code}")
                break
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network request exception on attempt {attempt+1}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            continue

    # Safe Fallback: Return old cache if API or network fails completely
    if hq_name_lower in FLIGHTS_CACHE:
        logger.warning(f"♻️ Returning expired cache fallback for HQ [{hq_name_lower}] due to API failure.")
        return {
            "status": "fallback_success",
            "location": hq_name_lower,
            "data": FLIGHTS_CACHE[hq_name_lower]["data"],
            "cached": True,
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "status": "api_error",
        "message": "OpenSky API calls failed entirely after retries. No fallback cache available.",
        "data": {"all_flights": [], "couriers": [], "heavy_cargo": [], "total_flights": 0, "total_couriers": 0, "total_heavy_cargo": 0}
    }

