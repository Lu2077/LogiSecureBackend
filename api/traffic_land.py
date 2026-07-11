# backend/api/traffic_land.py
"""
Land traffic API - OSRM/OpenStreetMap integration
Fixed: OSRM URL, response parsing, and error handling
"""

import time
import requests
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ============================================
# LOCAL CACHE
# ============================================

LAND_ROUTE_CACHE = {}
CACHE_TIMEOUT = 3600  # 1 hour

# ============================================
# ENTERPRISE SHIPMENTS DATABASE
# ============================================

ENTERPRISE_SHIPMENTS = {
    "MBL-MAERSK-2077": {
        "client": "Exportadora de Frutas Santiago (Chile)",
        "cargo_type": "Refrigerated Cherries Container",
        "tracking_type": "MARITIME_FEED",
        "has_active_gps": False,
        "start_coords": [4.4791, 51.9225],   # [lon, lat] Rotterdam
        "end_coords": [13.4050, 52.5200],    # [lon, lat] Berlin
        "departure_time": time.time() - 7200,
        "total_duration_seconds": 21600
    },
    "AWB-FEDEX-9942": {
        "client": "TechImport Houston LLC",
        "cargo_type": "Electronic Circuit Boards",
        "tracking_type": "AIR_FEED",
        "has_active_gps": True,
        "start_coords": [-95.3698, 29.7604],  # [lon, lat] Houston
        "end_coords": [-97.7431, 30.2672],    # [lon, lat] Austin
        "current_gps_ping": {"lat": 30.0120, "lng": -96.1140}
    },
    "BKG-SHANGHAI-04B": {
        "client": "Global Logistics Inc",
        "cargo_type": "Industrial Generators",
        "tracking_type": "LAND_INTERMODAL",
        "has_active_gps": False,
        "start_coords": [121.4737, 31.2304],  # [lon, lat] Shanghai
        "end_coords": [120.6195, 31.3001],    # [lon, lat] Suzhou
        "departure_time": time.time() - 1800,
        "total_duration_seconds": 5400
    },
    "BKG-LAND-04B": {
        "client": "EuroLogistics GmbH",
        "cargo_type": "Automotive Parts",
        "tracking_type": "LAND_INTERMODAL",
        "has_active_gps": False,
        "start_coords": [4.4791, 51.9225],    # [lon, lat] Rotterdam
        "end_coords": [6.0833, 50.7750],      # [lon, lat] Aachen
        "departure_time": time.time() - 900,
        "total_duration_seconds": 3600
    }
}


# ============================================
# OSRM ROUTE FETCHING (FIXED)
# ============================================

