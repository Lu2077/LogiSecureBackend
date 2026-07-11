# backend/ai_agents/router.py
"""
LogiSecure AI Router - Unified Tracking & Routing Engine
Handles all shipment tracking, route optimization, and agent workflows
"""

import time
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Query
from datetime import datetime
import logging

# ============================================
# Local Imports
# ============================================
from ai_agents.database import ENTERPRISE_SHIPMENTS, get_shipment
from api.traffic_air import get_flights_by_company_hq
from api.traffic_sea import get_vessels_by_company_hq_async, get_vessel_by_mmsi_async
from api.traffic_land import get_asset_tracking_by_id, get_route_optimization
from agents import LogiSecureAgents
from logger import logger

# ============================================
# ROUTER CLASS
# ============================================

class LogiSecureRouter:
    """
    Unified Router for all LogiSecure AI operations.
    Handles:
    1. Shipment Tracking (Air, Sea, Land)
    2. Route Optimization
    3. AI Agent Workflows
    4. Dashboard Data Aggregation
    """
    
    def __init__(self):
        """Initialize the router with agent system"""
        self.agents = LogiSecureAgents()
        logger.info("✅ Router initialized with AI agents")
    
    # ============================================
    # 1. SHIPMENT TRACKING
    # ============================================
    
    async def track_shipment(self, tracking_id: str) -> Dict[str, Any]:
        """
        Unified tracking endpoint.
        Handles AIR_LIVE, OCEAN_LIVE, and LAND_PREDICTIVE modes.
        """
        id_upper = tracking_id.upper().strip()
        
        # Check if shipment exists in database
        shipment = get_shipment(id_upper)
        if not shipment:
            return {
                "status": "error",
                "message": f"Tracking ID '{tracking_id}' not found",
                "available_ids": list(ENTERPRISE_SHIPMENTS.keys())
            }
        
        mode = shipment.get("mode")
        logger.info(f"🔍 Tracking {id_upper} - Mode: {mode}")
        
        # ============================================
        # CASE A: AIR_LIVE - OpenSky API
        # ============================================
        if mode == "AIR_LIVE":
            callsign = shipment.get("carrier_callsign")
            if not callsign:
                return {
                    "status": "error",
                    "message": f"No callsign found for {id_upper}"
                }
            
            # Query air traffic
            air_data = get_flights_by_company_hq("houston")
            flights = air_data.get("flights", [])
            
            # Find the flight with matching callsign
            for flight in flights:
                if flight.get("callsign", "").upper() == callsign.upper():
                    return {
                        "status": "success",
                        "tracking_id": id_upper,
                        "mode": "LIVE_GNSS_HARDWARE_STREAM",
                        "display_color": "green",
                        "metadata": shipment,
                        "telemetry": {
                            "current_position": {
                                "lat": flight.get("latitude"),
                                "lng": flight.get("longitude")
                            },
                            "altitude": flight.get("baro_altitude"),
                            "velocity": flight.get("velocity"),
                            "callsign": flight.get("callsign"),
                            "origin_country": flight.get("origin_country"),
                            "on_ground": flight.get("on_ground", False)
                        }
                    }
            
            # Flight not found
            return {
                "status": "warning",
                "tracking_id": id_upper,
                "mode": "AIR_FLEET_GATEWAY_PENDING",
                "display_color": "amber",
                "metadata": shipment,
                "message": "Flight not currently visible. Check back soon.",
                "telemetry": {
                    "estimated_position": {"lat": 29.7604, "lng": -95.3698}
                }
            }
        
        # ============================================
        # CASE B: OCEAN_LIVE - AISstream API
        # ============================================
        elif mode == "OCEAN_LIVE":
            mmsi = shipment.get("vessel_mmsi")
            if not mmsi:
                return {
                    "status": "error",
                    "message": f"No MMSI found for {id_upper}"
                }
            
            # Query maritime traffic
            try:
                sea_data = await get_vessels_by_company_hq_async("rotterdam")
                vessels = sea_data.get("data", {}).get("all_vessels", [])
                
                # Find vessel by MMSI
                for vessel in vessels:
                    if vessel.get("mmsi") == mmsi:
                        return {
                            "status": "success",
                            "tracking_id": id_upper,
                            "mode": "LIVE_AIS_MARITIME_TRACKING",
                            "display_color": "green",
                            "metadata": shipment,
                            "telemetry": {
                                "current_position": {
                                    "lat": vessel.get("lat"),
                                    "lng": vessel.get("lon")
                                },
                                "speed": vessel.get("speed"),
                                "course": vessel.get("course"),
                                "name": vessel.get("name"),
                                "country": vessel.get("country"),
                                "type_label": vessel.get("type_label"),
                                "timestamp": vessel.get("timestamp")
                            }
                        }
            except Exception as e:
                logger.error(f"Maritime tracking error: {e}")
            
            # Vessel not found
            return {
                "status": "warning",
                "tracking_id": id_upper,
                "mode": "PORT_ANCHORAGE_WAITING",
                "display_color": "amber",
                "metadata": shipment,
                "message": "Vessel not currently in monitored area.",
                "telemetry": {
                    "estimated_position": {"lat": 51.9225, "lng": 4.4791}
                }
            }
        
        # ============================================
        # CASE C: LAND_PREDICTIVE - OSRM + Dead Reckoning
        # ============================================
        elif mode == "LAND_PREDICTIVE":
            result = get_asset_tracking_by_id(id_upper)
            if result.get("status") == "success":
                result["metadata"] = shipment
            return result
        
        # ============================================
        # Unknown mode
        # ============================================
        else:
            return {
                "status": "error",
                "message": f"Unknown mode '{mode}' for {id_upper}"
            }
    
    # ============================================
    # 2. ROUTE OPTIMIZATION
    # ============================================
    
    def optimize_route(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
        avoid_tolls: bool = False
    ) -> Dict[str, Any]:
        """
        Optimize a route between two points.
        Uses OSRM for real road data.
        """
        logger.info(f"🗺️ Optimizing route: {origin} -> {destination}")
        
        result = get_route_optimization(origin, destination)
        
        if result.get("status") == "success":
            result["mode"] = mode
            result["avoid_tolls"] = avoid_tolls
            result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    # ============================================
    # 3. AI AGENT WORKFLOW
    # ============================================
    
    def run_agent_workflow(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the 5-step AI agent workflow.
        """
        logger.info("🧠 Running AI agent workflow")
        
        try:
            result = self.agents.run(incident_data)
            return {
                "status": "success",
                "workflow": "5-step complete",
                "analysis": result,
                "summary": self.agents.get_summary(result),
                "alerts": result.get("alerts", []),
                "affected_shipments": result.get("affected_shipments", []),
                "alternative_routes": result.get("alternative_routes", [])
            }
        except Exception as e:
            logger.error(f"Agent workflow failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ============================================
    # 4. DASHBOARD DATA
    # ============================================
    
    async def get_dashboard_data(self, hq: str = "rotterdam") -> Dict[str, Any]:
        """
        Aggregate all data for the dashboard.
        """
        logger.info(f"📊 Aggregating dashboard data for {hq}")
        
        # Get air traffic
        air_data = get_flights_by_company_hq(hq)
        
        # Get sea traffic
        try:
            sea_data = await get_vessels_by_company_hq_async(hq)
        except Exception as e:
            logger.error(f"Sea data error: {e}")
            sea_data = {"status": "error", "message": str(e)}
        
        # Get land traffic
        land_data = get_asset_tracking_by_id("BKG-LAND-04B")
        
        # Get all shipments
        shipments = []
        for tracking_id, data in ENTERPRISE_SHIPMENTS.items():
            shipments.append({
                "tracking_id": tracking_id,
                "mode": data.get("mode"),
                "cargo": data.get("cargo"),
                "client": data.get("client")
            })
        
        return {
            "status": "success",
            "location": hq,
            "timestamp": datetime.now().isoformat(),
            "air_traffic": {
                "total_flights": air_data.get("total_flights", 0),
                "flights": air_data.get("flights", [])
            },
            "maritime_traffic": {
                "total_vessels": sea_data.get("total_vessels", 0),
                "vessels": sea_data.get("data", {}).get("all_vessels", [])
            },
            "land_traffic": {
                "active_shipments": len(shipments),
                "shipments": shipments
            },
            "shipment_tracking": {
                "live_gps": sum(1 for s in shipments if s.get("mode") in ["AIR_LIVE", "OCEAN_LIVE"]),
                "predictive": sum(1 for s in shipments if s.get("mode") == "LAND_PREDICTIVE")
            }
        }


# ============================================
# SINGLETON INSTANCE
# ============================================

_router_instance = None

def get_router() -> LogiSecureRouter:
    """Get or create the router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LogiSecureRouter()
    return _router_instance


# ============================================
# TEST
# ============================================

async def test_router():
    """Test the router functionality"""
    print("=" * 60)
    print("🧪 TESTING LOGISECURE ROUTER")
    print("=" * 60)
    
    router = get_router()
    
    # Test 1: Track AIR shipment
    print("\n📦 Test 1: Track AWB-FEDEX-9942")
    result = await router.track_shipment("AWB-FEDEX-9942")
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Color: {result.get('display_color')}")
    
    # Test 2: Track MARITIME shipment
    print("\n📦 Test 2: Track MBL-MAERSK-2077")
    result = await router.track_shipment("MBL-MAERSK-2077")
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    
    # Test 3: Track LAND shipment
    print("\n📦 Test 3: Track BKG-LAND-04B")
    result = await router.track_shipment("BKG-LAND-04B")
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Progress: {result.get('telemetry', {}).get('progress_percentage', 'N/A')}%")
    
    # Test 4: Route optimization
    print("\n🗺️ Test 4: Optimize route Rotterdam -> Berlin")
    result = router.optimize_route("Rotterdam", "Berlin")
    print(f"  Status: {result.get('status')}")
    print(f"  Distance: {result.get('route', {}).get('distance')}")
    
    # Test 5: Agent workflow
    print("\n🧠 Test 5: Run agent workflow")
    result = router.run_agent_workflow({
        "type": "Port Strike",
        "location": "Rotterdam",
        "severity": "High",
        "description": "Dock workers strike"
    })
    print(f"  Status: {result.get('status')}")
    print(f"  Alerts: {len(result.get('alerts', []))}")
    
    print("\n✅ Router test complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_router())