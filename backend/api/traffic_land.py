#OSMR/OpenStreetMap
import time
import requests
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# LOCAL CACHE MEMORY TO STORE OSRM GEOGRAPHIC COORDINATES
LAND_ROUTE_CACHE = {}

# 📦 CONFIDENTIAL INTERNAL ERP / TMS DATABASE (Local Data Sovereignty)
# Indexed by Real Industry Identifiers: MBL, AWB and Booking IDs
ENTERPRISE_SHIPMENTS = {
    "MBL-MAERSK-2077": {
        "client": "Exportadora de Frutas Santiago (Chile)",
        "cargo_type": "Refrigerated Cherries Container",
        "tracking_type": "MARITIME_FEED",
        "has_active_gps": False,  # SCENARIO: No GPS (Uses Predictive Display)
        "start_coords": [4.4791, 51.9225],  # Port of Rotterdam (Origin)
        "end_coords": [13.4050, 52.5200],   # Berlin Distribution Hub (Destination)
        "departure_time": time.time() - 7200, # Departed exactly 2 hours ago (7200 seconds)
        "total_duration_seconds": 21600       # The complete journey takes 6 hours (OSRM Calculation)
    },
    "AWB-FEDEX-9942": {
        "client": "TechImport Houston LLC",
        "cargo_type": "Pallets of Electronic Circuit Boards (Hazardous Class 9)",
        "tracking_type": "AIR_FEED",
        "has_active_gps": True,   # SCENARIO: Active Satellite (Direct GNSS)
        "start_coords": [-95.3698, 29.7604], # Houston Hub
        "end_coords": [-97.7431, 30.2672],  # Austin Assembly Plant
        "current_gps_ping": {"lat": 30.0120, "lng": -96.1140} # Live satellite coordinate emission
    },
    "BKG-SHANGHAI-04B": {
        "client": "Global Logistics Global Inc",
        "cargo_type": "Industrial Electric Power Generators",
        "tracking_type": "LAND_INTERMODAL",
        "has_active_gps": False,  # SCENARIO: No GPS (Uses Predictive Display)
        "start_coords": [121.4737, 31.2304], # Port of Shanghai
        "end_coords": [120.6195, 31.3001],  # Suzhou Industrial Park
        "departure_time": time.time() - 1800, # Departed 30 minutes ago (1800 seconds)
        "total_duration_seconds": 5400        # The total journey takes 1.5 hours
    }
}

def get_route_geometry_osrm(start: List[float], end: List[float]) -> List[Dict[str, float]]:
    """Queries the OSRM API to get the exact real road line"""
    cache_key = f"{start[0]}_{start[1]}_{end[0]}_{end[1]}"
    if cache_key in LAND_ROUTE_CACHE:
        return LAND_ROUTE_CACHE[cache_key]
        
    url = f"http://project-osrm.org{start[0]},{start[1]};{end[0],{end[1]}}"
    try:
        res = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=5)
        if res.status_code == 200:
            geometry = res.json()["routes"]["geometry"]["coordinates"]
            # Convert OSRM's [Lng, Lat] to the standard [Lat, Lng] format required by React Leaflet
            waypoints = [{"lat": pt, "lng": pt} for pt in geometry]
            LAND_ROUTE_CACHE[cache_key] = waypoints
            return waypoints
    except Exception as e:
        logger.error(f"❌ OSRM Geometry tracking compilation failure: {e}")
    return []

def get_land_traffic_by_hq(hq_name: str) -> Dict[str, Any]:
    """
    Dashboard layer: summarizes the land/intermodal shipments registered in the
    local TMS so the /api/dashboard/sync master endpoint can render them.
    Detailed live/predictive telemetry stays in get_asset_tracking_by_id().
    """
    shipments = [
        {
            "tracking_id": tracking_id,
            "client": cargo["client"],
            "cargo": cargo["cargo_type"],
            "tracking_type": cargo["tracking_type"],
            "has_active_gps": cargo["has_active_gps"],
        }
        for tracking_id, cargo in ENTERPRISE_SHIPMENTS.items()
    ]
    return {
        "status": "success",
        "location": hq_name.lower().strip(),
        "data": {"active_shipments": shipments, "total_shipments": len(shipments)},
    }

def get_asset_tracking_by_id(tracking_id: str) -> Dict[str, Any]:
    """
    Core TMS Controller: Resolves the CEO's query by searching for 
    MBL, AWB or Booking ID, deciding whether to show real or predictive telemetry.
    """
    id_upper = tracking_id.upper().strip()
    
    if id_upper not in ENTERPRISE_SHIPMENTS:
        return {
            "status": "error", 
            "message": f"Tracking ID '{tracking_id}' not found in corporate ERP logs.",
            "examples_available": list(ENTERPRISE_SHIPMENTS.keys())
        }
        
    cargo = ENTERPRISE_SHIPMENTS[id_upper]
    
    # 🟢 CASE 1: THE ASSET HAS GPS / GNSS HARDWARE TRANSMITTING LIVE
    if cargo["has_active_gps"]:
        logger.info(f"🛰️ GNSS Satellite Link Active for tracking payload: {id_upper}")
        return {
            "status": "success",
            "tracking_id": id_upper,
            "client": cargo["client"],
            "cargo": cargo["cargo_type"],
            "mode": "LIVE_GNSS_HARDWARE_STREAM",
            "display_color": "green", # Direct instruction for the Frontend to paint it green
            "telemetry": {
                "current_position": cargo["current_gps_ping"],
                "status_tags": "IN_TRANSIT_ON_TIME"
            }
        }
        
    # 🟠 CASE 2: THE ASSET HAS NO GPS (PREDICTIVE SOFTWARE DISPLAY / DEAD RECKONING)
    else:
        logger.info(f"🧠 Initiating local predictive path simulation for blind tracking payload: {id_upper}")
        
        # 1. Fetch the real road path mapped by OSRM
        waypoints = get_route_geometry_osrm(cargo["start_coords"], cargo["end_coords"])
        
        if not waypoints:
            return {"status": "error", "message": "Failed to calculate physical route geography."}
            
        # 2. Predictive Display Mathematical Logic
        time_elapsed = time.time() - cargo["departure_time"]
        total_time = cargo["total_duration_seconds"]
        
        # Calculate the progress percentage of the journey (Strictly clamped between 0.0 and 1.0)
        progress_ratio = min(max(time_elapsed / total_time, 0.0), 1.0)
        progress_percentage = round(progress_ratio * 100, 2)
        
        # Find which index of the coordinate list corresponds to the current time progress
        total_coordinates_points = len(waypoints)
        estimated_index = int(progress_ratio * (total_coordinates_points - 1))
        estimated_position = waypoints[estimated_index]
        
        return {
            "status": "success",
            "tracking_id": id_upper,
            "client": cargo["client"],
            "cargo": cargo["cargo_type"],
            "mode": "PREDICTIVE_DEAD_RECKONING_MODEL",
            "display_color": "amber", # Instruction for React to paint it yellow/amber
            "telemetry": {
                "progress_percentage": progress_percentage,
                "current_position": estimated_position, # The Frontend places the icon here
                "full_estimated_polyline": waypoints,  # React draws the complete estimated road
                "status_tags": "COMPLETED" if progress_ratio >= 1.0 else "IN_TRANSIT_CALCULATED"
            }
        }


