"""
LogiSecure - Sistema de Alertas Logísticas Multi-Fuente
Versión para Hackathon - Día 1/3
"""

import time
import requests
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

CACHE_DURATION = 300  # 5 minutos
INCIDENTS_CACHE = {}

# ----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE INFRAESTRUCTURA CRÍTICA (Prioridad Alta)
# ----------------------------------------------------------------------------

CRITICAL_ASSETS = {
    # Puertos Top 10 Mundiales (por volumen de carga)
    "shanghai_port": {"lat": 31.23, "lon": 121.47, "type": "port", "tier": 1},
    "singapore_port": {"lat": 1.29, "lon": 103.86, "type": "port", "tier": 1},
    "rotterdam_port": {"lat": 51.92, "lon": 4.47, "type": "port", "tier": 1},
    "ningbo_port": {"lat": 29.86, "lon": 121.80, "type": "port", "tier": 1},
    "guangzhou_port": {"lat": 23.10, "lon": 113.25, "type": "port", "tier": 1},
    "qingdao_port": {"lat": 36.07, "lon": 120.30, "type": "port", "tier": 1},
    "busan_port": {"lat": 35.10, "lon": 129.03, "type": "port", "tier": 1},
    "hong_kong_port": {"lat": 22.31, "lon": 114.17, "type": "port", "tier": 1},
    "tianjin_port": {"lat": 38.98, "lon": 117.72, "type": "port", "tier": 1},
    "jebel_ali": {"lat": 25.00, "lon": 55.06, "type": "port", "tier": 1},
    
    # Aeropuertos Top Carga
    "memphis": {"lat": 35.04, "lon": -89.98, "type": "airport", "tier": 1},
    "hong_kong_airport": {"lat": 22.31, "lon": 113.91, "type": "airport", "tier": 1},
    "shanghai_pudong": {"lat": 31.14, "lon": 121.80, "type": "airport", "tier": 1},
    "anchorage": {"lat": 61.17, "lon": -149.99, "type": "airport", "tier": 1},
    "dubai_airport": {"lat": 25.25, "lon": 55.36, "type": "airport", "tier": 1},
    "heathrow": {"lat": 51.47, "lon": -0.45, "type": "airport", "tier": 1},
    "schiphol": {"lat": 52.31, "lon": 4.76, "type": "airport", "tier": 1},
    "frankfurt": {"lat": 50.03, "lon": 8.56, "type": "airport", "tier": 1},
    "cdg_paris": {"lat": 49.01, "lon": 2.55, "type": "airport", "tier": 1},
    "incheon": {"lat": 37.46, "lon": 126.45, "type": "airport", "tier": 1},
    
    # Estrechos y Canales (Puntos de Estrangulamiento)
    "strait_hormuz": {"lat": 26.57, "lon": 56.45, "type": "chokepoint", "tier": 1},
    "suez_canal": {"lat": 30.00, "lon": 32.50, "type": "chokepoint", "tier": 1},
    "bab_el_mandeb": {"lat": 13.00, "lon": 44.00, "type": "chokepoint", "tier": 1},
    "malacca_strait": {"lat": 1.50, "lon": 102.50, "type": "chokepoint", "tier": 1},
    "panama_canal": {"lat": 9.00, "lon": -79.50, "type": "chokepoint", "tier": 1},
    "bosphorus": {"lat": 41.10, "lon": 29.05, "type": "chokepoint", "tier": 1},
}

# ----------------------------------------------------------------------------
# 2. SISTEMA DE PUNTUACIÓN DE RIESGO
# ----------------------------------------------------------------------------

