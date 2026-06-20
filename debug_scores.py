import mysql.connector

conn = mysql.connector.connect(
    host='localhost', user='root', password='', database='smartambulance'
)
cur = conn.cursor(dictionary=True)

print("=" * 90)
print("HOSPITAL BEDS & FLEET LOAD")
print("=" * 90)
cur.execute('''
SELECT 
    h.name AS hospital_name,
    h.available_beds,
    h.total_beds,
    COUNT(drv.id) AS total_drivers,
    SUM(CASE WHEN drv.status = "on_duty" THEN 1 ELSE 0 END) AS busy_drivers,
    SUM(CASE WHEN drv.status = "available" THEN 1 ELSE 0 END) AS available_drivers
FROM hospitals h
LEFT JOIN drivers drv ON drv.hospital_id = h.id
GROUP BY h.id, h.name, h.available_beds, h.total_beds
ORDER BY h.name
''')
for r in cur.fetchall():
    busy_ratio = (r['busy_drivers'] or 0) / max(r['total_drivers'] or 1, 1)
    print(f"  {r['hospital_name']}")
    print(f"    Beds: {r['available_beds']} available / {r['total_beds']} total")
    print(f"    Drivers: {r['available_drivers']} available, {r['busy_drivers']} busy / {r['total_drivers']} total  (load ratio: {busy_ratio:.2f})")
    print()

print("=" * 90)
print("DRIVER STATUS & HISTORY")
print("=" * 90)
cur.execute('''
SELECT 
    drv.name AS driver_name,
    h.name AS hospital_name,
    drv.status,
    AVG(TIMESTAMPDIFF(MINUTE, pr.timestamp, d.updated_at)) AS avg_response_min,
    COUNT(d.dispatch_id) AS completed_trips
FROM drivers drv
JOIN hospitals h ON h.id = drv.hospital_id
LEFT JOIN dispatches d ON d.driver_id = drv.id AND LOWER(d.status) = "completed" AND d.updated_at IS NOT NULL
LEFT JOIN patient_requests pr ON pr.request_id = d.request_id
GROUP BY drv.id, drv.name, h.name, drv.status
ORDER BY h.name, drv.name
''')
for r in cur.fetchall():
    avg = round(float(r['avg_response_min']), 1) if r['avg_response_min'] else "15.0 (default/no history)"
    print(f"  {r['driver_name']} @ {r['hospital_name']}")
    print(f"    Status: {r['status']}  |  Avg response: {avg} min  |  Completed trips: {r['completed_trips']}")
    print()

print("=" * 90)
print("AI SCORE SIMULATION (sidebar ETA values as input)")
print("=" * 90)

import sys
sys.path.insert(0, r'c:\Users\zohai\OneDrive\Desktop\smart ambulance')
from ai_engine import calculate_dispatch_score

cur.execute('SELECT name, available_beds, total_beds FROM hospitals ORDER BY name')
hosp_beds = {r['name']: r for r in cur.fetchall()}

tests = [
    {'name': 'Gujrat Hospital',      'eta': 7,  'dist_km': 3.7},
    {'name': 'Aziz bhatti Hospital', 'eta': 9,  'dist_km': 4.2},
    {'name': 'Butt Hospital',        'eta': 5,  'dist_km': 3.0},
]

for t in tests:
    hdata = hosp_beds.get(t['name'], {})
    avail_beds = int(hdata.get('available_beds') or 50)
    total_beds = int(hdata.get('total_beds') or 100)
    score = calculate_dispatch_score(
        ambulance_lat=32.5, ambulance_lng=74.1,
        patient_lat=32.5, patient_lng=74.1,
        eta_minutes=t['eta'],
        hospital_busy_ambulances=0,
        hospital_total_ambulances=2,
        hospital_total_beds=total_beds,
        hospital_available_beds=avail_beds,
        driver_avg_response_minutes=15.0,
    )
    print(f"  {t['name']}")
    print(f"    ETA={t['eta']}min  Dist={t['dist_km']}km  Beds={avail_beds}/{total_beds}")
    print(f"    SCORE = {score['total_score']}  (lower = better)")
    print(f"    Breakdown: ETA_score={score['breakdown']['eta_score']}  Dist_score={score['breakdown']['distance_score']}  Bed_score={score['breakdown']['bed_availability_score']}")
    print()

conn.close()
