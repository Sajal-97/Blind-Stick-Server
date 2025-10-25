"""Navigation services module.

Provides voice-to-navigation pipeline:
- Speech-to-Text (Google Cloud)
- Translation (Google Cloud Translate)
- Place extraction (NLP heuristics)
- Geocoding (Google Maps)
- Directions (Google Maps)
"""

import re
import os
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from .models import SessionLocal, NavigationRequest
from .schemas import NavigationStep

# Setup uploads directory
UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'web' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Google Cloud clients
try:
    from google.cloud import speech_v1p1beta1 as speech
    from google.cloud import translate_v2 as translate
    GOOGLE_CLOUD_AVAILABLE = True
except Exception:
    GOOGLE_CLOUD_AVAILABLE = False

# Google Maps client
try:
    import googlemaps
    GOOGLE_MAPS_AVAILABLE = True
except Exception:
    GOOGLE_MAPS_AVAILABLE = False


def transcribe_audio(audio_content: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Transcribe audio using Google Speech-to-Text.
    Returns (transcript, detected_language_code) or (None, None) if unavailable.
    """
    if not GOOGLE_CLOUD_AVAILABLE:
        return (None, None)
    
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
            language_code="auto",
            enable_automatic_punctuation=True,
        )
        response = client.recognize(config=config, audio=audio)
        
        if response.results:
            transcript = " ".join([r.alternatives[0].transcript for r in response.results])
            # Detect language from first result if available
            lang_code = response.results[0].language_code if response.results else None
            return (transcript, lang_code)
        return (None, None)
    except Exception as e:
        print(f"Speech-to-Text error: {e}")
        return (None, None)


def translate_to_english(text: str, source_lang: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Translate text to English using Google Cloud Translate.
    Returns (translated_text, detected_source_language) or (text, None) if unavailable.
    """
    if not GOOGLE_CLOUD_AVAILABLE:
        return (text, None)
    
    try:
        client = translate.Client()
        
        # Detect language if not provided
        if not source_lang:
            detection = client.detect_language(text)
            source_lang = detection.get("language")
        
        # Skip translation if already English
        if source_lang and source_lang.lower().startswith("en"):
            return (text, source_lang)
        
        # Translate to English
        result = client.translate(text, target_language="en", source_language=source_lang)
        translated = result.get("translatedText", text)
        return (translated, source_lang)
    except Exception as e:
        print(f"Translation error: {e}")
        return (text, None)


def extract_place_name(text: str) -> Optional[str]:
    """
    Extract place/destination name from English text using simple NLP heuristics.
    Looks for patterns like "take me to X", "go to X", "navigate to X", etc.
    Returns extracted place name or the full text as fallback.
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Common navigation patterns
    patterns = [
        r"(?:take me to|go to|navigate to|direction to|find|show me|where is)\s+(.+)",
        r"(?:how do i get to|how to reach|route to)\s+(.+)",
        r"(?:i want to go to|i need to go to)\s+(.+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            place = match.group(1).strip()
            # Clean up trailing punctuation
            place = re.sub(r'[?.!,]+$', '', place)
            return place
    
    # If no pattern matched, return the full text (user might just say place name)
    return text.strip()


def geocode_place(place_name: str, gmaps_api_key: str) -> Optional[Dict[str, Any]]:
    """
    Geocode a place name using Google Maps Places/Geocoding API.
    Returns dict with 'lat', 'lng', 'formatted_address' or None if not found.
    """
    if not GOOGLE_MAPS_AVAILABLE or not place_name:
        return None
    
    try:
        gmaps = googlemaps.Client(key=gmaps_api_key)
        
        # Try geocoding first (handles addresses and place names)
        results = gmaps.geocode(place_name)
        
        if results:
            location = results[0]['geometry']['location']
            return {
                'lat': location['lat'],
                'lng': location['lng'],
                'formatted_address': results[0].get('formatted_address', place_name)
            }
        
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def get_directions(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    gmaps_api_key: str
) -> Optional[Dict[str, Any]]:
    """
    Get turn-by-turn directions from origin to destination using Google Maps Directions API.
    Returns dict with 'polyline', 'distance', 'duration', 'steps' or None if failed.
    """
    if not GOOGLE_MAPS_AVAILABLE:
        return None
    
    try:
        gmaps = googlemaps.Client(key=gmaps_api_key)
        
        # Request directions (walking mode for blind stick)
        result = gmaps.directions(
            origin=(origin_lat, origin_lng),
            destination=(dest_lat, dest_lng),
            mode="walking",
            alternatives=False
        )
        
        if not result:
            return None
        
        route = result[0]
        leg = route['legs'][0]
        
        # Extract steps
        steps = []
        for step in leg['steps']:
            steps.append({
                'instruction': step['html_instructions'],
                'distance': step['distance']['text'],
                'duration': step['duration']['text'],
                'maneuver': step.get('maneuver', None)
            })
        
        return {
            'polyline': route['overview_polyline']['points'],
            'distance': leg['distance']['text'],
            'duration': leg['duration']['text'],
            'steps': steps
        }
    except Exception as e:
        print(f"Directions error: {e}")
        return None


def save_audio_file(content: bytes, filename: str) -> str:
    """Save audio bytes to uploads directory and return relative path."""
    dest = UPLOAD_DIR / filename
    with open(dest, 'wb') as f:
        f.write(content)
    return f"web/uploads/{filename}"


def store_navigation_request(
    device_id: str,
    origin_lat: float,
    origin_lng: float,
    heading: Optional[float],
    transcript: Optional[str],
    detected_language: Optional[str],
    translated_text: Optional[str],
    destination_place: Optional[str],
    destination_lat: Optional[float],
    destination_lng: Optional[float],
    audio_path: Optional[str]
) -> NavigationRequest:
    """Store navigation request in database and return the record."""
    with SessionLocal() as db:
        req = NavigationRequest(
            device_id=device_id,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            heading=heading,
            transcript=transcript,
            detected_language=detected_language,
            translated_text=translated_text,
            destination_place=destination_place,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            audio_path=audio_path
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

