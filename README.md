# Blind-Stick-Server

A small FastAPI service for ingesting GPS points from devices and serving simple APIs and a map view.

## Quick start (macOS)

1. Create a virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Upgrade pip and install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt python-dotenv
```

3. (Optional) Create a `.env` file in the project root to override defaults:

```
API_KEY=change-me
DATABASE_URL=sqlite:///./gps.sqlite3
```

4. Run the server with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at http://127.0.0.1:8000

## Endpoints

- GET / — root message (used by tests)
- GET /health — returns basic status and timestamp
- POST /receive_gps — ingest a GPS point (expects JSON body and X-API-Key header)
  - Example body: {"device_id":"esp32-1","lat":23.78,"lon":90.41,"ts":"2025-10-17T09:12:00Z"}
- GET /latest?device_id=... — returns the latest point for a device
- GET /track?device_id=...&limit=... — returns recent points (limit default 100)
- GET /geojson?device_id=...&limit=... — returns GeoJSON FeatureCollection
- GET /map — simple Leaflet map showing recent points

## Testing

Run the test suite with pytest (ensure the virtualenv is active):

```bash
export PYTHONPATH="$(pwd)"
pytest -q
```

Two basic tests are provided in `tests/test_main.py`.

## Configuration

- `API_KEY` — default `change-me`. Set via environment or `.env`.
- `DATABASE_URL` — default `sqlite:///./gps.sqlite3`. Set to a Postgres URL to use Postgres.

## Notes

- The app uses SQLAlchemy and creates the `gps.sqlite3` SQLite file if not present.
- If you deploy to a server, set a secure `API_KEY` and use a proper database URL.

If you'd like, I can add a `.env.example` file, an integration test that posts a GPS point and verifies `/latest`, or a Dockerfile for easy containerized runs.
# Blind-Stick-Server