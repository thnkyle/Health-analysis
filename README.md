# Health Analysis

Full-stack health data platform: Android app reads health data via **Health Connect API**, syncs to a **Python/FastAPI** backend for trend analysis and anomaly detection.

## Architecture

```
Android App (Kotlin)  →  POST /api/v1/sync  →  FastAPI Backend (Python)
  Health Connect SDK                            SQLite + Pandas + NumPy
  Jetpack Compose UI                            Trend & Anomaly Analysis
```

## Backend

### Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs at `http://localhost:8000/docs`

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/sync` | Batch ingest health records |
| GET | `/api/v1/records?user_id=...` | Query records (filter by type, date range) |
| GET | `/api/v1/trends/{data_type}?user_id=...` | Daily/weekly/monthly trends |
| GET | `/api/v1/anomalies?user_id=...` | Z-score anomaly detection |
| GET | `/api/v1/health` | Health check |

### Tests

```bash
cd backend
pytest tests/test_api.py -v
```

## Android App

### Requirements
- Android Studio Hedgehog+
- Android SDK 34
- Device/emulator with Health Connect app installed

### Setup
1. Open `android/` in Android Studio
2. Sync Gradle
3. Update `backendUrl` in `MainActivity.kt` to your backend address
4. Build and run on device

### Supported Health Data Types
Steps, Distance, Calories, Exercise, Heart Rate, Blood Pressure, Body Temperature, Weight, Sleep, Nutrition

## Data Types

| Type | Unit | Source Record |
|------|------|---------------|
| steps | count | StepsRecord |
| distance | meters | DistanceRecord |
| calories | kcal | TotalCaloriesBurnedRecord |
| heart_rate | bpm | HeartRateRecord |
| blood_pressure_systolic | mmHg | BloodPressureRecord |
| blood_pressure_diastolic | mmHg | BloodPressureRecord |
| body_temperature | celsius | BodyTemperatureRecord |
| weight | kg | WeightRecord |
| sleep | minutes | SleepSessionRecord |
