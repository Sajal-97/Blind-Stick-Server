## 📋 Setup Instructions

#### **Step 1: Get Google Cloud Credentials (Speech-to-Text + Translation)**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable these APIs:
   - **Cloud Speech-to-Text API**
   - **Cloud Translation API**
4. Create a service account:
   - Go to IAM & Admin → Service Accounts
   - Create service account with roles: "Cloud Speech Client" + "Cloud Translation API User"
   - Download JSON key file
5. Add to .env:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=/Users/mdtajbidhossainbappi/path/to/service-account.json
   ```

#### **Step 2: Get Google Maps API Key (Geocoding + Directions)**

1. Go to [Google Cloud Console → APIs & Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "API Key"
3. Enable these APIs:
   - **Geocoding API**
   - **Directions API**
   - **Places API** (optional, for better place search)
4. Restrict the API key (recommended):
   - Set Application restrictions: None or IP addresses (your server IP)
   - Set API restrictions: Select the 3 APIs above
5. Add to .env:
   ```bash
   GOOGLE_MAPS_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

### 🧪 Testing Without Google APIs (Optional)

If you want to test the endpoint structure without setting up Google APIs yet, I can create a mock mode that returns simulated responses. Would you like me to add that?

### 🚀 Once Configured

After adding the credentials to .env, restart the server and run:

```bash
python demo_navigation.py test_audio.webm
```

You should see output like:
```
✅ Navigation successful!
   Transcript: [your voice command]
   Detected Language: en
   Destination: [place name]
   Distance: X km
   Duration: Y mins
   📍 Turn-by-turn directions (N steps):
   1. Head northeast on Road 27... (120 m, 2 mins)
   2. Turn right onto Avenue 5... (500 m, 6 mins)
   ...
```

---

**Would you like me to:**
1. Create a mock/demo mode for testing without Google APIs?
2. Help you set up the Google Cloud project step-by-step?
3. Create alternative testing with just the GPS endpoints first?

Let me know what you'd prefer! 🎯

Made changes.