# traffic_air.py
import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Desactivar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# CONFIGURACIÓN DE SEDES
# ============================================================================
AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "range": 2.0},
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.5},
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 2.0},
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.5},
    "beirut": {"lat": 33.8938, "lon": 35.5018, "range": 1.5},
    "santiago": {"lat": -33.4489, "lon": -70.6693, "range": 1.5},
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
OPENSKY_BASE_URL = "https://opensky-network.org/api"

REGIONS = {
    "europe": {"lamin": 45.8389, "lomin": 5.9962, "lamax": 47.8229, "lomax": 10.5226},
    "south_america": {"lamin": -33.0, "lomin": -71.0, "lamax": -30.0, "lomax": -68.0},
    "middle_east": {"lamin": 32.0, "lomin": 34.0, "lamax": 34.0, "lomax": 36.0},
    "asia": {"lamin": 30.0, "lomin": 120.0, "lamax": 33.0, "lomax": 123.0}
}

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validate_hq(hq_name: str) -> bool:
    """Validate if HQ exists in configuration"""
    return hq_name.lower() in AVAILABLE_LOCATIONS

def get_hq_coordinates(hq_name: str) -> Optional[Dict[str, float]]:
    """Get HQ coordinates and range"""
    if not validate_hq(hq_name):
        return None
    return AVAILABLE_LOCATIONS[hq_name.lower()]

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def get_flights_by_region(region: str = "europe") -> Optional[Dict[str, Any]]:
    """
    Obtiene vuelos en tiempo real de OpenSky para una región específica
    """
    if region not in REGIONS:
        print(f"❌ Región '{region}' no encontrada. Usando 'europe'")
        region = "europe"
    
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
            
            formatted_flights = []
            for flight in states:
                formatted_flights.append({
                    "icao24": flight[0],
                    "callsign": flight[1].strip() if flight[1] else "Unknown",
                    "origin_country": flight[2],
                    "time_position": flight[3],
                    "last_contact": flight[4],
                    "longitude": flight[5],
                    "latitude": flight[6],
                    "baro_altitude": flight[7],
                    "on_ground": flight[8],
                    "velocity": flight[9],
                    "true_track": flight[10],
                    "vertical_rate": flight[11],
                    "sensors": flight[12],
                    "geo_altitude": flight[13],
                    "squawk": flight[14],
                    "spi": flight[15],
                    "position_source": flight[16]
                })
            
            return {
                "status": "success",
                "region": region,
                "timestamp": datetime.now().isoformat(),
                "total_flights": len(formatted_flights),
                "flights": formatted_flights
            }
        else:
            return {
                "status": "error",
                "message": f"OpenSky API error: {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a OpenSky: {str(e)}"
        }

def get_flights_by_company_hq(hq_name: str) -> Dict[str, Any]:
    """
    Obtiene vuelos cerca de una sede específica
    """
    hq_name_lower = hq_name.lower().strip()
    
    # Validación
    if not validate_hq(hq_name_lower):
        return {
            "status": "error", 
            "message": f"Headquarter '{hq_name}' not configured.",
            "available_hqs": list(AVAILABLE_LOCATIONS.keys())
        }
    
    # Obtener datos de la sede
    hq_data = get_hq_coordinates(hq_name_lower)
    if not hq_data:
        return {
            "status": "error",
            "message": f"Could not retrieve coordinates for '{hq_name}'"
        }
    
    # Calcular bounding box con rango personalizado
    lat_min = hq_data["lat"] - hq_data["range"]
    lon_min = hq_data["lon"] - hq_data["range"]
    lat_max = hq_data["lat"] + hq_data["range"]
    lon_max = hq_data["lon"] + hq_data["range"]
    
    print(f"📡 Querying OpenSky for HQ [{hq_name_lower}] - BBox: ({lat_min:.2f}, {lon_min:.2f})")
    
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
                if flight[5] and flight[6]:  # Tiene coordenadas
                    flights.append({
                        "icao24": flight[0],
                        "callsign": flight[1].strip() if flight[1] else "Unknown",
                        "origin_country": flight[2],
                        "time_position": flight[3],
                        "last_contact": flight[4],
                        "longitude": flight[5],
                        "latitude": flight[6],
                        "baro_altitude": flight[7],
                        "on_ground": flight[8],
                        "velocity": flight[9],
                        "true_track": flight[10],
                        "vertical_rate": flight[11],
                        "sensors": flight[12],
                        "geo_altitude": flight[13],
                        "squawk": flight[14],
                        "spi": flight[15],
                        "position_source": flight[16]
                    })
            
            return {
                "status": "success",
                "location": hq_name_lower,
                "timestamp": datetime.now().isoformat(),
                "total_flights": len(flights),
                "flights": flights
            }
        else:
            return {
                "status": "error",
                "message": f"OpenSky API error: {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a OpenSky: {str(e)}"
        }

# ============================================================================
# FUNCIÓN DE PRUEBA
# ============================================================================

def test_traffic_air():
    """Prueba las funciones de tráfico aéreo"""
    print("=" * 60)
    print("✈️ DIAGNÓSTICO DE TRÁFICO AÉREO")
    print("=" * 60)
    
    # Probar vuelos en Europa
    print("\n📍 Región: Europa")
    result = get_flights_by_region("europe")
    if result and result["status"] == "success":
        print(f"✅ {result['total_flights']} vuelos detectados")
        for i, flight in enumerate(result["flights"][:3]):
            print(f"   ✈️ {i+1}. {flight['callsign']} - {flight['origin_country']} - Alt: {flight['baro_altitude']}m")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # Probar vuelos cerca de Rotterdam
    print("\n📍 Sede: Rotterdam")
    result = get_flights_by_company_hq("roterdam")
    if result and result["status"] == "success":
        print(f"✅ {result['total_flights']} vuelos cerca de Rotterdam")
        for flight in result["flights"][:3]:
            print(f"   ✈️ {flight['callsign']} - {flight['origin_country']} - Alt: {flight['baro_altitude']}m")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")

if __name__ == "__main__":
    test_traffic_air()
