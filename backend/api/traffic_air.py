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
SEDES_DISPONIBLES = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "range": 2.0},  # Róterdam Roterdam (Europe)
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.5}, # Logistic Hub Texas (USA)
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 2.0}, # Logistic center SaoPaulo (Brazil)
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.5}  # Shanghái port (Asia)
}

# Cache configuration
FLIGHTS_CACHE = {}
CACHE_DURATION = 30  # Increased to 30 seconds for better performance
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Known cargo airlines patterns for classification
CARGO_PATTERNS = {
    "couriers": ["DHX", "FDX", "UPS", "DHL", "FEDEX"],
    "heavy_cargo": ["TAY", "BOX", "CLX", "GTI", "CARGOLUX", "KAL", "SIA", "CARGO"]
}

def validate_hq(hq_name: str) -> bool:
    """Validate if HQ exists in configuration"""
    return hq_name in SEDES_DISPONIBLES

def get_hq_coordinates(hq_name: str) -> Optional[Dict[str, float]]:
    """Get HQ coordinates and range"""
    if not validate_hq(hq_name):
        return None
    return SEDES_DISPONIBLES[hq_name]

def classify_flight(callsign: str) -> str:
    """Classify flight type based on callsign patterns"""
    if not callsign:
        return "unknown"
    
    callsign_upper = callsign.upper().strip()
    
    # Check courier patterns
    for pattern in CARGO_PATTERNS["couriers"]:
        if callsign_upper.startswith(pattern):
            return "courier"
    
    # Check heavy cargo patterns
    for pattern in CARGO_PATTERNS["heavy_cargo"]:
        if callsign_upper.startswith(pattern):
            return "heavy_cargo"
    
    return "unknown"

def process_flight_data(states: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process and classify flight data from OpenSky API
    Returns categorized flights with enriched information
    """
    couriers = []
    heavy_cargo = []
    all_flights = []
    
    for flight in states:
        # Ensure flight has minimum required fields
        if len(flight) < 11:
            continue
            
        # Extract and clean callsign
        callsign = flight[1].strip() if flight[1] else ""
        
        # Create enriched flight data
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
        
        # Add to all flights
        all_flights.append(flight_info)
        
        # Classify and add to appropriate categories
        flight_type = classify_flight(callsign)
        
        # Keep simplified version for UI
        simplified_flight = {
            "id": flight[0],
            "callsign": callsign,
            "lng": flight[5],
            "lat": flight[6],
            "alt": flight[7],
            "velocity": flight[9],
            "heading": flight[10]
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
    
    # Validate HQ exists
    if not validate_hq(hq_name):
        return {
            "status": "error", 
            "message": f"Headquarter '{hq_name}' not configured.",
            "available_hqs": list(SEDES_DISPONIBLES.keys())
        }
    
    hq = SEDES_DISPONIBLES[hq_name]
    hq_name_lower = hq_name.lower()
    
    # Check cache
    if hq_name_lower in FLIGHTS_CACHE:
        cache_entry = FLIGHTS_CACHE[hq_name_lower]
        if (current_time - cache_entry["timestamp"]) < CACHE_DURATION:
            logger.info(f"⚡ Serving cached flight data for HQ [{hq_name}]")
            return {
                "status": "success", 
                "location": hq_name, 
                "data": cache_entry["data"],
                "cached": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Calculate bounding box
    lat_min = hq["lat"] - hq["range"]
    lon_min = hq["lon"] - hq["range"]
    lat_max = hq["lat"] + hq["range"]
    lon_max = hq["lon"] + hq["range"]
    
    logger.info(f"📡 Querying OpenSky for HQ [{hq_name}] - BBox: ({lat_min:.2f}, {lon_min:.2f}) to ({lat_max:.2f}, {lon_max:.2f})")
    
    settings = get_settings()
    url = "https://opensky-network.org/api/states/all"
    
    params = {
        "lamin": lat_min,
        "lomin": lon_min,
        "lamax": lat_max,
        "lomax": lon_max
    }
    
    # Retry logic
    for attempt in range(MAX_RETRIES):
        try:
            # Use authentication if provided, otherwise try without
            auth = None
            if settings.OPENSKY_USERNAME and settings.OPENSKY_PASSWORD:
                auth = (settings.OPENSKY_USERNAME, settings.OPENSKY_PASSWORD)
            
            response = requests.get(
                url, 
                params=params, 
                auth=auth,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                states = data.get("states", []) or []
                
                # Process and classify flights
                processed_data = process_flight_data(states)
                
                # Cache the result
                FLIGHTS_CACHE[hq_name_lower] = {
                    "timestamp": current_time,
                    "data": processed_data
                }
                
                logger.info(f"✅ Retrieved {processed_data['total_flights']} flights for HQ [{hq_name}]")
                
                return {
                    "status": "success",
                    "location": hq_name,
                    "data": processed_data,
                    "cached": False,
                    "timestamp": datetime.utcnow().isoformat()
                }
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(f"⚠️ Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ API Error {response.status_code}: {response.text[:200]}")
                return {
                    "status": "api_error",
                    "message": f"OpenSky API returned status {response.status_code}",
                    "data": {
                        "all_flights": [],
                        "couriers": [],
                        "heavy_cargo": [],
                        "total_flights": 0
                    }
                }
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            else:
                return {
                    "status": "network_error",
                    "message": "Timeout connecting to OpenSky API",
                    "data": {
                        "all_flights": [],
                        "couriers": [],
                        "heavy_cargo": [],
                        "total_flights": 0
                    }
                }
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return {
                "status": "network_error",
                "message": f"Error fetching flight data: {str(e)}",
                "data": {
                    "all_flights": [],
                    "couriers": [],
                    "heavy_cargo": [],
                    "total_flights": 0
                }
            }
    
    # If we get here, all retries failed
    return {
        "status": "network_error",
        "message": "Failed to fetch flight data after multiple retries",
        "data": {
            "all_flights": [],
            "couriers": [],
            "heavy_cargo": [],
            "total_flights": 0
        }
    }

def clear_flight_cache(hq_name: Optional[str] = None) -> Dict[str, Any]:
    """Clear flight cache for specific HQ or all HQs"""
    if hq_name:
        hq_name_lower = hq_name.lower()
        if hq_name_lower in FLIGHTS_CACHE:
            del FLIGHTS_CACHE[hq_name_lower]
            return {"status": "success", "message": f"Cache cleared for {hq_name}"}
        else:
            return {"status": "error", "message": f"No cache found for {hq_name}"}
    else:
        FLIGHTS_CACHE.clear()
        return {"status": "success", "message": "All cache cleared"}

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    stats = {
        "total_cached_hqs": len(FLIGHTS_CACHE),
        "cached_hqs": list(FLIGHTS_CACHE.keys()),
        "cache_ttl": CACHE_DURATION,
        "cache_entries": {}
    }
    
    for hq, entry in FLIGHTS_CACHE.items():
        age = int(time.time() - entry["timestamp"])
        stats["cache_entries"][hq] = {
            "age_seconds": age,
            "expires_in_seconds": max(0, CACHE_DURATION - age),
            "total_flights": entry["data"].get("total_flights", 0)
        }
    
    return stats
