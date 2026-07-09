# backend/models.py
"""
Data models for LogiSecure API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================
# Enums
# ============================================

class IncidentType(str, Enum):
    PORT_STRIKE = "Port Strike"
    WEATHER = "Weather"
    GEOPOLITICAL = "Geopolitical"
    ACCIDENT = "Accident"
    OTHER = "Other"

class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

# ============================================
# Request Models
# ============================================

class IncidentRequest(BaseModel):
    """Request model for incident analysis"""
    type: str = Field(..., description="Type of incident")
    location: str = Field(..., description="Location of incident")
    severity: str = Field(..., description="Severity level")
    description: Optional[str] = Field("", description="Detailed description")
    estimated_duration: Optional[str] = Field("Unknown")
    affected_assets: Optional[str] = Field("Unknown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "Port Strike",
                "location": "Rotterdam",
                "severity": "High",
                "description": "Dock workers strike affecting all container operations",
                "estimated_duration": "7 days",
                "affected_assets": "5 cargo ships, 10,000 containers"
            }
        }

# ============================================
# Filtered Data Models (From Backend)
# ============================================

class IncidentContext(BaseModel):
    weather: Optional[str] = None
    traffic: Optional[str] = None
    geopolitical: Optional[str] = None

class IncidentSource(BaseModel):
    type: str
    name: str
    url: Optional[str] = None
    confidence: float = 0.5

class FilteredIncident(BaseModel):
    """Complete incident data with confidence"""
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str
    location: str
    severity: str
    description: str
    context: Optional[IncidentContext] = None
    source: Optional[IncidentSource] = None
    confidence: float = 0.5
    raw_data: Optional[Dict[str, Any]] = None
    
    def is_relevant(self, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold
    
    def get_ai_prompt_context(self) -> str:
        if not self.context:
            return ""
        return f"""
        Context:
        - Weather: {self.context.weather or 'Unknown'}
        - Traffic: {self.context.traffic or 'Unknown'}
        - Geopolitical: {self.context.geopolitical or 'Unknown'}
        - Confidence: {self.confidence:.0%}
        """

# ============================================
# Response Models
# ============================================

class HealthResponse(BaseModel):
    status: str
    agents: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    code: Optional[int] = None
    detail: Optional[str] = None