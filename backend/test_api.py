"""
Test the LogiSecure API
"""

import requests
import json

url = "http://localhost:8000/agent-analyze"

data = {
    "type": "Port Strike",
    "location": "Rotterdam",
    "severity": "High",
    "description": "Dock workers strike affecting all container operations",
    "estimated_duration": "7 days"
}

print("📤 Sending request to LogiSecure API...")
response = requests.post(url, json=data)

if response.status_code == 200:
    print("✅ SUCCESS!")
    result = response.json()
    
    print("\n📊 Summary:")
    print(result.get("summary", "No summary"))
    
    print("\n📦 Affected Shipments:")
    for shipment in result.get("affected_shipments", []):
        print(f"  - {shipment['id']}: {shipment['cargo']} at {shipment['location']}")
    
    print("\n🛣️ Alternative Routes:")
    for route in result.get("alternative_routes", []):
        print(f"  - {route['route']} ({route['time']}) - Priority: {route['priority']}")
    
    print("\n🔔 Alerts:")
    for alert in result.get("alerts", []):
        print(f"  - {alert['message']}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)