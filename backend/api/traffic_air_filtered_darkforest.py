import time
import requests
from config import get_settings

# Estructura para almacenar cachés dinámicos por zonas geográficas
# Evita mezclar datos si un usuario mira Europa y otro el Estrecho de Ormuz
REGIONAL_CACHES = {}
CACHE_DURATION = 20

def get_dark_forest_flights(lamin: float, lomin: float, lamax: float, lomax: float):
    current_time = time.time()
    
    # 1. Crear un identificador único para la zona consultada (Clave de región)
    region_key = f"{round(lamin, 1)}_{round(lomin, 1)}_{round(lamax, 1)}_{round(lomax, 1)}"
    
    # 2. Validar Escudo de Seguridad: Evitar consultas planetarias masivas
    # Si la diferencia de grados es muy grande, bloqueamos la petición para proteger el hardware
    if (lamax - lamin) > 15.0 or (lomax - lomin) > 15.0:
        print("🛡️ Dark Forest Shield: Viewport too large. Query rejected to save compute power.")
        return {"status": "zoom_closer", "message": "Please zoom in to reveal assets.", "states": []}

    # 3. Verificar si esta región específica tiene un caché válido en la RAM
    if region_key in REGIONAL_CACHES:
        cache_data = REGIONAL_CACHES[region_key]
        if (current_time - cache_data["timestamp"]) < CACHE_DURATION:
            print(f"⚡ Entregando {len(cache_data['data'])} aviones de la región [{region_key}] desde caché local.")
            return {"status": "success", "states": cache_data["data"]}

    # 4. Si no hay caché o expiró, hacemos la consulta en la nube
    print(f"📡 Solicitando datos reales a OpenSky para la zona: {region_key}")
    settings = get_settings()
    url = "https://opensky-network.org"
    
    params = {
        "lamin": lamin,
        "lomin": lomin,
        "lamax": lamax,
        "lomax": lomax
    }

    try:
        response = requests.get(
            url, 
            params=params,
            auth=(settings.OPENSKY_USERNAME, settings.OPENSKY_PASSWORD),
            timeout=8
        )
        
        if response.status_code == 200:
            flight_states = response.json().get("states", []) or []
            # Guardamos en la memoria RAM el resultado indexado por región y tiempo
            REGIONAL_CACHES[region_key] = {
                "timestamp": current_time,
                "data": flight_states
            }
            return {"status": "success", "states": flight_states}
        else:
            # Si la API falla (ej. error 429), devolvemos el caché viejo de esa región si existe
            old_data = REGIONAL_CACHES.get(region_key, {}).get("data", [])
            return {"status": "rate_limited", "states": old_data}
            
    except Exception as e:
        print(f"❌ Error de red en el Bosque Oscuro: {e}")
        return {"status": "error", "states": []}

