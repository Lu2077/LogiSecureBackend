# weather.py
import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Desactivar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "timezone": "Europe/Amsterdam"},
    "houston": {"lat": 29.7604, "lon": -95.3698, "timezone": "America/Chicago"},
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "timezone": "America/Sao_Paulo"},
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "timezone": "Asia/Shanghai"},
    #If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node", "timezone": "UTC"}
}

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def get_weather(lat: float, lon: float, location_name: str = "Ubicación") -> Optional[Dict[str, Any]]:
    """
    Obtiene el clima actual de Open-Meteo para una ubicación
    
    if hq_name_lower not in AVAILABLE_LOCATIONS:
        return {"status": "error", "message": "HQ not configured for weather telemetry."}
        
    hq = AVAILABLE_LOCATIONS[hq_name_lower]
    
    Returns:
        Dict con datos climáticos o None si falla
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true"
    }
    
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get("current_weather", {})
            
            temp = current.get("temperature")
            wind_speed = current.get("windspeed")
            wind_dir = current.get("winddirection")
            weather_code = current.get("weathercode")
            time = current.get("time")
            is_day = current.get("is_day")
            
            # Traducir código de clima
            condition = WEATHER_CODES.get(weather_code, f"Código {weather_code}")
            
            return {
                "status": "success",
                "location": location_name,
                "lat": lat,
                "lon": lon,
                "timestamp": time,
                "temperature": temp,
                "temperature_unit": "°C",
                "wind_speed": wind_speed,
                "wind_speed_unit": "km/h",
                "wind_direction": wind_dir,
                "wind_direction_unit": "°",
                "weather_code": weather_code,
                "condition": condition,
                "is_day": is_day == 1,
                "source": "Open-Meteo",
                "elevation": data.get("elevation"),
                "timezone": data.get("timezone")
            }
        else:
            return {
                "status": "error",
                "message": f"Open-Meteo error: {response.status_code}",
                "location": location_name
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a Open-Meteo: {str(e)}",
            "location": location_name
        }

def get_weather_by_hq(hq_name: str) -> Dict[str, Any]:
    """
    Obtiene el clima para una sede específica
    
    Args:
        hq_name: Nombre de la sede (roterdam, houston, etc.)
    
    Returns:
        Dict con datos climáticos
    """
    # Mapeo de sedes a coordenadas
    HQ_COORDINATES = {
        "roterdam": {"lat": 51.92, "lon": 4.47},
        "houston": {"lat": 29.76, "lon": -95.36},
        "sao_paulo": {"lat": -23.55, "lon": -46.63},
        "shanghai": {"lat": 31.23, "lon": 121.47},
        "beirut": {"lat": 33.89, "lon": 35.50},
        "santiago": {"lat": -33.45, "lon": -70.66},
        "puerto_cabello": {"lat": 10.48, "lon": -68.01},
        "punta_arenas": {"lat": -53.16, "lon": -70.91}
    }
    
    hq = hq_name.lower().strip()
    if hq not in HQ_COORDINATES:
        return {
            "status": "error",
            "message": f"Sede '{hq_name}' no encontrada",
            "available_locations": list(HQ_COORDINATES.keys())
        }
    
    coord = HQ_COORDINATES[hq]
    return get_weather(coord["lat"], coord["lon"], hq)

def get_weather_multiple_locations(locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Obtiene el clima para múltiples ubicaciones
    
    Args:
        locations: Lista de dicts con "name", "lat", "lon"
    
    Returns:
        Dict con todos los resultados
    """
    results = {}
    for loc in locations:
        name = loc.get("name", "Unknown")
        lat = loc.get("lat")
        lon = loc.get("lon")
        if lat and lon:
            results[name] = get_weather(lat, lon, name)
    return results

def get_all_hqs_weather() -> Dict[str, Any]:
    """
    Obtiene el clima para todas las sedes predefinidas
    """
    hqs = ["roterdam", "houston", "sao_paulo", "shanghai", "beirut", "santiago", "puerto_cabello"]
    results = {}
    for hq in hqs:
        results[hq] = get_weather_by_hq(hq)
    return results

# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def test_weather():
    """Prueba las funciones de clima"""
    print("=" * 60)
    print("🌤️ DIAGNÓSTICO DE CLIMA")
    print("=" * 60)
    
    # 1. Probar Puerto Cabello
    print("\n📍 Puerto Cabello, Venezuela")
    result = get_weather(10.48, -68.01, "Puerto Cabello")
    if result and result["status"] == "success":
        print(f"✅ {result['temperature']}°C - {result['condition']}")
        print(f"   💨 Viento: {result['wind_speed']} km/h")
        print(f"   🕐 Hora: {result['timestamp']}")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # 2. Probar Santiago
    print("\n📍 Santiago, Chile")
    result = get_weather(-33.45, -70.66, "Santiago")
    if result and result["status"] == "success":
        print(f"✅ {result['temperature']}°C - {result['condition']}")
        print(f"   💨 Viento: {result['wind_speed']} km/h")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # 3. Probar Beirut
    print("\n📍 Beirut, Líbano")
    result = get_weather_by_hq("beirut")
    if result and result["status"] == "success":
        print(f"✅ {result['temperature']}°C - {result['condition']}")
        print(f"   💨 Viento: {result['wind_speed']} km/h")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # 4. Probar todas las sedes
    print("\n" + "=" * 60)
    print("📍 TODAS LAS SEDES")
    print("=" * 60)
    all_weather = get_all_hqs_weather()
    for hq, data in all_weather.items():
        if data and data["status"] == "success":
            print(f"   {hq}: {data['temperature']}°C - {data['condition']}")
        else:
            print(f"   {hq}: ❌ {data.get('message', 'Error')}")

if __name__ == "__main__":
    test_weather()
