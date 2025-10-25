#!/usr/bin/env python3
"""
Demo script showing how ESP32 would call the /navigate endpoint.

Usage:
    python demo_navigation.py path/to/audio.webm

This simulates ESP32 uploading:
- Audio file (voice command like "take me to Dhaka University")
- Current GPS coordinates
- Compass heading (optional)
"""

import sys
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_navigation(audio_file_path: str):
    """Test the /navigate endpoint with a sample audio file."""
    
    # Server configuration
    BASE_URL = "http://localhost:8000"
    API_KEY = os.getenv("API_KEY", "change-me")  # Read from .env file
    
    # Simulate ESP32 current location (example: Dhaka, Bangladesh)
    device_id = "esp32-blind-stick-001"
    current_lat = 23.7809  # Dhaka
    current_lng = 90.2792
    heading = 45.0  # Northeast heading (optional)
    
    # Prepare multipart form data
    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'audio': ('command.webm', audio_file, 'audio/webm')
        }
        data = {
            'device_id': device_id,
            'lat': current_lat,
            'lng': current_lng,
            'heading': heading
        }
        headers = {
            'X-API-Key': API_KEY
        }
        
        print(f"🎤 Sending navigation request...")
        print(f"   Device: {device_id}")
        print(f"   Location: ({current_lat}, {current_lng})")
        print(f"   Heading: {heading}°")
        print(f"   Audio: {audio_file_path}")
        print()
        
        try:
            response = requests.post(
                f"{BASE_URL}/navigate",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result['success']:
                    print("✅ Navigation successful!")
                    print(f"   Transcript: {result.get('transcript', 'N/A')}")
                    print(f"   Detected Language: {result.get('detected_language', 'N/A')}")
                    print(f"   Destination: {result.get('destination_place', 'N/A')}")
                    print(f"   Coordinates: ({result.get('destination_lat')}, {result.get('destination_lng')})")
                    print(f"   Distance: {result.get('distance_text', 'N/A')}")
                    print(f"   Duration: {result.get('duration_text', 'N/A')}")
                    print(f"   Polyline: {result.get('overview_polyline', 'N/A')[:50]}...")
                    print(f"\n📍 Turn-by-turn directions ({len(result.get('steps', []))} steps):")
                    
                    for i, step in enumerate(result.get('steps', []), 1):
                        print(f"   {i}. {step['instruction'][:80]}... ({step['distance']}, {step['duration']})")
                else:
                    print(f"❌ Navigation failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection error. Is the server running?")
            print("   Start it with: uvicorn app.main:app --reload")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python demo_navigation.py <audio_file.webm>")
        print("\nExample:")
        print("  python demo_navigation.py test_audio.webm")
        print("\nNote: You need a real audio file with voice command like:")
        print('  "Take me to Dhaka University"')
        print('  "Navigate to Jatiya Sangsad Bhaban"')
        sys.exit(1)
    
    audio_file = sys.argv[1]
    test_navigation(audio_file)