class RiskScorer:
    """
    Calcula el riesgo real basado en múltiples factores
    """
    weights = {
        "tier_1_asset": 40,      # Puerto/aeropuerto top 10
        "tier_2_asset": 25,      # Puerto/aeropuerto secundario
        "chokepoint": 50,        # Estrecho/canal
        "military_conflict": 35,  # Guerra activa
        "terrorism": 30,         # Ataque terrorista
        "natural_disaster": 25,  # Huracán, terremoto
        "political_instability": 15,  # Protestas, golpes
        "media_confidence": 10,  # Reuters/BBC = 10, Blog = 3
        "proximity": 5,          # Cerca de sede del usuario
    }
    
    def score_event(self, event: Dict[str, Any], user_hq: Dict[str, float]) -> int:
        score = 0
        
        # 1. Impacto en infraestructura crítica
        for asset_name, asset_info in CRITICAL_ASSETS.items():
            if asset_name in event.get("text", "").lower():
                if asset_info["tier"] == 1:
                    score += self.weights["tier_1_asset"]
                else:
                    score += self.weights["tier_2_asset"]
                if asset_info["type"] == "chokepoint":
                    score += self.weights["chokepoint"]
        
        # 2. Tipo de evento
        text = event.get("text", "").lower()
        if any(k in text for k in ["attack", "missile", "strike", "war", "invasion"]):
            score += self.weights["military_conflict"]
        if any(k in text for k in ["terror", "bomb", "explosion"]):
            score += self.weights["terrorism"]
        if any(k in text for k in ["hurricane", "earthquake", "flood", "tsunami"]):
            score += self.weights["natural_disaster"]
        if any(k in text for k in ["protest", "riot", "coup", "unrest"]):
            score += self.weights["political_instability"]
        
        # 3. Confianza de la fuente
        source = event.get("source", "").lower()
        if source in ["reuters", "bbc", "ap", "afp"]:
            score += self.weights["media_confidence"]
        
        # 4. Proximidad al usuario
        if user_hq:
            lat_diff = abs(event.get("lat", 0) - user_hq.get("lat", 0))
            lon_diff = abs(event.get("lon", 0) - user_hq.get("lon", 0))
            if lat_diff < 5 and lon_diff < 5:
                score += self.weights["proximity"]
        
        return min(score, 100)  # Cap en 100

# ============================================================================
# 3. CAPA DE DATOS - MÚLTIPLES FUENTES
# ============================================================================

