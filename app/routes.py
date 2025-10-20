from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional, List
from datetime import datetime, timezone

from .models import SessionLocal, GPSPoint, init_db
from .schemas import GPSIn, GPSOut
from .services import init_upload_dir
from .config import API_KEY

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


def _auth_or_401(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/")
def root():
    return {"message": "Blind Stick Server is running"}


@router.post("/receive_gps", response_model=dict)
def receive_gps(data: GPSIn, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _auth_or_401(x_api_key)
    with SessionLocal() as db:
        point = GPSPoint(
            device_id=data.device_id,
            lat=float(data.lat),
            lon=float(data.lon),
            hdop=float(data.hdop) if data.hdop is not None else None,
            ts=datetime.now(timezone.utc),
        )
        db.add(point)
        db.commit()
        db.refresh(point)
    return JSONResponse(status_code=201, content={"ok": True, "id": point.id})


@router.get("/latest", response_model=GPSOut)
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


@router.get("/track", response_model=List[GPSOut])
def track(device_id: str = Query(...), limit: int = Query(100, ge=1, le=1000)):
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


@router.get("/geojson")
def geojson(device_id: str = Query(...), limit: int = Query(100, ge=1, le=2000)):
    with SessionLocal() as db:
        rows = (
            db.query(GPSPoint)
            .filter(GPSPoint.device_id == device_id)
            .order_by(GPSPoint.ts.desc(), GPSPoint.id.desc())
            .limit(limit)
            .all()
        )
    features = []
    for r in reversed(rows):
        features.append({
            "type": "Feature",
            "properties": {
                "id": r.id,
                "device_id": r.device_id,
                "hdop": r.hdop,
                "ts": r.ts.isoformat(),
            },
            "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
        })
    return JSONResponse({"type": "FeatureCollection", "features": features})


# Reuse the existing HTML map from previous main; keep it simple here
LEAFLET_HTML = """(leaflet omitted for brevity)"""


@router.get("/map", response_class=HTMLResponse)
def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request, "default_device": "esp32-1"})


@router.get('/voice', response_class=HTMLResponse)
def voice_page(request: Request):
    # voice UI removed
    return HTMLResponse('<html><body><h3>Voice functionality has been removed from this server.</h3></body></html>')
