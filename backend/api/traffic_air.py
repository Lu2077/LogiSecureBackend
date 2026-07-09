# backend/api/traffic_air.py
"""
Air Traffic API - OpenSky Network Integration
"""

import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# CONFIGURACIÓN DE SEDES
# ============================================================================
AVAILABLE_LOCATIONS = {
    "rotterdam": {"lat": 51.9225, "lon": 4.4791, "range": 2.0},
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.5},
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 2.0},
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.5},
    "beirut": {"lat": 33.8938, "lon": 35.5018, "range": 1.5},
    "santiago": {"lat": -33.4489, "lon": -70.6693, "range": 1.5},
    "dubai": {"lat": 25.2528, "lon": 55.3644, "range": 2.0},
    "tokyo": {"lat": 35.7656, "lon": 140.3856, "range": 2.0},
}

OPENSKY_BASE_URL = "https://opensky-network.org/api"

REGIONS = {
    "europe": {"lamin": 45.8389, "lomin": 5.9962, "lamax": 47.8229, "lomax": 10.5226},
    "south_america": {"lamin": -33.0, "lomin": -71.0, "lamax": -30.0, "lomax": -68.0},
    "middle_east": {"lamin": 32.0, "lomin": 34.0, "lamax": 34.0, "lomax": 36.0},
    "asia": {"lamin": 30.0, "lomin": 120.0, "lamax": 33.0, "lomax": 123.0}
}

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def get_flights_by_region(region: str = "europe") -> Dict[str, Any]:
    """Get real-time flights from OpenSky for a specific region"""
    if region not in REGIONS:
        return {"status": "error", "message": f"Region '{region}' not found"}
    
    bounds = REGIONS[region]
    url = f"{OPENSKY_BASE_URL}/states/all"
    params = {
        "lamin": bounds["lamin"],
        "lomin": bounds["lomin"],
        "lamax": bounds["lamax"],
        "lomax": bounds["lomax"]
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            states = data.get("states", [])
            
            flights = []
            for flight in states:
                flights.append({
                    "icao24": flight[0],
                    "callsign": flight[1].strip() if flight[1] else "Unknown",
                    "origin_country": flight[2],
                    "longitude": flight[5],
                    "latitude": flight[6],
                    "baro_altitude": flight[7],
                    "on_ground": flight[8],
                    "velocity": flight[9],
                    "true_track": flight[10],
                    "vertical_rate": flight[11],
                    "geo_altitude": flight[13],
                })
            
            return {
                "status": "success",
                "region": region,
                "timestamp": datetime.now().isoformat(),
                "total_flights": len(flights),
                "flights": flights
            }
        else:
            return {"status": "error", "message": f"OpenSky API error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}

def get_flights_by_company_hq(hq_name: str) -> Dict[str, Any]:
    """Get flights near a specific headquarters"""
    hq_name_lower = hq_name.lower().strip()
    
    if hq_name_lower not in AVAILABLE_LOCATIONS:
        return {
            "status": "error",
            "message": f"HQ '{hq_name}' not found",
            "available_hqs": list(AVAILABLE_LOCATIONS.keys())
        }
    
    hq = AVAILABLE_LOCATIONS[hq_name_lower]
    lat_min = hq["lat"] - hq["range"]
    lon_min = hq["lon"] - hq["range"]
    lat_max = hq["lat"] + hq["range"]
    lon_max = hq["lon"] + hq["range"]
    
    url = f"{OPENSKY_BASE_URL}/states/all"
    params = {
        "lamin": lat_min,
        "lomin": lon_min,
        "lamax": lat_max,
        "lomax": lon_max
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            states = data.get("states", [])
            
            flights = []
            for flight in states:
                if flight[5] and flight[6]:  # Has coordinates
                    flights.append({
                        "icao24": flight[0],
                        "callsign": flight[1].strip() if flight[1] else "Unknown",
                        "origin_country": flight[2],
                        "longitude": flight[5],
                        "latitude": flight[6],
                        "baro_altitude": flight[7],
                        "on_ground": flight[8],
                        "velocity": flight[9],
                        "true_track": flight[10],
                        "vertical_rate": flight[11],
                        "geo_altitude": flight[13],
                    })
            
            return {
                "status": "success",
                "location": hq_name_lower,
                "timestamp": datetime.now().isoformat(),
                "total_flights": len(flights),
                "flights": flights
            }
        else:
            return {"status": "error", "message": f"OpenSky API error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("✈️ AIR TRAFFIC API TEST")
    print("=" * 60)
    
    # Test region
    print("\n📍 Region: Europe")
    result = get_flights_by_region("europe")
    if result.get("status") == "success":
        print(f"✅ {result['total_flights']} flights found")
        for f in result["flights"][:3]:
            print(f"   ✈️ {f['callsign']} - {f['origin_country']}")
    
    # Test HQ
    print("\n📍 HQ: Rotterdam")
    result = get_flights_by_company_hq("rotterdam")
    if result.get("status") == "success":
        print(f"✅ {result['total_flights']} flights near Rotterdam")
        for f in result["flights"][:3]:
            print(f"   ✈️ {f['callsign']} - {f['origin_country']}")
    
    print("\n✅ Air traffic test complete!")