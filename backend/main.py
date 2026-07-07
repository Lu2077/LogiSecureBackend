from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from config import get_settings, Settings
import asyncio
from functools import lru_cache
import time
from datetime import datetime, timedelta

# Importamos tus lógicas de captura de datos reales
from api.weather import get_live_weather
from api.traffic_land import simulate_truck_route
from api.traffic_air import get_flights_by_company_hq

app = FastAPI(
    title="LogiSecure AI - Core Enterprise API",
    description="Dynamic backend for managing global, multi-site assets"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache configuration
CACHE_TTL = 60  # seconds
flight_cache = {}

def get_cached_flights(hq: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Get cached flight data for a HQ with TTL"""
    cache_key = f"flights_{hq}"
    current_time = time.time()
    
    if not force_refresh and cache_key in flight_cache:
        cached_data, timestamp = flight_cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            return cached_data
    
    # Fetch fresh data
    result = get_flights_by_company_hq(hq)
    flight_cache[cache_key] = (result, current_time)
    return result

def validate_icao24(icao24: str) -> bool:
    """Validate ICAO24 format (hexadecimal, 6 characters)"""
    if not icao24 or len(icao24) != 6:
        return False
    try:
        int(icao24, 16)  # Try to parse as hexadecimal
        return True
    except ValueError:
        return False

def sanitize_hq_name(hq: str) -> str:
    """Sanitize and normalize HQ names"""
    return hq.lower().strip().replace(" ", "_")

@app.get("/")
def health_check():
    """Verifica si el servidor local de LogiSecure está en línea."""
    return {"status": "online", "system": "LogiSecure AI Core", "version": "1.0.0"}

# 🌎 1. ENDPOINT MULTI-SEDE: The user can select multiple ports or hubs at once.
@app.get("/api/traffic/air/hqs")
async def get_multi_hq_air_traffic(
    hqs: List[str] = Query(["roterdam"], description="List of logistics hubs activated on the map"),
    force_refresh: bool = Query(False, description="Force data update")
):
    """
    Allows the frontend to send multiple locations simultaneously (e.g., ?hqs=roterdam&hqs=sao_paulo).
    The backend consolidates and cleans the actual aircraft data from all selected locations into a single JSON object.
    """
    consolidated_data = {
        "couriers": [],
        "heavy_cargo": [],
        "all_flights": [],
        "total_flights": 0,
        "last_update": datetime.utcnow().isoformat()
    }
    
    active_hqs = [sanitize_hq_name(hq) for hq in hqs]
    errors = []
    
    for hq in active_hqs:
        try:
            # Use cached data with optional refresh
            hq_result = get_cached_flights(hq, force_refresh)
            
            if hq_result.get("status") == "success":
                data = hq_result.get("data", {})
                
                # Handle missing data gracefully
                couriers = data.get("couriers", [])
                heavy_cargo = data.get("heavy_cargo", [])
                all_flights = data.get("all_flights", [])
                
                consolidated_data["couriers"].extend(couriers)
                consolidated_data["heavy_cargo"].extend(heavy_cargo)
                consolidated_data["all_flights"].extend(all_flights)
                consolidated_data["total_flights"] += len(all_flights)
            else:
                errors.append({
                    "hq": hq,
                    "error": hq_result.get("message", "Unknown error")
                })
        except Exception as e:
            errors.append({
                "hq": hq,
                "error": str(e)
            })
    
    # Prepare response
    response = {
        "status": "success" if not errors else "partial_success",
        "active_hqs": active_hqs,
        "data": consolidated_data
    }
    
    if errors:
        response["errors"] = errors
    
    return response

# ✈️ 2. INDIVIDUAL FLIGHT ENDPOINT: Surgical consultation by asset ID
@app.get("/api/traffic/air/flight/{icao24}")
async def get_individual_flight(
    icao24: str, 
    active_hqs: List[str] = Query(["roterdam"], description="Locations where the asset can be found"),
    force_refresh: bool = Query(False, description="Force data update")
):
    """
    When the user clicks on a specific aircraft on the React map,
    this endpoint looks up its unique ID (icao24) in the active stations cache
    and instantly retrieves its telemetry and history.
    """
    # Validate ICAO24 format
    if not validate_icao24(icao24):
        raise HTTPException(
            status_code=400, 
            detail="Invalid ICAO24 format. Must be 6 hexadecimal characters."
        )
    
    icao24 = icao24.lower().strip()
    active_hqs = [sanitize_hq_name(hq) for hq in active_hqs]
    errors = []
    
    for hq in active_hqs:
        try:
            hq_result = get_cached_flights(hq, force_refresh)
            
            if hq_result.get("status") == "success":
                flights = hq_result.get("data", {}).get("all_flights", [])
                
                # Search for the flight
                for flight in flights:
                    # Validate that the flight data structure is as expected
                    if len(flight) >= 11 and flight[0] == icao24:
                        return {
                            "status": "success",
                            "asset_id": icao24,
                            "callsign": flight[1].strip() if flight[1] else "UNKNOWN",
                            "origin_country": flight[2] or "UNKNOWN",
                            "lng": flight[5],
                            "lat": flight[6],
                            "altitude": flight[7],
                            "velocity": flight[9],
                            "heading": flight[10],
                            "found_in_hq": hq,
                            "timestamp": datetime.utcnow().isoformat()
                        }
            else:
                errors.append(f"HQ {hq}: {hq_result.get('message', 'Unknown error')}")
        except Exception as e:
            errors.append(f"HQ {hq}: {str(e)}")
    
    # If we get here, flight wasn't found
    error_message = f"Active asset {icao24} not found in selected log zones"
    if errors:
        error_message += f" (Errors: {', '.join(errors)})"
    
    raise HTTPException(status_code=404, detail=error_message)

# 🚛 GROUND TRAFFIC ENDPOINT (GPS simulator on real roads)
@app.get("/api/traffic/land")
async def get_land_traffic(
    start_lat: float, 
    start_lon: float, 
    end_lat: float, 
    end_lon: float
):
    """Returns the GPS points so the truck moves realistically along the streets in React."""
    # Validate coordinates
    if not (-90 <= start_lat <= 90) or not (-90 <= end_lat <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude values")
    if not (-180 <= start_lon <= 180) or not (-180 <= end_lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude values")
    
    try:
        route_points = simulate_truck_route(start_lat, start_lon, end_lat, end_lon)
        return {
            "status": "success", 
            "coordinates": route_points,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating route: {str(e)}")

# 🌍 Global Port Weather Endpoint
@app.get("/api/weather")
async def get_weather(lat: float, lon: float):
    """Check real-time weather alerts from Open-Meteo."""
    # Validate coordinates
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude value")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude value")
    
    try:
        weather_data = get_live_weather(lat, lon)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")

# 🗑️ Cache management endpoint (optional)
@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the flight data cache"""
    flight_cache.clear()
    return {"status": "success", "message": "Cache cleared"}

# 📊 Statistics endpoint (optional)
@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "status": "success",
        "cache_size": len(flight_cache),
        "cache_items": list(flight_cache.keys()),
        "uptime": time.time() - app.start_time if hasattr(app, 'start_time') else 0
    }

# Initialize start time
app.start_time = time.time()

