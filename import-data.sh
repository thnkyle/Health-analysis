#!/bin/bash
# Import health data exports into the local server
# Supports CSV and JSON files from Google Fit, Samsung Health, etc.
#
# Usage:
#   bash import-data.sh my_export.csv
#   bash import-data.sh my_export.json
#   bash import-data.sh ~/Downloads/*.csv

SERVER="http://127.0.0.1:8000"
USER_ID="default_user"

if [ $# -eq 0 ]; then
    echo "Usage: bash import-data.sh <file1.csv> [file2.json] ..."
    echo ""
    echo "Or generate 30 days of sample data:"
    echo "  bash import-data.sh --sample"
    echo ""
    echo "Supported formats:"
    echo "  CSV with columns: data_type, value, unit, recorded_at"
    echo "  JSON array of records"
    echo ""
    echo "Export guides:"
    echo "  Google Fit: Settings > Download your data (via Google Takeout)"
    echo "  Samsung Health: Settings > Download personal data"
    exit 1
fi

# Check server is running
if ! curl -s "$SERVER/api/v1/health" > /dev/null 2>&1; then
    echo "Error: Server not running. Start it first:"
    echo "  cd ~/Health-analysis/backend && uvicorn main:app --host 127.0.0.1 --port 8000"
    exit 1
fi

if [ "$1" = "--sample" ]; then
    echo "Generating 30 days of sample data..."
    python3 -c "
import json, random, urllib.request
from datetime import datetime, timedelta

records = []
now = datetime.now()
for d in range(29, -1, -1):
    dt = (now - timedelta(days=d)).isoformat()
    records.append({'user_id': '$USER_ID', 'data_type': 'steps', 'value': round(5000 + random.random() * 10000), 'unit': 'count', 'recorded_at': dt})
    records.append({'user_id': '$USER_ID', 'data_type': 'heart_rate', 'value': round(60 + random.random() * 30), 'unit': 'bpm', 'recorded_at': dt})
    records.append({'user_id': '$USER_ID', 'data_type': 'sleep', 'value': round(300 + random.random() * 240), 'unit': 'minutes', 'recorded_at': dt})
    records.append({'user_id': '$USER_ID', 'data_type': 'weight', 'value': round(70 + random.random() * 5 - 2.5, 1), 'unit': 'kg', 'recorded_at': dt})
    records.append({'user_id': '$USER_ID', 'data_type': 'calories', 'value': round(1500 + random.random() * 1000), 'unit': 'kcal', 'recorded_at': dt})

data = json.dumps({'records': records}).encode()
req = urllib.request.Request('$SERVER/api/v1/sync', data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f\"Inserted {result['inserted']} sample records\")
"
    exit 0
fi

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "File not found: $file"
        continue
    fi

    echo "Importing $file ..."

    python3 -c "
import csv, json, sys, urllib.request
from datetime import datetime

file_path = '$file'
user_id = '$USER_ID'
records = []

UNITS = {
    'steps': 'count', 'heart_rate': 'bpm', 'weight': 'kg', 'sleep': 'minutes',
    'calories': 'kcal', 'blood_pressure_systolic': 'mmHg', 'blood_pressure_diastolic': 'mmHg',
    'body_temperature': 'celsius', 'distance': 'meters', 'exercise': 'minutes',
    'nutrition': 'kcal',
}

if file_path.endswith('.json'):
    with open(file_path) as f:
        raw = json.load(f)
    items = raw if isinstance(raw, list) else raw.get('records', [])
    for r in items:
        dt = r.get('data_type') or r.get('type', 'steps')
        records.append({
            'user_id': r.get('user_id', user_id),
            'data_type': dt,
            'value': float(r.get('value', 0)),
            'unit': r.get('unit', UNITS.get(dt, 'unit')),
            'recorded_at': r.get('recorded_at') or r.get('timestamp') or datetime.now().isoformat(),
        })
else:
    with open(file_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = (row.get('data_type') or row.get('type', 'steps')).strip()
            records.append({
                'user_id': row.get('user_id', user_id).strip() if row.get('user_id') else user_id,
                'data_type': dt,
                'value': float(row.get('value', 0)),
                'unit': (row.get('unit') or UNITS.get(dt, 'unit')).strip(),
                'recorded_at': (row.get('recorded_at') or row.get('timestamp') or datetime.now().isoformat()).strip(),
            })

if not records:
    print('No records found in file')
    sys.exit(1)

data = json.dumps({'records': records}).encode()
req = urllib.request.Request('$SERVER/api/v1/sync', data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f\"  Imported {result['inserted']} records from $(basename $file)\")
"
done
