#Using gdelt/un.gdas

import time
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

INCIDENTS_CACHE = {}
CACHE_DURATION = 300  # Keep global alerts for 5 minutes

AVAILABLE_LOCATIONS = {
    "roterdam": {"lat": 51.92, "lon": 4.47, "range": 5.0},
    "houston": {"lat": 29.76, "lon": -95.36, "range": 6.0},
    "sao_paulo": {"lat": -23.55, "lon": -46.63, "range": 5.0},
    "shanghai": {"lat": 31.23, "lon": 121.47, "range": 4.0}
    # If the user wants to try another coordinate in the demo || React sends "custom" along with the Lat/Lon marked by the user when clicking on the map 
    "custom": {"lat": 0.0, "lon": 0.0, "range": 2.0, "type": "Custom Enterprise Node"}
}

def fetch_global_crisis_feed() -> List[Dict[str, Any]]:
    """Captures real critical alerts from the UN API (GDACS)"""
    url = "https://gdacs.org"
    incidents = []
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Parse the UN XML feed
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else "Unknown Crisis"
                description = item.find("description").text if item.find("description") is not None else ""
                
                # GDACS includes native geolocation tags in georss format
                lat_element = item.find("{http://georss.org}point")
                
                if lat_element is not None and lat_element.text:
                    coords = lat_element.text.strip().split()
                    if len(coords) == 2:
                        incidents.append({
                            "source": "UN_GDACS",
                            "event": title,
                            "details": description[:200],
                            "lat": float(coords[0]),
                            "lng": float(coords[1]),
                            "severity": "CRITICAL" if "Red" in title or "High" in description else "WARNING"
                        })
    except Exception as e:
        logger.error(f"❌ Failure harvesting UN GDACS crisis layer: {e}")
        
    # Advanced Geopolitical Mock Injection (GDELT Simulation) for active areas in your demo
    # This ensures the system simulates tactical incidents (Ormuz blockades, Red Sea attacks)
    incidents.extend([
        {"source": "GDELT_GEOPOLITICAL", "event": "Haifa Port Security Lockdown", "details": "Tactical airspace closure and harbor perimeter enforcement due to security threat mitigation updates.", "lat": 32.8191, "lng": 34.9983, "severity": "CRITICAL"},
        {"source": "GDELT_GEOPOLITICAL", "event": "Strait of Hormuz Naval Bottleneck", "details": "Commercial maritime transit slowing down due to regulatory inspection checkpoints.", "lat": 26.5670, "lng": 56.4520, "severity": "CRITICAL"}
    ])
    
    return incidents

def get_incidents_by_hq(hq_name: str) -> Dict[str, Any]:
    current_time = time.time()
    hq_name_lower = hq_name.lower().strip()
    
    if hq_name_lower not in AVAILABLE_LOCATIONS:
        return {"status": "error", "message": "Target location out of boundaries."}
        
    hq = AVAILABLE_LOCATIONS[hq_name_lower]
    
    # Geographic filtering (Geofencing) in X,Y coordinates
    all_global_crises = fetch_global_crisis_feed()
    local_threats = []
    
    for crisis in all_global_crises:
        # Calculate if the missile, strike or typhoon coordinate is near our operational range
        lat_diff = abs(crisis["lat"] - hq["lat"])
        lng_diff = abs(crisis["lng"] - hq["lon"])
        
        if lat_diff <= hq["range"] and lng_diff <= hq["range"]:
            local_threats.append(crisis)
            
    return {
        "status": "success",
        "location": hq_name_lower,
        "total_threats_detected": len(local_threats),
        "threat_level": "RED_ALERT" if any(t["severity"] == "CRITICAL" for t in local_threats) else "STABLE",
        "incidents": local_threats
    }

