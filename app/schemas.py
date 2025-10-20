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

