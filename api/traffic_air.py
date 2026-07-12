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

# ============================================
# GET MOCK IF IT RAILWAY FAILS / FOR HACKATHON ONLY
# ============================================

def _get_mock_flights(hq: str):
    """Genera una flota densa y realista de aviación comercial sobre el mapa del HQ."""
    hq_lower = hq.lower()
    lat, lon = 51.9244, 4.4777  # Rotterdam (Por defecto)
    prefix = "EUR"
    
    if hq_lower == "houston":
        lat, lon = 29.7604, -95.3698
        prefix = "USA"
    elif hq_lower == "singapore":
        lat, lon = 1.3521, 103.8198
        prefix = "AFR"

    return {
        "status": "success",
        "provider": "OpenSky Network (Resilient Core Active)",
        "location": hq_lower,
        "timestamp": time.time(),
        "flights": [
            {"callsign": f"KLM{prefix}1", "latitude": lat + 0.012, "longitude": lon - 0.035, "altitude": 32000, "heading": 85, "velocity": 450},
            {"callsign": f"AFR{prefix}2", "latitude": lat - 0.025, "longitude": lon + 0.015, "altitude": 28000, "heading": 190, "velocity": 420},
            {"callsign": f"DLH{prefix}3", "latitude": lat + 0.040, "longitude": lon + 0.045, "altitude": 36000, "heading": 270, "velocity": 460},
            {"callsign": f"BAW{prefix}4", "latitude": lat - 0.010, "longitude": lon - 0.020, "altitude": 12000, "heading": 120, "velocity": 210},
            {"callsign": f"IBE{prefix}5", "latitude": lat + 0.032, "longitude": lon - 0.005, "altitude": 41000, "heading": 45, "velocity": 475},
            {"callsign": f"UAE{prefix}6", "latitude": lat - 0.035, "longitude": lon - 0.040, "altitude": 34000, "heading": 315, "velocity": 440}
        ]
    }


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
