"""Check hospital/ambulance status for emergency page visibility"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smartambulance'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 100)
    print("CHECKING HOSPITALS FOR EMERGENCY PAGE VISIBILITY")
    print("=" * 100)
    
    # Get all hospitals with their details and ambulance count
    cursor.execute('''
        SELECT 
            h.id,
            h.name,
            h.latitude,
            h.longitude,
            h.status,
            h.available_beds,
            COUNT(a.id) as ambulance_count
        FROM hospitals h
        LEFT JOIN ambulances a ON a.hospital_id = h.id
        GROUP BY h.id, h.name, h.latitude, h.longitude, h.status, h.available_beds
        ORDER BY h.id
    ''')
    
    hospitals = cursor.fetchall()
    
    print(f"\n{'ID':<4} {'Name':<30} {'Lat':<10} {'Lng':<10} {'Status':<12} {'Beds':<6} {'Ambulances':<12} {'Visible?':<10}")
    print("-" * 100)
    
    for h in hospitals:
        has_coords = h['latitude'] is not None and h['longitude'] is not None
        status_ok = h['status'] == 'approved' or h['status'] is None
        has_ambulances = h['ambulance_count'] > 0
        is_visible = has_coords and status_ok and has_ambulances
        
        visible_text = "✓ YES" if is_visible else "✗ NO"
        
        print(f"{h['id']:<4} {h['name']:<30} {str(h['latitude']):<10} {str(h['longitude']):<10} {str(h['status']):<12} {h['available_beds']:<6} {h['ambulance_count']:<12} {visible_text:<10}")
    
    print("\n" + "=" * 100)
    print("REQUIREMENTS FOR HOSPITAL TO APPEAR ON EMERGENCY PAGE:")
    print("=" * 100)
    print("1. ✓ Must have latitude & longitude (NOT NULL)")
    print("2. ✓ Must have status = 'approved' (or NULL)")
    print("3. ✓ Must have at least 1 ambulance assigned")
    
    print("\n" + "=" * 100)
    print("AMBULANCE DETAILS:")
    print("=" * 100)
    
    cursor.execute('''
        SELECT 
            a.id,
            a.ambulance_number,
            a.hospital_id,
            h.name as hospital_name,
            a.status
        FROM ambulances a
        LEFT JOIN hospitals h ON h.id = a.hospital_id
        ORDER BY a.hospital_id, a.id
    ''')
    
    ambulances = cursor.fetchall()
    print(f"\n{'ID':<4} {'Ambulance #':<15} {'Hospital ID':<12} {'Hospital Name':<30} {'Status':<12}")
    print("-" * 73)
    
    for a in ambulances:
        print(f"{a['id']:<4} {a['ambulance_number']:<15} {str(a['hospital_id']):<12} {str(a['hospital_name']):<30} {a['status']:<12}")
    
    cursor.close()
    conn.close()
    
except Error as e:
    print(f"Error: {e}")