def get_route_geometry_osrm(start: List[float], end: List[float]) -> List[Dict[str, float]]:
    """
    Get route geometry from OSRM API.
    start/end: [longitude, latitude] format
    Returns: List of {"lat": x, "lng": y} for React Leaflet
    """
    # Create cache key
    cache_key = f"{start[0]}_{start[1]}_{end[0]}_{end[1]}"
    
    # Check cache
    if cache_key in LAND_ROUTE_CACHE:
        cache_time, waypoints = LAND_ROUTE_CACHE[cache_key]
        if (time.time() - cache_time) < CACHE_TIMEOUT:
            logger.info(f"📦 Cache hit for route: {cache_key}")
            return waypoints
    
    # Build OSRM URL - FIXED!
    # OSRM uses: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start[0]},{start[1]};{end[0]},{end[1]}"
    )
    
    logger.info(f"🗺️ Fetching route from OSRM: {url}")
    
    try:
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            routes = data.get("routes", [])
            
            if routes:
                geometry = routes[0].get("geometry", {})
                coordinates = geometry.get("coordinates", [])
                
                # Convert [lng, lat] to {"lat": x, "lng": y} for React
                waypoints = [{"lat": coord[1], "lng": coord[0]} for coord in coordinates]
                
                # Cache the result
                LAND_ROUTE_CACHE[cache_key] = (time.time(), waypoints)
                logger.info(f"✅ Route found with {len(waypoints)} points")
                return waypoints
            else:
                logger.warning("No routes found in OSRM response")
        else:
            logger.error(f"OSRM error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        logger.error("OSRM request timeout")
    except Exception as e:
        logger.error(f"OSRM error: {e}")
    
    # Fallback: Return straight line
    logger.warning("Using fallback straight-line route")
    return [
        {"lat": start[1], "lng": start[0]},
        {"lat": end[1], "lng": end[0]}
    ]


# ============================================
# LAND TRAFFIC FUNCTIONS
# ============================================

def get_land_traffic_by_hq(hq_name: str) -> Dict[str, Any]:
    """
    Get land traffic summary for a headquarters.
    Used by /api/dashboard/sync endpoint.
    """
    hq_name = hq_name.lower().strip()
    
    # Filter shipments by HQ (simple filter for now)
    hq_shipments = []
    for tracking_id, cargo in ENTERPRISE_SHIPMENTS.items():
        # Check if HQ matches start location or client
        if hq_name in str(cargo.get("client", "")).lower() or hq_name in str(cargo.get("start_coords", "")).lower():
            hq_shipments.append({
                "tracking_id": tracking_id,
                "client": cargo["client"],
                "cargo": cargo["cargo_type"],
                "tracking_type": cargo["tracking_type"],
                "has_active_gps": cargo["has_active_gps"],
            })
    
    # If no specific shipments found, return all
    if not hq_shipments:
        hq_shipments = [
            {
                "tracking_id": tid,
                "client": cargo["client"],
                "cargo": cargo["cargo_type"],
                "tracking_type": cargo["tracking_type"],
                "has_active_gps": cargo["has_active_gps"],
            }
            for tid, cargo in ENTERPRISE_SHIPMENTS.items()
        ]
    
    # Calculate statistics
    total = len(hq_shipments)
    with_gps = sum(1 for s in hq_shipments if s["has_active_gps"])
    
    return {
        "status": "success",
        "location": hq_name,
        "data": {
            "active_shipments": hq_shipments,
            "total_shipments": total,
            "shipments_with_gps": with_gps,
            "shipments_without_gps": total - with_gps
        }
    }


def get_asset_tracking_by_id(tracking_id: str) -> Dict[str, Any]:
    """
    Track a specific land asset by ID.
    Returns either live GPS or predictive location.
    """
    id_upper = tracking_id.upper().strip()
    
    if id_upper not in ENTERPRISE_SHIPMENTS:
        return {
            "status": "error",
            "message": f"Tracking ID '{tracking_id}' not found",
            "examples": list(ENTERPRISE_SHIPMENTS.keys())
        }
    
    cargo = ENTERPRISE_SHIPMENTS[id_upper]
    
    # ============================================
    # CASE 1: Live GPS Tracking (Green)
    # ============================================
    if cargo.get("has_active_gps", False):
        logger.info(f"🛰️ Live GPS tracking for: {id_upper}")
        return {
            "status": "success",
            "tracking_id": id_upper,
            "client": cargo["client"],
            "cargo": cargo["cargo_type"],
            "mode": "LIVE_GNSS_HARDWARE_STREAM",
            "display_color": "green",
            "telemetry": {
                "current_position": cargo["current_gps_ping"],
                "status_tags": "IN_TRANSIT_ON_TIME"
            }
        }
    
    # ============================================
    # CASE 2: Predictive Tracking (Amber/Yellow)
    # ============================================
    logger.info(f"🧠 Predictive tracking for: {id_upper}")
    
    # Get route
    waypoints = get_route_geometry_osrm(cargo["start_coords"], cargo["end_coords"])
    
    if not waypoints:
        return {
            "status": "error",
            "message": "Failed to calculate route. Please try again later."
        }
    
    # Calculate progress
    time_elapsed = time.time() - cargo["departure_time"]
    total_time = cargo["total_duration_seconds"]
    progress_ratio = min(max(time_elapsed / total_time, 0.0), 1.0)
    progress_percentage = round(progress_ratio * 100, 2)
    
    # Find current position on route
    total_points = len(waypoints)
    estimated_index = int(progress_ratio * (total_points - 1))
    estimated_position = waypoints[estimated_index]
    
    # Determine status
    if progress_ratio >= 1.0:
        status = "COMPLETED"
    else:
        status = "IN_TRANSIT_CALCULATED"
    
    return {
        "status": "success",
        "tracking_id": id_upper,
        "client": cargo["client"],
        "cargo": cargo["cargo_type"],
        "mode": "PREDICTIVE_DEAD_RECKONING_MODEL",
        "display_color": "amber",
        "telemetry": {
            "progress_percentage": progress_percentage,
            "current_position": estimated_position,
            "full_estimated_polyline": waypoints,
            "status_tags": status,
            "time_elapsed_hours": round(time_elapsed / 3600, 2),
            "time_remaining_hours": round((total_time - time_elapsed) / 3600, 2) if progress_ratio < 1.0 else 0
        }
    }


def get_route_optimization(
    origin: str,
    destination: str,
    shipment_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get optimized route between two cities.
    Useful for route planning.
    """
    # Simple implementation for now
    return {
        "status": "success",
        "origin": origin,
        "destination": destination,
        "route": {
            "distance": "250 km",
            "duration": "3.5 hours",
            "traffic_congestion": "medium",
            "status": "open"
        },
        "alternative_routes": [
            {
                "path": f"{origin} → {destination} (via alternate)",
                "distance": "280 km",
                "duration": "4 hours",
                "traffic_congestion": "low"
            }
        ]
    }


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚛 LAND TRAFFIC API TEST")
    print("=" * 60)
    
    # Test 1: Get all shipments
    print("\n📦 Test 1: Get land traffic summary")
    result = get_land_traffic_by_hq("rotterdam")
    print(f"   Status: {result['status']}")
    print(f"   Total shipments: {result['data']['total_shipments']}")
    print(f"   With GPS: {result['data']['shipments_with_gps']}")
    
    # Test 2: Track specific shipment
    print("\n📦 Test 2: Track shipment MBL-MAERSK-2077")
    result = get_asset_tracking_by_id("MBL-MAERSK-2077")
    print(f"   Status: {result['status']}")
    print(f"   Mode: {result['mode']}")
    print(f"   Progress: {result['telemetry']['progress_percentage']}%")
    print(f"   Position: {result['telemetry']['current_position']}")
    
    # Test 3: Track live GPS shipment
    print("\n📦 Test 3: Track live GPS AWB-FEDEX-9942")
    result = get_asset_tracking_by_id("AWB-FEDEX-9942")
    print(f"   Status: {result['status']}")
    print(f"   Mode: {result['mode']}")
    print(f"   GPS Position: {result['telemetry']['current_position']}")
    
    print("\n✅ Land Traffic API test complete!")