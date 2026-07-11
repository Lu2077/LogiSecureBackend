# backend/ai_agents/database.py
"""
Confidential In-Memory TMS Database
Local Data Sovereignty - Never leaves the on-premise server
"""

# ============================================================================
# UNIFIED SUPPLY CHAIN DATABASE
# ============================================================================

ENTERPRISE_SHIPMENTS = {
    # ============================================
    # ✈️ AIR CASE: Links an AWB with a REAL OpenSky flight
    # ============================================
    "AWB-FEDEX-9942": {
        "mode": "AIR_LIVE",
        "carrier_callsign": "FDX9942",  # Backend looks for this in traffic_air.py
        "cargo": "Pallets of Electronic Circuit Boards",
        "client": "TechImport Houston LLC",
        "origin": "Houston Hub",
        "destination": "Austin Assembly Plant",
        "priority": "High"
    },
    
    # ============================================
    # 🚢 MARITIME CASE: Links an MBL with a REAL AISstream vessel
    # ============================================
    "MBL-MAERSK-2077": {
        "mode": "OCEAN_LIVE",
        "vessel_mmsi": "211622000",  # Backend looks for this in traffic_sea.py
        "cargo": "Refrigerated Cherries Container",
        "client": "Exportadora de Frutas Santiago",
        "origin": "Port of Rotterdam",
        "destination": "Berlin Distribution Hub",
        "priority": "High"
    },
    
    # ============================================
    # 🚛 LAND CASE: Uses dead-reckoning navigation (Predictive Display)
    # ============================================
    "BKG-LAND-04B": {
        "mode": "LAND_PREDICTIVE",  # Uses OSRM + time calculation from traffic_land.py
        "cargo": "Industrial Electric Power Generators",
        "client": "Global Logistics Inc",
        "origin": "Port of Shanghai",
        "destination": "Suzhou Industrial Park",
        "priority": "Medium"
    },
    
    # ============================================
    # 📦 ADDITIONAL SHIPMENTS FOR TESTING
    # ============================================
    "MBL-MSC-8899": {
        "mode": "OCEAN_LIVE",
        "vessel_mmsi": "563000100",  # MSC MICHELLE
        "cargo": "Containerized Electronics",
        "client": "TechImport Singapore",
        "origin": "Port of Singapore",
        "destination": "Kuala Lumpur Hub",
        "priority": "Medium"
    },
    
    "AWB-DHL-5511": {
        "mode": "AIR_LIVE",
        "carrier_callsign": "DHL5511",
        "cargo": "Pharmaceuticals (Temperature Controlled)",
        "client": "PharmaGlobal EU",
        "origin": "Frankfurt Airport",
        "destination": "Dubai Logistics Hub",
        "priority": "Critical"
    },
    
    "BKG-EURO-8877": {
        "mode": "LAND_PREDICTIVE",
        "cargo": "Automotive Parts",
        "client": "EuroLogistics GmbH",
        "origin": "Rotterdam Port",
        "destination": "Munich Assembly Plant",
        "priority": "High"
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_shipment(tracking_id: str) -> dict:
    """Get a shipment by tracking ID"""
    return ENTERPRISE_SHIPMENTS.get(tracking_id.upper().strip())

def get_all_shipments() -> dict:
    """Get all shipments"""
    return ENTERPRISE_SHIPMENTS

def get_shipments_by_mode(mode: str) -> dict:
    """Get shipments by mode (AIR_LIVE, OCEAN_LIVE, LAND_PREDICTIVE)"""
    return {k: v for k, v in ENTERPRISE_SHIPMENTS.items() if v.get("mode") == mode}

def get_shipments_by_client(client: str) -> dict:
    """Get shipments by client name"""
    client_lower = client.lower()
    return {k: v for k, v in ENTERPRISE_SHIPMENTS.items() if client_lower in v.get("client", "").lower()}


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📦 ENTERPRISE SHIPMENTS DATABASE")
    print("=" * 60)
    
    print(f"\nTotal Shipments: {len(ENTERPRISE_SHIPMENTS)}")
    print(f"Tracking IDs: {list(ENTERPRISE_SHIPMENTS.keys())}")
    
    print("\n📊 By Mode:")
    for mode in ["AIR_LIVE", "OCEAN_LIVE", "LAND_PREDICTIVE"]:
        count = len(get_shipments_by_mode(mode))
        print(f"  {mode}: {count}")
    
    print("\n📋 All Shipments:")
    for tracking_id, data in ENTERPRISE_SHIPMENTS.items():
        print(f"  {tracking_id} -> {data['mode']} | {data['client']}")
    
    print("\n✅ Database loaded successfully!")