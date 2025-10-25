from fastapi import APIRouter, Header, HTTPException, Query, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional, List
from datetime import datetime, timezone
import time
import os

from .models import SessionLocal, GPSPoint, init_db
from .schemas import GPSIn, GPSOut, NavigationResponse, NavigationStep
from .services import (
    transcribe_audio,
    translate_to_english,
    extract_place_name,
    geocode_place,
    get_directions,
    save_audio_file,
    store_navigation_request
)
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


@router.post("/navigate", response_model=NavigationResponse)
async def navigate(
    device_id: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    heading: Optional[float] = Form(None),
    audio: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Voice-based navigation endpoint for ESP32 Blind Stick.
    
    Flow:
    1. Receive audio blob + GPS + heading from ESP32
    2. Transcribe audio → text
    3. Translate to English (if needed)
    4. Extract place name from text
    5. Geocode place → destination lat/lng
    6. Get directions from origin to destination
    7. Return navigation payload (polyline, steps, waypoints)
    """
    _auth_or_401(x_api_key)
    
    # Get Google Maps API key from environment
    gmaps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not gmaps_api_key:
        return NavigationResponse(
            success=False,
            request_id=0,
            error="Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY in .env"
        )
    
    # Read audio content
    audio_content = await audio.read()
    
    # Save audio file
    audio_filename = f"nav_{device_id}_{int(time.time())}.webm"
    audio_path = save_audio_file(audio_content, audio_filename)
    
    # Step 1: Transcribe audio
    transcript, detected_lang = transcribe_audio(audio_content)
    if not transcript:
        return NavigationResponse(
            success=False,
            request_id=0,
            error="Could not transcribe audio. Ensure Google Cloud Speech-to-Text is configured."
        )
    
    # Step 2: Translate to English if needed
    translated_text, source_lang = translate_to_english(transcript, detected_lang)
    
    # Step 3: Extract place name
    place_name = extract_place_name(translated_text)
    if not place_name:
        return NavigationResponse(
            success=False,
            request_id=0,
            transcript=transcript,
            detected_language=source_lang,
            error="Could not extract destination place from speech."
        )
    
    # Step 4: Geocode place to get destination coordinates
    geocode_result = geocode_place(place_name, gmaps_api_key)
    if not geocode_result:
        return NavigationResponse(
            success=False,
            request_id=0,
            transcript=transcript,
            detected_language=source_lang,
            destination_place=place_name,
            error=f"Could not find location for: {place_name}"
        )
    
    dest_lat = geocode_result['lat']
    dest_lng = geocode_result['lng']
    dest_address = geocode_result['formatted_address']
    
    # Step 5: Get directions
    directions = get_directions(lat, lng, dest_lat, dest_lng, gmaps_api_key)
    if not directions:
        return NavigationResponse(
            success=False,
            request_id=0,
            transcript=transcript,
            detected_language=source_lang,
            destination_place=dest_address,
            destination_lat=dest_lat,
            destination_lng=dest_lng,
            error="Could not retrieve directions."
        )
    
    # Step 6: Store request in database
    nav_request = store_navigation_request(
        device_id=device_id,
        origin_lat=lat,
        origin_lng=lng,
        heading=heading,
        transcript=transcript,
        detected_language=source_lang,
        translated_text=translated_text,
        destination_place=dest_address,
        destination_lat=dest_lat,
        destination_lng=dest_lng,
        audio_path=audio_path
    )
    
    # Step 7: Build navigation response
    steps = [
        NavigationStep(
            instruction=s['instruction'],
            distance=s['distance'],
            duration=s['duration'],
            maneuver=s.get('maneuver')
        )
        for s in directions['steps']
    ]
    
    return NavigationResponse(
        success=True,
        request_id=nav_request.id,
        transcript=transcript,
        detected_language=source_lang,
        destination_place=dest_address,
        destination_lat=dest_lat,
        destination_lng=dest_lng,
        distance_text=directions['distance'],
        duration_text=directions['duration'],
        overview_polyline=directions['polyline'],
        steps=steps
    )
