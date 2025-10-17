import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Annotated
from fastapi.responses import HTMLResponse, JSONResponse

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, text
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ----------------------------
# Config
# ----------------------------
# Load .env if present
load_dotenv()
API_KEY = os.getenv("API_KEY", "change-me")  # can be set in .env or in the hosting environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gps.sqlite3")

# SQLite needs this arg; Postgres doesn't.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# ----------------------------
# Database model
# ----------------------------
class GPSPoint(Base):
    __tablename__ = "gps_points"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), index=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    hdop = Column(Float, nullable=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

Base.metadata.create_all(bind=engine)

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="GPS Ingest Server", version="1.0.0")

# ----------------------------
# Schemas
# ----------------------------
class GPSIn(BaseModel):
    # Validate latitude/longitude ranges using Pydantic v2 style
    lat: Annotated[float, Field(..., ge=-90, le=90, description="Latitude")]
    lon: Annotated[float, Field(..., ge=-180, le=180, description="Longitude")]
    hdop: Optional[float] = Field(None, description="Horizontal dilution of precision")
    ts: Optional[str] = Field(None, description="ISO 8601 timestamp from device, e.g. 2025-10-17T09:12:00Z")
    device_id: str = Field("esp32-1", description="Device identifier")

class GPSOut(BaseModel):
    id: int
    device_id: str
    lat: float
    lon: float
    hdop: Optional[float] = None
    ts: datetime
    created_at: datetime

# ----------------------------
# Helpers
# ----------------------------
def _parse_ts(ts: Optional[str]) -> datetime:
    """Parse ISO 8601, accept 'Z'. Default to now (UTC) if missing/invalid."""
    if not ts:
        return datetime.now(timezone.utc)
    try:
        # fromisoformat doesn't like 'Z', replace with +00:00
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def _auth_or_401(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@app.post("/receive_gps", response_model=dict)
def receive_gps(
    data: GPSIn,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    _auth_or_401(x_api_key)

    with SessionLocal() as db:
        point = GPSPoint(
            device_id=data.device_id,
            lat=float(data.lat),
            lon=float(data.lon),
            hdop=float(data.hdop) if data.hdop is not None else None,
            ts=_parse_ts(data.ts),
        )
        db.add(point)
        db.commit()
        db.refresh(point)

    return JSONResponse(status_code=201, content={"ok": True, "id": point.id})

@app.get("/latest", response_model=GPSOut)
def latest(device_id: str = Query(..., description="Device ID")):
    with SessionLocal() as db:
        row = (
            db.query(GPSPoint)
            .filter(GPSPoint.device_id == device_id)
            .order_by(GPSPoint.ts.desc(), GPSPoint.id.desc())
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="No data for device_id")
        return GPSOut(
            id=row.id,
            device_id=row.device_id,
            lat=row.lat,
            lon=row.lon,
            hdop=row.hdop,
            ts=row.ts,
            created_at=row.created_at,
        )

@app.get("/track", response_model=List[GPSOut])
def track(
    device_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000, description="Number of points"),
):
    with SessionLocal() as db:
        rows = (
            db.query(GPSPoint)
            .filter(GPSPoint.device_id == device_id)
            .order_by(GPSPoint.ts.desc(), GPSPoint.id.desc())
            .limit(limit)
            .all()
        )
        return [
            GPSOut(
                id=r.id,
                device_id=r.device_id,
                lat=r.lat,
                lon=r.lon,
                hdop=r.hdop,
                ts=r.ts,
                created_at=r.created_at,
            )
            for r in rows
        ]

@app.get("/geojson")
def geojson(
    device_id: str = Query(...),
    limit: int = Query(100, ge=1, le=2000),
):
    """Return recent points as a GeoJSON FeatureCollection."""
    with SessionLocal() as db:
        rows = (
            db.query(GPSPoint)
            .filter(GPSPoint.device_id == device_id)
            .order_by(GPSPoint.ts.desc(), GPSPoint.id.desc())
            .limit(limit)
            .all()
        )
    features = []
    for r in reversed(rows):  # oldest first for nice polylines
        features.append({
            "type": "Feature",
            "properties": {
                "id": r.id,
                "device_id": r.device_id,
                "hdop": r.hdop,
                "ts": r.ts.isoformat(),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [r.lon, r.lat],
            },
        })
    return JSONResponse({"type": "FeatureCollection", "features": features})

# ----------------------------
# Simple map (Leaflet)
# ----------------------------
LEAFLET_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>GPS Map</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <style>
    html,body,#map { height:100%; margin:0; }
    .legend { position:absolute; top:10px; left:10px; background:#fff; padding:8px 10px; border-radius:6px; box-shadow:0 0 10px rgba(0,0,0,.1); }
  </style>
</head>
<body>
  <div class="legend">
    Device: <input id="dev" value="esp32-1" size="12"/>
    Limit: <input id="lim" value="200" size="4"/>
    <button onclick="reloadData()">Load</button>
  </div>
  <div id="map"></div>

  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <script>
    const map = L.map('map');
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19}).addTo(map);

    let layer = null;

    async function reloadData() {
      const dev = document.getElementById('dev').value;
      const lim = document.getElementById('lim').value;
      const res = await fetch(`/geojson?device_id=${encodeURIComponent(dev)}&limit=${encodeURIComponent(lim)}`);
      const gj = await res.json();

      if (layer) layer.remove();
      layer = L.geoJSON(gj).addTo(map);

      const coords = gj.features.map(f => [f.geometry.coordinates[1], f.geometry.coordinates[0]]);
      if (coords.length) {
        const bounds = L.latLngBounds(coords);
        map.fitBounds(bounds.pad(0.2));
      } else {
        map.setView([23.7809, 90.2792], 12); // default view (Dhaka)
      }
    }

    reloadData();
  </script>
</body>
</html>
"""

@app.get("/map", response_class=HTMLResponse)
def map_page():
    return HTMLResponse(LEAFLET_HTML)