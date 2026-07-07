import time
import requests
from typing import Dict, Any
from datetime import datetime
import logging
from config import get_settings

logger = logging.getLogger(__name__)

AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.9225, "lon": 4.4791, "timezone": "Europe/Amsterdam"},
    "houston": {"lat": 29.7604, "lon": -95.3698, "timezone": "America/Chicago"},
    "sao_paulo": {"lat": -23.5505, "lon": -46.6333, "timezone": "America/Sao_Paulo"},
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "timezone": "Asia/Shanghai"}
    #If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map 
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

WEATHER_CACHE = {}
CACHE_DURATION = 600  # The weather is changing slowly; we're keeping the cache for 10 minutes.

def get_live_weather_by_hq(hq_name: str) -> Dict[str, Any]:
    current_time = time.time()
    hq_name_lower = hq_name.lower().strip()
    
    if hq_name_lower not in AVAILABLE_LOCATIONS:
        return {"status": "error", "message": "HQ not configured for weather telemetry."}
        
    hq = SEDES_DISPONIBLES[hq_name_lower]
    
    if hq_name_lower in WEATHER_CACHE:
        cache = WEATHER_CACHE[hq_name_lower]
        if (current_time - cache["timestamp"]) < CACHE_DURATION:
            logger.info(f"⚡ Serving cached weather telemetry for HQ [{hq_name_lower}]")
            return {"status": "success", "data": cache["data"], "cached": True}

    logger.info(f"📡 Requesting live meteorological data for HQ [{hq_name_lower}]")
    url = "https://open-meteo.com"
    params = {
        "latitude": hq["lat"],
        "longitude": hq["lon"],
        "current_weather": "true",
        "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m,visibility",
        "timezone": hq["timezone"]
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            raw_data = response.json()
            current = raw_data.get("current_weather", {})
            
            # Clasificación de riesgo ambiental para el Frontend
            # Códigos WMO >= 61 significan lluvia pesada, tormentas o nieve
            is_hazardous = current.get("weathercode", 0) >= 61
            
            processed_data = {
                "temperature": current.get("temperature"),
                "windspeed": current.get("windspeed"),
                "winddirection": current.get("winddirection"),
                "weather_code": current.get("weathercode"),
                "is_hazardous_for_transit": is_hazardous,
                "risk_level": "HIGH_ALERT" if is_hazardous and current.get("windspeed", 0) > 40 else "SAFE",
                "last_update": current.get("time")
            }
            
            WEATHER_CACHE[hq_name_lower] = {"timestamp": current_time, "data": processed_data}
            return {"status": "success", "data": processed_data, "cached": False}
    except Exception as e:
        logger.error(f"❌ Weather service connection failure: {e}")
        
    return {"status": "error", "message": "Weather telemetry unavailable."}