class DataFetcher:
    """
    Obtiene datos de múltiples APIs y los unifica
    """
    
    def __init__(self):
        self.sources = {
            "newsdata": {
                "url": "https://newsdata.io/api/1/latest",
                "api_key": "pub_ac540cfd003d484fbb9f4fd2a1e69aef",
                "weight": 0.6
            },
            "opensky": {
                "url": "https://opensky-network.org/api/states/all",
                "api_key": None,
                "weight": 0.2
            },
            "openmeteo": {
                "url": "https://api.open-meteo.com/v1/forecast",
                "api_key": None,
                "weight": 0.2
            }
        }
    
    def fetch_news(self, countries: str) -> List[Dict[str, Any]]:
        """Obtiene noticias relevantes"""
        events = []
        try:
            params = {
                "apikey": self.sources["newsdata"]["api_key"],
                "country": countries,
                "language": "en",
                "category": "breaking,politics,world"
            }
            resp = requests.get(self.sources["newsdata"]["url"], params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for article in data.get("results", [])[:30]:
                    events.append({
                        "source": "newsdata",
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "text": article.get("title", "") + " " + article.get("description", ""),
                        "published": article.get("pubDate", ""),
                        "url": article.get("link", ""),
                        "country": (article.get("country") or [""])[0] or ""
                    })
        except Exception as e:
            logger.error(f"NewsData error: {e}")
        return events
    
    def fetch_flights(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Obtiene vuelos cerca de coordenadas"""
        # TODO: Implementar OpenSky
        return []
    
    def fetch_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Obtiene clima actual"""
        # TODO: Implementar Open-Meteo
        return {}

# ============================================================================
# 4. MOTOR DE ALERTAS - UNIFICA TODO
# ============================================================================

class AlertEngine:
    """
    Combina datos de múltiples fuentes y genera alertas priorizadas
    """
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.scorer = RiskScorer()
    
    def get_alerts(self, hq_name: str, lat: float = None, lon: float = None) -> Dict[str, Any]:
        """
        Obtiene alertas para una sede o coordenadas
        """
        cache_key = f"alerts_{hq_name}_{lat}_{lon}"
        if cache_key in INCIDENTS_CACHE:
            cache = INCIDENTS_CACHE[cache_key]
            if (time.time() - cache["timestamp"]) < CACHE_DURATION:
                return cache["data"]
        
        # 1. Configurar HQ
        hq_locations = {
            "roterdam": {"lat": 51.92, "lon": 4.47, "range": 5.0, "countries": "nl,be,de"},
            "shanghai": {"lat": 31.23, "lon": 121.47, "range": 4.0, "countries": "cn"},
            "beirut": {"lat": 33.89, "lon": 35.50, "range": 4.0, "countries": "lb,il,ps,sy,jo"},
        }
        
        if hq_name and hq_name in hq_locations:
            hq = hq_locations[hq_name]
            countries = hq["countries"]
            user_lat, user_lon = hq["lat"], hq["lon"]
        elif lat and lon:
            hq = {"lat": lat, "lon": lon, "range": 3.0}
            countries = "us,gb,fr,de"  # Default
            user_lat, user_lon = lat, lon
        else:
            return {"status": "error", "message": "Se necesita HQ o coordenadas"}
        
        # 2. Obtener datos de todas las fuentes
        logger.info(f"🔍 Buscando alertas para {hq_name or f'{lat},{lon}'}")
        
        # 2a. Noticias
        news_events = self.fetcher.fetch_news(countries)
        logger.info(f"📰 {len(news_events)} noticias procesadas")
        
        # 3. Procesar y puntuar eventos
        scored_events = []
        for event in news_events:
            # Geolocalizar básica
            location = self._geolocate(event)
            if location["type"] == "unknown":
                continue
            
            # Calcular score
            event["lat"] = location["lat"]
            event["lon"] = location["lon"]
            event["infrastructure"] = location["matched"]
            event["infrastructure_type"] = location["type"]
            
            score = self.scorer.score_event(event, hq)
            event["risk_score"] = score
            
            if score >= 30:  # Solo eventos con score significativo
                scored_events.append(event)
        
        # 4. Ordenar por score (mayor riesgo primero)
        scored_events.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # 5. Construir respuesta
        response = {
            "status": "success",
            "location": {"name": hq_name or "custom", "lat": user_lat, "lon": user_lon},
            "summary": {
                "total_alerts": len(scored_events),
                "critical": sum(1 for e in scored_events if e["risk_score"] >= 70),
                "warning": sum(1 for e in scored_events if 40 <= e["risk_score"] < 70),
                "info": sum(1 for e in scored_events if 30 <= e["risk_score"] < 40),
                "top_threat": scored_events[0]["title"] if scored_events else None,
                "updated": datetime.now().isoformat()
            },
            "events": scored_events[:10],  # Top 10
            "metadata": {
                "sources_used": ["newsdata"],
                "total_scored": len(scored_events),
                "threshold": 30
            }
        }
        
        # Cache
        INCIDENTS_CACHE[cache_key] = {"timestamp": time.time(), "data": response}
        return response
    
    def _geolocate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Geolocaliza un evento buscando infraestructura crítica mencionada
        """
        text = event.get("text", "").lower()
        
        # 1. Buscar en infraestructura crítica
        for name, info in CRITICAL_ASSETS.items():
            if name.replace("_", " ") in text or name in text:
                return {
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "matched": name,
                    "type": info["type"],
                    "confidence": "high"
                }
        
        # 2. Buscar países mencionados
        country_map = {
            "ukraine": [49.99, 36.23], "russia": [55.75, 37.62],
            "lebanon": [33.89, 35.50], "syria": [33.51, 36.29],
            "israel": [31.05, 34.85], "palestine": [31.95, 35.23],
            "china": [31.23, 121.47], "brazil": [-14.24, -51.93],
            "united states": [37.09, -95.71], "iran": [32.43, 53.69]
        }
        
        for country, coords in country_map.items():
            if country in text:
                return {
                    "lat": coords[0],
                    "lon": coords[1],
                    "matched": country,
                    "type": "country",
                    "confidence": "medium"
                }
        
        return {"lat": 0, "lon": 0, "matched": "unknown", "type": "unknown", "confidence": "low"}

# ============================================================================
# 5. INTERFAZ PARA FRONTEND (SIMPLE)
# ============================================================================

engine = AlertEngine()

def get_incidents_by_hq(hq_name: str) -> Dict[str, Any]:
    """Endpoint para sedes predefinidas"""
    return engine.get_alerts(hq_name)

def get_incidents_by_coords(lat: float, lon: float, radius: float = 3.0) -> Dict[str, Any]:
    """Endpoint para coordenadas personalizadas"""
    return engine.get_alerts(None, lat, lon)

# ============================================================================
# 6. PRUEBA
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚢 LOGISECURE - SISTEMA DE ALERTAS LOGÍSTICAS v2.0")
    print("🏗️ Multi-fuente | Puntuación de Riesgo | Infraestructura Crítica")
    print("=" * 60)
    
    # Prueba con Rotterdam
    print("\n📍 ROTTERDAM:")
    result = get_incidents_by_hq("roterdam")
    print(json.dumps(result, indent=2))
    
    # Prueba con Shanghai
    print("\n📍 SHANGHAI:")
    result = get_incidents_by_hq("shanghai")
    print(json.dumps(result, indent=2))
    
    # Prueba con Beirut
    print("\n📍 BEIRUT:")
    result = get_incidents_by_hq("beirut")
    print(json.dumps(result, indent=2))
