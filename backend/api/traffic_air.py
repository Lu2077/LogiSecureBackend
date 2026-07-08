# traffic_air.py
import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Pre-configured coordinates of the world's most important logistics hubs.
AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "range": 2.0},  # Róterdam (Europe)
    "houston": {"lat": 29.7604, "lon": -95.3698, "range": 2.5}, # Logistic Hub Texas (USA)
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "range": 2.0}, # Logistic center SaoPaulo (Brazil)
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "range": 1.5},  # Shanghái port (Asia)
    #If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
OPENSKY_BASE_URL = "https://opensky-network.org/api"

# Regiones predefinidas para monitoreo
REGIONS = {
    "europe": {"lamin": 45.8389, "lomin": 5.9962, "lamax": 47.8229, "lomax": 10.5226},
    "south_america": {"lamin": -33.0, "lomin": -71.0, "lamax": -30.0, "lomax": -68.0},
    "middle_east": {"lamin": 32.0, "lomin": 34.0, "lamax": 34.0, "lomax": 36.0},
    "asia": {"lamin": 30.0, "lomin": 120.0, "lamax": 33.0, "lomax": 123.0}
}

def validate_hq(hq_name: str) -> bool:
    """Validate if HQ exists in configuration"""
    return hq_name.lower() in AVAILABLE_LOCATIONS

def get_hq_coordinates(hq_name: str) -> Optional[Dict[str, float]]:
    """Get HQ coordinates and range"""
    if not validate_hq(hq_name):
        return None
    return AVAILABLE_LOCATIONS[hq_name.lower()]

def get_flights_by_region(region: str = "europe") -> Optional[Dict[str, Any]]:
    """
    Obtiene vuelos en tiempo real de OpenSky para una región específica
    
    Args:
        region: Nombre de la región (europe, south_america, middle_east, asia)
    
    Returns:
        Dict con los datos de vuelos o None si falla
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
            
            # Formatear datos para facilitar el uso
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
    
    Args:
        hq_name: Nombre de la sede (roterdam, houston, etc.)
    
    Returns:
        Dict con los vuelos cercanos
    """
    # Mapeo de sedes a coordenadas
    HQ_COORDINATES = {
        "roterdam": {"lat": 51.92, "lon": 4.47},
        "houston": {"lat": 29.76, "lon": -95.36},
        "sao_paulo": {"lat": -23.55, "lon": -46.63},
        "shanghai": {"lat": 31.23, "lon": 121.47},
        "beirut": {"lat": 33.89, "lon": 35.50},
        "santiago": {"lat": -33.45, "lon": -70.66}
    }
    
    hq = hq_name.lower().strip()
    if hq not in HQ_COORDINATES:
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
    
    # Buscar vuelos en un radio aproximado (5 grados)
    url = f"{OPENSKY_BASE_URL}/states/all"
    params = {
        "lamin": coord["lat"] - 5,
        "lomin": coord["lon"] - 5,
        "lamax": coord["lat"] + 5,
        "lomax": coord["lon"] + 5
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
                        "callsign": flight[1].strip() if flight[1] else "Unknown",
                        "origin": flight[2],
                        "lat": flight[6],
                        "lng": flight[5],
                        "altitude": flight[7],
                        "velocity": flight[9],
                        "on_ground": flight[8]
                    })
            
            return {
                "status": "success",
                "location": hq,
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
            "message": f"Error: {str(e)}"
        }

# ============================================================================
# FUNCIÓN DE PRUEBA
# ============================================================================

def test_traffic_air():
    """Prueba las funciones de tráfico aéreo"""
    print("=" * 60)
    print("✈️ DIAGNÓSTICO DE TRÁFICO AÉREO")
    print("=" * 60)
    
    # 1. Probar vuelos en Europa
    print("\n📍 Región: Europa")
    result = get_flights_by_region("europe")
    if result and result["status"] == "success":
        print(f"✅ {result['total_flights']} vuelos detectados")
        # Mostrar primeros 3
        for i, flight in enumerate(result["flights"][:3]):
            print(f"   ✈️ {i+1}. {flight['callsign']} - {flight['origin_country']} - Alt: {flight['baro_altitude']}m")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # 2. Probar vuelos cerca de Beirut
    print("\n📍 Sede: Beirut")
    result = get_flights_by_company_hq("beirut")
    if result and result["status"] == "success":
        print(f"✅ {result['total_flights']} vuelos cerca de Beirut")
        for flight in result["flights"][:3]:
            print(f"   ✈️ {flight['callsign']} - {flight['origin']} - Alt: {flight['altitude']}m")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")

if __name__ == "__main__":
    test_traffic_air()
    
##MEJORAR FILTRADO PARA EL FRONT END!!!!
