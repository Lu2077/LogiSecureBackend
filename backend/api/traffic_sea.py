# backend/api/traffic_sea.py
"""
Maritime traffic API - AISstream V0 with full classification
FIXED: MMSI tracking across ALL HQs, expanded port list, mock fallback
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import websockets
from config import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# MOCK DATA (Fallback when API key is missing or fails)
# ============================================================================

MOCK_VESSELS = {
    "rotterdam": [
        {"mmsi": "244710000", "name": "EVER GIVEN", "lat": 51.92, "lon": 4.48,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Netherlands", "speed": 0, "course": 0, "heading": 0},
        {"mmsi": "244710001", "name": "MSC OSCAR", "lat": 51.90, "lon": 4.45,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Netherlands", "speed": 5.2, "course": 90, "heading": 85},
        {"mmsi": "244710002", "name": "MAERSK HAMBURG", "lat": 51.95, "lon": 4.50,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Netherlands", "speed": 8.7, "course": 180, "heading": 175},
    ],
    "singapore": [
        {"mmsi": "563000100", "name": "MSC MICHELLE", "lat": 1.29, "lon": 103.85,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Singapore", "speed": 0, "course": 0, "heading": 0},
        {"mmsi": "563000101", "name": "MAERSK SINGAPORE", "lat": 1.28, "lon": 103.82,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Singapore", "speed": 3.4, "course": 45, "heading": 40},
    ],
    "houston": [
        {"mmsi": "367000100", "name": "MAERSK HOUSTON", "lat": 29.76, "lon": -95.37,
         "type": "tanker", "type_label": "Tanque", "category": "Comercial",
         "country": "United States", "speed": 2.1, "course": 180, "heading": 175},
    ],
    "tokyo": [
        {"mmsi": "431000100", "name": "NYK VENUS", "lat": 35.50, "lon": 139.80,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Japan", "speed": 0, "course": 0, "heading": 0},
    ],
    "shanghai": [
        {"mmsi": "413000000", "name": "COSCO SHIPPING", "lat": 31.23, "lon": 121.47,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "China", "speed": 0, "course": 0, "heading": 0},
    ],
    "antwerp": [
        {"mmsi": "205000100", "name": "MSC ANTWERP", "lat": 51.22, "lon": 4.40,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Belgium", "speed": 0, "course": 0, "heading": 0},
    ],
    "hamburg": [
        {"mmsi": "211000100", "name": "MAERSK HAMBURG", "lat": 53.55, "lon": 9.99,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "Germany", "speed": 0, "course": 0, "heading": 0},
    ],
    "dubai": [
        {"mmsi": "470000100", "name": "MSC DUBAI", "lat": 25.20, "lon": 55.27,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "UAE", "speed": 0, "course": 0, "heading": 0},
    ],
    "los_angeles": [
        {"mmsi": "366000100", "name": "CMA CGM LOS ANGELES", "lat": 33.75, "lon": -118.25,
         "type": "cargo", "type_label": "Carga", "category": "Comercial",
         "country": "United States", "speed": 0, "course": 0, "heading": 0},
    ],
}

# Combined index for fast MMSI lookup
ALL_MOCK_SHIPS = {}
for hq, ships in MOCK_VESSELS.items():
    for ship in ships:
        ALL_MOCK_SHIPS[ship["mmsi"]] = {**ship, "hq": hq}


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

AIS_WS_URL = "wss://stream.aisstream.io/v0/stream"


# ============================================================================
# BOUNDING BOXES - EXPANDED
# ============================================================================

PORT_BOUNDING_BOXES = {
    # Europe
    "rotterdam": [[51.80, 3.80], [52.10, 4.80]],
    "antwerp": [[51.10, 4.20], [51.40, 4.50]],
    "hamburg": [[53.40, 9.80], [53.70, 10.10]],
    "bremerhaven": [[53.50, 8.40], [53.60, 8.70]],
    "felixstowe": [[51.90, 1.30], [52.00, 1.50]],
    "le_havre": [[49.40, 0.10], [49.60, 0.30]],
    
    # Asia
    "singapore": [[1.00, 103.50], [1.50, 104.50]],
    "shanghai": [[30.80, 121.00], [31.60, 122.20]],
    "ningbo": [[29.80, 121.80], [30.00, 122.20]],
    "shenzhen": [[22.40, 113.80], [22.60, 114.20]],
    "tokyo": [[34.50, 138.80], [36.50, 141.00]],
    "busan": [[35.00, 129.00], [35.20, 129.20]],
    
    # Americas
    "houston": [[29.30, -95.10], [29.90, -94.70]],
    "los_angeles": [[33.50, -118.50], [34.00, -118.00]],
    "long_beach": [[33.70, -118.30], [33.80, -118.10]],
    "new_york": [[40.50, -74.10], [40.80, -74.00]],
    "sao_paulo": [[-24.00, -46.60], [-23.70, -46.10]],
    "panama": [[8.80, -79.60], [9.00, -79.40]],
    
    # Middle East
    "dubai": [[24.50, 54.50], [25.50, 55.50]],
    "jebel_ali": [[24.90, 54.90], [25.10, 55.10]],
    "dammam": [[26.40, 50.10], [26.60, 50.30]],
    
    # Africa
    "durban": [[-29.90, 31.00], [-29.70, 31.20]],
    "cape_town": [[-33.90, 18.40], [-33.70, 18.60]],
}


# ============================================================================
# VESSEL CLASSIFICATION
# ============================================================================

def classify_vessel(ais_type: int, mmsi: int) -> str:
    """
    Clasifica un buque por su código de tipo AIS.
    Códigos basados en el estándar AIS (ITU-R M.1371-5)
    """
    # 80-89: Tanques (Oil/Chemical/Gas)
    if 80 <= ais_type <= 89:
        return "tanker"
    # 70-79: Carga (Container/Cargo)
    if 70 <= ais_type <= 79:
        return "cargo"
    # 60-69: Pasajeros (Cruceros, Ferries)
    if 60 <= ais_type <= 69:
        return "passenger"
    # 36-37: Veleros/Yates
    if ais_type in (36, 37):
        return "yacht"
    # 35: Militar
    if ais_type == 35:
        return "military"
    # 30-34: Pesca, Remolcadores, Buceo
    if ais_type in (30, 31, 32, 33, 34):
        return "fishing"
    # 50-59: Piloto, SAR, Puerto
    if 50 <= ais_type <= 59:
        return "port_service"
    # MMSI-based military detection (US Navy, etc.)
    mmsi_str = str(mmsi)
    if mmsi_str.startswith("3380") or mmsi_str.startswith("3381"):
        return "military"
    # 99: Buque de alta velocidad
    if ais_type == 99:
        return "high_speed"
    # Cualquier otro
    return "unknown"


def classify_by_name(ship_name: str) -> str:
    """
    Clasificación FALLBACK por patrón en el nombre.
    Usado cuando no llega el ShipType.
    """
    if not ship_name:
        return "unknown"
    
    name_upper = ship_name.upper().strip()
    
    # Lineras (Container/Cargo)
    liners = ["MAERSK", "MSC", "CMA", "COSCO", "ONE", "EVERGREEN", "HAPAG", 
              "OOCL", "HYUNDAI", "YANG MING", "ZIM", "K LINE", "MOL", "NYK"]
    for pattern in liners:
        if pattern in name_upper:
            return "cargo"
    
    # Tanques (LNG, Oil, Chemical)
    tankers = ["LNG", "TANKER", "OIL", "BULK", "GAS", "CRUDE", "CHEMICAL", 
               "VLCC", "SUEZMAX", "AFRAMAX", "PANAMAX"]
    for pattern in tankers:
        if pattern in name_upper:
            return "tanker"
    
    # Pasajeros
    passengers = ["CRUISE", "FERRY", "QUEEN", "PRINCESS", "CELEBRITY", "CARNIVAL"]
    for pattern in passengers:
        if pattern in name_upper:
            return "passenger"
    
    # Yates
    yachts = ["YACHT", "S/Y", "MY ", "M/Y"]
    for pattern in yachts:
        if pattern in name_upper:
            return "yacht"
    
    # Militares
    military = ["WARSHIP", "NAVY", "USCGC", "HMAS", "FS ", "HMS "]
    for pattern in military:
        if pattern in name_upper:
            return "military"
    
    return "unknown"


def get_vessel_label(vessel_type: str) -> str:
    """Devuelve una etiqueta legible para el tipo de buque"""
    labels = {
        "tanker": "Tanque",
        "cargo": "Carga",
        "passenger": "Pasajeros",
        "yacht": "Yate",
        "military": "Militar",
        "fishing": "Pesca",
        "port_service": "Servicio Portuario",
        "high_speed": "Alta Velocidad",
        "unknown": "Desconocido"
    }
    return labels.get(vessel_type, vessel_type)


def get_vessel_category(vessel_type: str) -> str:
    """Devuelve una categoría más general para agrupación"""
    categories = {
        "tanker": "Comercial",
        "cargo": "Comercial",
        "passenger": "Comercial",
        "yacht": "Recreativo",
        "military": "Gubernamental",
        "fishing": "Comercial",
        "port_service": "Servicio",
        "high_speed": "Comercial",
        "unknown": "Desconocido"
    }
    return categories.get(vessel_type, "Desconocido")


# ============================================================================
# COUNTRY DETECTION FROM MMSI
# ============================================================================

MID_COUNTRY = {
    # Europa
    201: "Albania", 202: "Andorra", 203: "Austria", 204: "Portugal",
    205: "Belgium", 206: "Belarus", 207: "Bulgaria", 208: "Vatican",
    209: "Cyprus", 210: "Cyprus", 211: "Germany", 212: "Cyprus",
    213: "Georgia", 214: "Moldova", 215: "Malta", 216: "Armenia",
    218: "Germany", 219: "Denmark", 220: "Denmark", 224: "Spain",
    225: "Spain", 226: "France", 227: "France", 228: "France",
    229: "Malta", 230: "Finland", 231: "Faroe Islands", 232: "United Kingdom",
    233: "United Kingdom", 234: "United Kingdom", 235: "United Kingdom",
    236: "Gibraltar", 237: "Greece", 238: "Croatia", 239: "Greece",
    240: "Greece", 241: "Greece", 242: "Morocco", 243: "Hungary",
    244: "Netherlands", 245: "Netherlands", 246: "Netherlands", 247: "Italy",
    248: "Malta", 249: "Malta", 250: "Ireland", 251: "Iceland",
    252: "Liechtenstein", 253: "Luxembourg", 254: "Monaco", 255: "Portugal",
    256: "Malta", 257: "Norway", 258: "Norway", 259: "Norway",
    261: "Poland", 263: "Portugal", 264: "Romania", 265: "Sweden",
    266: "Sweden", 267: "Slovakia", 268: "San Marino", 269: "Switzerland",
    270: "Czech Republic", 271: "Turkey", 272: "Ukraine", 273: "Russia",
    274: "North Macedonia", 275: "Latvia", 276: "Estonia", 277: "Lithuania",
    278: "Slovenia",
    # América
    301: "Anguilla", 303: "Alaska", 304: "Antigua", 305: "Antigua",
    306: "Netherlands Antilles", 307: "Aruba", 308: "Bahamas", 309: "Bahamas",
    310: "Bermuda", 311: "Bahamas", 312: "Belize", 314: "Barbados",
    316: "Canada", 319: "Cayman Islands", 321: "Costa Rica", 323: "Cuba",
    325: "Dominica", 327: "Dominican Republic", 329: "Guadeloupe",
    330: "Grenada", 331: "Greenland", 332: "Guatemala", 334: "Honduras",
    336: "Haiti", 338: "United States", 339: "Jamaica", 341: "Saint Kitts",
    343: "Saint Lucia", 345: "Mexico", 347: "Martinique", 348: "Montserrat",
    350: "Nicaragua", 351: "Panama", 352: "Panama", 353: "Panama",
    354: "Panama", 355: "Panama", 356: "Panama", 357: "Panama",
    358: "Puerto Rico", 359: "El Salvador", 361: "Saint Pierre",
    362: "Trinidad", 364: "Turks and Caicos", 366: "United States",
    367: "United States", 368: "United States", 369: "United States",
    370: "Panama", 371: "Panama", 372: "Panama", 373: "Panama",
    374: "Panama", 375: "Saint Vincent", 376: "Saint Vincent",
    377: "Saint Vincent", 378: "British Virgin Islands", 379: "US Virgin Islands",
    # Asia
    401: "Afghanistan", 403: "Saudi Arabia", 405: "Bangladesh", 408: "Bahrain",
    410: "Bhutan", 412: "China", 413: "China", 414: "China",
    416: "Taiwan", 417: "Sri Lanka", 419: "India", 422: "Iran",
    423: "Azerbaijan", 425: "Iraq", 428: "Israel", 431: "Japan",
    432: "Japan", 434: "Turkmenistan", 436: "Kazakhstan", 437: "Uzbekistan",
    438: "Jordan", 440: "South Korea", 441: "South Korea", 443: "Palestine",
    445: "North Korea", 447: "Kuwait", 450: "Lebanon", 451: "Kyrgyzstan",
    453: "Macao", 455: "Maldives", 457: "Mongolia", 459: "Nepal",
    461: "Oman", 463: "Pakistan", 466: "Qatar", 468: "Syria",
    470: "UAE", 472: "Tajikistan", 473: "Yemen", 475: "Tonga",
    477: "Hong Kong", 478: "Bosnia",
    # África
    601: "South Africa", 603: "Angola", 605: "Algeria", 607: "Benin",
    609: "Botswana", 610: "Burundi", 611: "Cameroon", 612: "Cape Verde",
    613: "Central African Republic", 615: "Congo", 616: "Comoros",
    617: "DR Congo", 618: "Ivory Coast", 619: "Djibouti", 620: "Egypt",
    621: "Equatorial Guinea", 622: "Ethiopia", 624: "Eritrea", 625: "Gabon",
    626: "Gambia", 627: "Ghana", 629: "Guinea", 630: "Guinea-Bissau",
    631: "Kenya", 632: "Lesotho", 633: "Liberia", 634: "Liberia",
    635: "Liberia", 636: "Liberia", 637: "Libya", 642: "Madagascar",
    644: "Malawi", 645: "Mali", 647: "Mauritania", 649: "Mauritius",
    650: "Mozambique", 654: "Namibia", 655: "Niger", 656: "Nigeria",
    657: "Guinea", 659: "Rwanda", 660: "Senegal", 661: "Sierra Leone",
    662: "Somalia", 663: "South Africa", 664: "Sudan", 667: "Tanzania",
    668: "Togo", 669: "Tunisia", 670: "Uganda", 671: "Egypt",
    672: "Tanzania", 674: "Zambia", 675: "Zimbabwe", 676: "Comoros",
    677: "Tanzania",
}


def get_country_from_mmsi(mmsi: int) -> str:
    """Obtiene el país del MMSI (primeros 3 dígitos)"""
    mmsi_str = str(mmsi)
    if len(mmsi_str) == 9:
        mid = int(mmsi_str[:3])
        return MID_COUNTRY.get(mid, "UNKNOWN")
    return "UNKNOWN"


# ============================================================================
# CORE AISSTREAM FUNCTION
# ============================================================================

async def get_ais_vessels_async(hq_name: str, max_messages: int = 25) -> List[Dict]:
    """
    Obtiene buques vía WebSocket AISstream V0 con clasificación COMPLETA.
    """
    settings = get_settings()
    hq_name_lower = hq_name.lower().strip()
    
    if hq_name_lower not in PORT_BOUNDING_BOXES:
        logger.error(f"Sede '{hq_name}' no configurada")
        return []
    
    if not settings.AISSTREAM_API_KEY:
        logger.warning("AISSTREAM_API_KEY no configurada, usando mock data")
        return MOCK_VESSELS.get(hq_name_lower, [])
    
    bbox = PORT_BOUNDING_BOXES[hq_name_lower]
    
    subscription_payload = {
        "APIKey": settings.AISSTREAM_API_KEY,
        "BoundingBoxes": [bbox],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }
    
    vessels = []
    seen_mmsi = set()
    vessel_static_data = {}
    
    try:
        logger.info(f"Conectando a AISstream V0 para [{hq_name_lower}]...")
        
        async with websockets.connect(AIS_WS_URL) as websocket:
            logger.info("WebSocket conectado. Enviando suscripcion...")
            await websocket.send(json.dumps(subscription_payload))
            logger.info("Escuchando datos satelitales...")
            
            for i in range(max_messages):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    packet = json.loads(message)
                    
                    msg_type = packet.get("MessageType", "")
                    metadata = packet.get("MetaData", {})
                    msg_data = packet.get("Message", {})
                    
                    mmsi = metadata.get("MMSI")
                    if not mmsi:
                        continue
                    
                    if msg_type == "ShipStaticData":
                        static = msg_data.get("ShipStaticData", {})
                        vessel_static_data[mmsi] = {
                            "name": static.get("Name", "").strip(),
                            "type": static.get("Type", 0),
                            "callsign": static.get("CallSign", "").strip(),
                            "imo": static.get("ImoNumber", 0),
                            "destination": static.get("Destination", "").strip(),
                        }
                        if vessel_static_data[mmsi]["name"]:
                            metadata["ShipName"] = vessel_static_data[mmsi]["name"]
                        continue
                    
                    if msg_type not in ("PositionReport", "StandardClassBPositionReport"):
                        continue
                    
                    if mmsi in seen_mmsi:
                        continue
                    
                    seen_mmsi.add(mmsi)
                    
                    if msg_type == "PositionReport":
                        report = msg_data.get("PositionReport", {})
                        lat = report.get("Latitude", metadata.get("latitude"))
                        lon = report.get("Longitude", metadata.get("longitude"))
                        sog = report.get("Sog", metadata.get("SpeedOverGround", 0))
                        cog = report.get("Cog", metadata.get("CourseOverGround", 0))
                        heading = report.get("TrueHeading", 0)
                    else:
                        lat = metadata.get("Latitude")
                        lon = metadata.get("Longitude")
                        sog = metadata.get("SpeedOverGround", 0)
                        cog = metadata.get("CourseOverGround", 0)
                        heading = 0
                    
                    if lat is None or lon is None:
                        continue
                    
                    static = vessel_static_data.get(mmsi, {})
                    ship_name = static.get("name") or metadata.get("ShipName", "UNKNOWN").strip()
                    if not ship_name or ship_name == "UNKNOWN":
                        ship_name = f"Vessel-{mmsi}"
                    
                    ais_type = static.get("type", metadata.get("ShipType", 0))
                    vessel_type = classify_vessel(ais_type, mmsi)
                    
                    if vessel_type == "unknown" and ship_name:
                        vessel_type = classify_by_name(ship_name)
                    
                    country = get_country_from_mmsi(mmsi)
                    vessel_label = get_vessel_label(vessel_type)
                    vessel_category = get_vessel_category(vessel_type)
                    
                    vessels.append({
                        "mmsi": str(mmsi),
                        "name": ship_name,
                        "lat": float(lat),
                        "lon": float(lon),
                        "type": vessel_type,
                        "type_label": vessel_label,
                        "category": vessel_category,
                        "ais_type_code": ais_type,
                        "country": country,
                        "callsign": static.get("callsign", ""),
                        "imo": static.get("imo", 0),
                        "destination": static.get("destination", ""),
                        "speed": round(float(sog or 0), 1),
                        "course": round(float(cog or 0), 1),
                        "heading": heading,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    })
                    
                    logger.info(f"Buque: {ship_name} [{vessel_label}] - {country} en ({lat:.4f}, {lon:.4f})")
                    
                except asyncio.TimeoutError:
                    logger.info(f"Timeout despues de {i+1} mensajes")
                    break
                except json.JSONDecodeError:
                    continue
                    
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"Error WebSocket: {e}")
        return MOCK_VESSELS.get(hq_name_lower, [])
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return MOCK_VESSELS.get(hq_name_lower, [])
    
    logger.info(f"Capturados {len(vessels)} buques unicos")
    return vessels


# ============================================================================
# RESPONSE FORMATTER
# ============================================================================

def format_response(hq: str, ships: List[Dict], source: str) -> Dict[str, Any]:
    """Formatea la respuesta consistentemente"""
    stats = {
        "cargo": 0, "tanker": 0, "passenger": 0, "yacht": 0,
        "military": 0, "fishing": 0, "port_service": 0, 
        "high_speed": 0, "unknown": 0
    }
    category_stats = {
        "Comercial": 0, "Recreativo": 0, "Gubernamental": 0,
        "Servicio": 0, "Desconocido": 0
    }
    
    for s in ships:
        vessel_type = s.get("type", "unknown")
        stats[vessel_type] = stats.get(vessel_type, 0) + 1
        category = s.get("category", "Desconocido")
        category_stats[category] = category_stats.get(category, 0) + 1
    
    return {
        "status": "success" if ships else "info",
        "location": hq.lower(),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "total_vessels": len(ships),
        "data": {
            "all_vessels": ships,
            "by_type": stats,
            "by_category": category_stats
        },
        "source": source
    }


# ============================================================================
# FASTAPI ENDPOINT FUNCTIONS - FIXED
# ============================================================================

async def get_vessels_by_company_hq_async(hq_name: str) -> Dict[str, Any]:
    """Obtiene buques cerca de una sede - CON FALLBACK A MOCK DATA"""
    hq_name = hq_name.lower().strip()
    
    # Try real API
    try:
        ships = await get_ais_vessels_async(hq_name)
        if ships:
            return format_response(hq_name, ships, "AISstream V0 WebSocket")
    except Exception as e:
        logger.warning(f"AISstream error: {e}")
    
    # Fallback to mock data
    if hq_name in MOCK_VESSELS:
        logger.info(f"Usando mock data para {hq_name}")
        return format_response(hq_name, MOCK_VESSELS[hq_name], "mock (fallback)")
    
    # No data available
    return {
        "status": "error",
        "message": f"No hay datos para '{hq_name}'",
        "available_hqs": list(PORT_BOUNDING_BOXES.keys()),
        "suggestion": "Prueba con: rotterdam, singapore, houston, shanghai, dubai"
    }


async def get_vessels_by_bbox_async(lat: float, lon: float, radius_km: float = 50) -> Dict[str, Any]:
    """Obtiene buques en un área definida por el usuario"""
    radius_deg = radius_km / 111.0
    bbox = [
        [lat - radius_deg, lon - radius_deg],
        [lat + radius_deg, lon + radius_deg]
    ]
    
    temp_key = f"bbox_{lat}_{lon}"
    PORT_BOUNDING_BOXES[temp_key] = bbox
    
    try:
        ships = await get_ais_vessels_async(temp_key, max_messages=15)
    finally:
        if temp_key in PORT_BOUNDING_BOXES:
            del PORT_BOUNDING_BOXES[temp_key]
    
    return {
        "status": "success" if ships else "info",
        "center": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "total_vessels": len(ships),
        "vessels": ships,
        "source": "AISstream V0 WebSocket"
    }


async def get_vessel_by_mmsi_async(mmsi: str) -> Dict[str, Any]:
    """
    Busca un buque específico por MMSI en TODAS las sedes - FIXED!
    """
    mmsi = mmsi.strip()
    
    # 1. Check mock data first (fast)
    if mmsi in ALL_MOCK_SHIPS:
        return {
            "status": "success",
            "vessel": ALL_MOCK_SHIPS[mmsi],
            "found_in": ALL_MOCK_SHIPS[mmsi].get("hq", "unknown"),
            "source": "mock"
        }
    
    # 2. Check all HQs via API
    for hq in PORT_BOUNDING_BOXES.keys():
        try:
            ships = await get_ais_vessels_async(hq, max_messages=20)
            for ship in ships:
                if ship.get("mmsi") == mmsi:
                    return {
                        "status": "success",
                        "vessel": ship,
                        "found_in": hq,
                        "source": "AISstream V0 WebSocket"
                    }
        except Exception as e:
            logger.warning(f"Error checking {hq}: {e}")
            continue
    
    # 3. Not found - provide helpful suggestions
    return {
        "status": "error",
        "message": f"Buque con MMSI '{mmsi}' no encontrado en ninguna sede",
        "suggestions": [
            "Verifica que el MMSI sea correcto (9 digitos)",
            "El buque puede estar fuera de las areas monitoreadas",
            "Prueba con estos MMSI de prueba: 244710000, 563000100, 367000100"
        ],
        "monitored_ports": list(PORT_BOUNDING_BOXES.keys())
    }


# ============================================================================
# SYNC VERSIONS FOR BACKWARD COMPATIBILITY
# ============================================================================

def get_vessels_by_company_hq(hq_name: str) -> Dict[str, Any]:
    """Version sincrona para compatibilidad"""
    return asyncio.run(get_vessels_by_company_hq_async(hq_name))


def get_vessel_by_mmsi(mmsi: str) -> Dict[str, Any]:
    """Version sincrona para compatibilidad"""
    return asyncio.run(get_vessel_by_mmsi_async(mmsi))


# ============================================================================
# TEST
# ============================================================================

async def test():
    """Prueba la conexión AISstream V0 con estadísticas por tipo"""
    print("=" * 60)
    print("MARITIME API TEST - FIXED VERSION")
    print("=" * 60)
    
    test_cases = [
        ("rotterdam", "test HQ"),
        ("singapore", "test HQ"),
        ("244710000", "test MMSI (EVER GIVEN)"),
        ("999999999", "test MMSI (not found)"),
    ]
    
    for test_item, test_type in test_cases:
        print(f"\n--- Testing: {test_item} ({test_type}) ---")
        
        if test_type == "test MMSI":
            result = await get_vessel_by_mmsi_async(test_item)
            if result["status"] == "success":
                vessel = result["vessel"]
                print(f"  Found: {vessel['name']} at {vessel['lat']}, {vessel['lon']}")
                print(f"  Type: {vessel['type_label']} | Country: {vessel['country']}")
                print(f"  Source: {result['source']} | Found in: {result.get('found_in', 'N/A')}")
            else:
                print(f"  {result['status']}: {result['message']}")
                if 'suggestions' in result:
                    for s in result['suggestions']:
                        print(f"    - {s}")
        else:
            result = await get_vessels_by_company_hq_async(test_item)
            if result["status"] == "success":
                print(f"  Found: {result['total_vessels']} vessels")
                print(f"  Source: {result['source']}")
                if result["data"]["by_type"]:
                    print("  By type:")
                    for t, count in result["data"]["by_type"].items():
                        if count > 0:
                            print(f"    - {t}: {count}")
            else:
                print(f"  {result['status']}: {result.get('message', 'No data')}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())