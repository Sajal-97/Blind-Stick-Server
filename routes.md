## API routes

Below are all routes exposed by the app, with method, purpose, auth, inputs, and a short example for each.

---

### GET /
- Purpose: Root / sanity check  
- Auth: none  
- Response: JSON
  - Example: `{ "message": "Blind Stick Server is running" }`

---

### GET /health
- Purpose: Health check (timestamp)  
- Auth: none  
- Response: JSON
  - Example: `{ "status": "ok", "time": "2025-10-20T..." }`

---

### POST /receive_gps
- Purpose: Ingest a GPS point and save to DB  
- Auth: X-API-Key header required (header name: `X-API-Key`) — value must match `API_KEY` env var  
- Content-Type: `application/json`  
- Body (GPSIn):
  - `lat` (float, required, -90..90)
  - `lon` (float, required, -180..180)
  - `hdop` (float, optional)
  - `ts` (string, optional ISO 8601)
  - `device_id` (string, optional; default `"esp32-1"`)  
- Response: 201 JSON `{ "ok": true, "id": <point_id> }`  

Example:
```bash
curl -X POST "http://127.0.0.1:8000/receive_gps" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"device_id":"esp32-1","lat":23.78,"lon":90.41,"ts":"2025-10-17T09:12:00Z"}'
```

---

### GET /latest
- Purpose: Get latest GPS point for a device  
- Auth: none  
- Query params:
  - `device_id` (string, required)  
- Response: `GPSOut` JSON:
  - `id`, `device_id`, `lat`, `lon`, `hdop`, `ts`, `created_at`

Example:
```bash
curl "http://127.0.0.1:8000/latest?device_id=esp32-1"
```

---

### GET /track
- Purpose: Return recent points for a device (array)  
- Auth: none  
- Query params:
  - `device_id` (string, required)
  - `limit` (int, optional, default 100, 1..1000)  
- Response: JSON array of `GPSOut` objects

Example:
```bash
curl "http://127.0.0.1:8000/track?device_id=esp32-1&limit=50"
```

---

### GET /geojson
- Purpose: Return recent points as a GeoJSON FeatureCollection  
- Auth: none  
- Query params:
  - `device_id` (string, required)
  - `limit` (int, optional, default 100, 1..2000)  
- Response: GeoJSON FeatureCollection

Example:
```bash
curl "http://127.0.0.1:8000/geojson?device_id=esp32-1&limit=200"
```

---

### GET /map
- Purpose: Simple Leaflet map UI (renders `map.html` template)  
- Auth: none  
- Response: HTML page you can open in a browser

Open in browser:
```
http://127.0.0.1:8000/map
```

---

### POST /upload_voice
- Purpose: Upload an audio file (voice SMS) → transcribe (Google Speech-to-Text if configured) → translate (Google Translate if configured) → store text in DB  
- Auth: X-API-Key header required (`X-API-Key`)  
- Content-Type: `multipart/form-data`  
- Form fields:
  - `file` (file, required) — audio file
  - `device_id` (string, optional)
  - `lang_tgt` (string, optional, default `"en"`) — target language code for translation  
- Response: 201 JSON with saved record and texts:
  ```json
  {
    "ok": true,
    "id": 123,
    "lang_src": "auto-detected-or-null",
    "lang_tgt": "en",
    "transcript": "transcribed text or placeholder",
    "translation": "translated text or null"
  }
  ```
- Notes:
  - For actual transcription/translation, set up Google credentials (see `GOOGLE_APPLICATION_CREDENTIALS`) and enable the Translate & Speech APIs. If Google is not configured the app stores a placeholder transcript.

Example (macOS / zsh):
```bash
curl -X POST "http://127.0.0.1:8000/upload_voice" \
  -H "X-API-Key: change-me" \
  -F "file=@/path/to/audio.wav" \
  -F "device_id=esp32-1" \
  -F "lang_tgt=en"
```

---

### GET /voice_messages
- Purpose: List recent voice message records (transcript + translation)  
- Auth: none  
- Query params:
  - `limit` (int, optional, default 100, 1..1000)  
- Response: array of `VoiceOut` objects:
  - `id`, `device_id`, `lang_src`, `lang_tgt`, `transcript`, `translation`, `created_at`

Example:
```bash
curl "http://127.0.0.1:8000/voice_messages?limit=20"
```

---

### GET /voice
- Purpose: Browser UI for uploading voice SMS (renders voice.html template)  
- Auth: none (UI expects you to supply `X-API-Key` value)  
- Response: HTML page

Open in browser:
```
http://127.0.0.1:8000/voice
```

---

## Notes
- Authentication: endpoints that modify data require the `X-API-Key` header and are checked against the `API_KEY` env var (default `change-me` if you do not set it). Read/write endpoints: `POST /receive_gps`, `POST /upload_voice`.
- Google APIs: to enable transcription/translation, set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON (or provide an API key and modify code to use it). See .env.example for placeholders.
- All endpoints are implemented in routes.py. Schemas live in schemas.py and DB models in models.py.

If you want, I can also:
- Produce a single OpenAPI/Markdown table with request+response JSON examples for each route.
- Add a `GET /debug/google` endpoint that returns whether Google clients are available (no secrets).