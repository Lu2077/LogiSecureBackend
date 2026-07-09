# weather.py
import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Desactivar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# CONFIGURACIÓN DE APIS
# ============================================================================

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ============================================================================
# ZONAS HORARIAS POR SEDE ✅ AGREGADO
# ============================================================================

TIMEZONES = {
    "roterdam": "Europe/Amsterdam",
    "houston": "America/Chicago",
    "sao_paulo": "America/Sao_Paulo",
    "shanghai": "Asia/Shanghai",
    "santiago": "America/Santiago",
    "beirut": "Asia/Beirut",
    "custom": "UTC"
}

# ============================================================================
# COORDENADAS DE SEDES
# ============================================================================

AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791},
    "houston": {"lat": 29.7604, "lon": -95.3698},
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333},
    "shanghai": {"lat": 31.2304, "lon": 121.4737},
    "santiago": {"lat": -33.4489, "lon": -70.6693},
    "beirut": {"lat": 33.8938, "lon": 35.5018},
    "custom": {"lat": 0.0, "lon": 0.0}
}

# ============================================================================
# CÓDIGOS DE CLIMA OPEN-METEO
# ============================================================================

WEATHER_CODES = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    56: "Llovizna congelante ligera",
    57: "Llovizna congelante intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    66: "Lluvia congelante ligera",
    67: "Lluvia congelante intensa",
    71: "Nieve ligera",
    73: "Nieve moderada",
    75: "Nieve intensa",
    77: "Granizo",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos intensos",
    85: "Chubascos de nieve ligeros",
    86: "Chubascos de nieve intensos",
    95: "Tormenta eléctrica",
    96: "Tormenta con granizo ligero",
    99: "Tormenta con granizo intenso"
}

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def get_weather(lat: float, lon: float, location_name: str = "Ubicación") -> Optional[Dict[str, Any]]:
    """
    Obtiene el clima actual de Open-Meteo para una ubicación
    con la zona horaria correcta.
    """
    # Obtener zona horaria para la ubicación
    timezone = TIMEZONES.get(location_name.lower(), "UTC")
    
    # 🔧 IMPORTANTE: Especificar timezone en la petición
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": timezone,  # ← CLAVE: zona horaria correcta
        "forecast_days": 1
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
            timestamp = current.get("time")  # ← Ahora en la zona horaria correcta
            is_day = current.get("is_day")
            
            # Traducir código de clima
            condition = WEATHER_CODES.get(weather_code, f"Código {weather_code}")
            
            return {
                "status": "success",
                "location": location_name,
                "lat": lat,
                "lon": lon,
                "timestamp": timestamp,  # ← Hora local correcta
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
                "timezone": timezone  # ← Mostrar zona horaria usada
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
    Obtiene el clima para una sede específica con zona horaria correcta.
    """
    hq = hq_name.lower().strip()
    if hq not in AVAILABLE_LOCATIONS:
        return {
            "status": "error",
            "message": f"Sede '{hq_name}' no encontrada",
            "available_locations": list(AVAILABLE_LOCATIONS.keys())
        }
    
    coord = AVAILABLE_LOCATIONS[hq]
    return get_weather(coord["lat"], coord["lon"], hq)

# ============================================================================
# ALIAS PARA COMPATIBILIDAD CON main.py
# ============================================================================

get_live_weather_by_hq = get_weather_by_hq

# ============================================================================
# FUNCIÓN DE PRUEBA
# ============================================================================

def test_weather():
    """Prueba las funciones de clima"""
    print("=" * 60)
    print("🌤️ DIAGNÓSTICO DE CLIMA")
    print("=" * 60)
    
    # Probar Santiago
    print("\n📍 Santiago, Chile")
    result = get_weather_by_hq("santiago")
    if result and result["status"] == "success":
        print(f"✅ {result['temperature']}°C - {result['condition']}")
        print(f"   💨 Viento: {result['wind_speed']} km/h")
        print(f"   🕐 Hora local: {result['timestamp']}")
        print(f"   🗺️ Zona horaria: {result['timezone']}")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")
    
    # Probar São Paulo
    print("\n📍 São Paulo, Brasil")
    result = get_weather_by_hq("sao_paulo")
    if result and result["status"] == "success":
        print(f"✅ {result['temperature']}°C - {result['condition']}")
        print(f"   💨 Viento: {result['wind_speed']} km/h")
        print(f"   🕐 Hora local: {result['timestamp']}")
        print(f"   🗺️ Zona horaria: {result['timezone']}")
    else:
        print(f"❌ Error: {result.get('message', 'Desconocido')}")

if __name__ == "__main__":
    test_weather()
