from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Annotated


class GPSIn(BaseModel):
    lat: Annotated[float, Field(..., ge=-90, le=90, description="Latitude")]
    lon: Annotated[float, Field(..., ge=-180, le=180, description="Longitude")]
    hdop: Optional[float] = Field(None, description="Horizontal dilution of precision")
    ts: Optional[str] = Field(None, description="ISO 8601 timestamp from device")
    device_id: str = Field("esp32-1", description="Device identifier")


class GPSOut(BaseModel):
    id: int
    device_id: str
    lat: float
    lon: float
    hdop: Optional[float] = None
    ts: datetime
    created_at: datetime


class NavigationStep(BaseModel):
    """Single navigation step (turn-by-turn instruction)"""
    instruction: str
    distance: str  # e.g., "500 m"
    duration: str  # e.g., "2 mins"
    maneuver: Optional[str] = None  # e.g., "turn-left", "turn-right"


class NavigationResponse(BaseModel):
    """Response payload sent back to ESP32"""
    success: bool
    request_id: int
    transcript: Optional[str] = None
    detected_language: Optional[str] = None
    destination_place: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    distance_text: Optional[str] = None  # total distance e.g., "5.2 km"
    duration_text: Optional[str] = None  # total duration e.g., "15 mins"
    overview_polyline: Optional[str] = None  # encoded polyline
    steps: List[NavigationStep] = []
    error: Optional[str] = None
