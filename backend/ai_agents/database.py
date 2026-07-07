# Unification of the supply chain by Industry Tracking ID
ENTERPRISE_SHIPMENTS = {
    # ✈️ AIR CASE: Links an AWB with a REAL OpenSky flight
    "AWB-FEDEX-9942": {
        "mode": "AIR_LIVE",
        "carrier_callsign": "FDX9942", # Your backend looks for this callsign in traffic_air.py
        "cargo": "Pallets of Electronic Circuit Boards",
        "client": "TechImport Houston LLC"
    },
    # 🚢 MARITIME CASE: Links an MBL with a REAL AISstream vessel
    "MBL-MAERSK-2077": {
        "mode": "OCEAN_LIVE",
        "vessel_mmsi": "211622000", # Your backend looks for this MMSI in traffic_sea.py
        "cargo": "Refrigerated Cherries Container",
        "client": "Exportadora de Frutas Santiago"
    },
    # 🚛 LAND CASE: Uses dead-reckoning navigation (Predictive Display)
    "BKG-LAND-04B": {
        "mode": "LAND_PREDICTIVE", # Uses the mathematical time calculation from traffic_land.py
        "cargo": "Industrial Electric Power Generators",
        "client": "Global Logistics Inc"
    }
}

