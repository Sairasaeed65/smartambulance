"""
Test Attendance System for SmartAmbulance Driver Dashboard
Tests: Database tables, Attendance marking, History retrieval
"""

import mysql.connector
import json
from datetime import datetime, date

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smartambulance'
}

def test_database_connection():
    """Test if database connection works"""
    print("[TEST] Database Connection...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"  ✓ Connected. Found {len(tables)} tables")
        
        # Check if attendance_records table exists
        cursor.execute("SHOW TABLES LIKE 'attendance_records'")
        if cursor.fetchone():
            print("  ✓ attendance_records table exists")
        else:
            print("  ✗ attendance_records table NOT found")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_attendance_schema():
    """Verify attendance_records table schema"""
    print("[TEST] Attendance Schema...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("DESCRIBE attendance_records")
        columns = cursor.fetchall()
        expected_columns = {'id', 'driver_id', 'date', 'status', 'admin_status', 'leave_reason', 'admin_id', 'approved_at', 'created_at'}
        found_columns = {col['Field'] for col in columns}
        
        if expected_columns.issubset(found_columns):
            print(f"  ✓ Schema correct. Columns: {', '.join(sorted(found_columns))}")
            cursor.close()
            conn.close()
            return True
        else:
            missing = expected_columns - found_columns
            print(f"  ✗ Missing columns: {missing}")
            cursor.close()
            conn.close()
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_driver_profile_pic():
    """Test profile_pic column in drivers table"""
    print("[TEST] Profile Pic Column...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("DESCRIBE drivers")
        columns = cursor.fetchall()
        column_names = {col['Field'] for col in columns}
        
        if 'profile_pic' in column_names:
            print("  ✓ profile_pic column exists in drivers table")
            cursor.close()
            conn.close()
            return True
        else:
            print("  ✗ profile_pic column NOT found in drivers table")
            print(f"    Available columns: {column_names}")
            cursor.close()
            conn.close()
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_attendance_insert():
    """Test inserting an attendance record"""
    print("[TEST] Insert Attendance Record...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get first driver
        cursor.execute("SELECT id, username FROM drivers LIMIT 1")
        driver = cursor.fetchone()
        
        if not driver:
            print("  ✗ No drivers found in database")
            cursor.close()
            conn.close()
            return False
        
        driver_id = driver['id']
        
        # Insert attendance record
        cursor.execute('''
            INSERT INTO attendance_records (driver_id, date, status, admin_status, leave_reason)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status=VALUES(status), admin_status=VALUES(admin_status)
        ''', (driver_id, date.today(), 'Present', 'approved', None))
        
        conn.commit()
        
        # Verify insert
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE driver_id = %s AND date = %s
        ''', (driver_id, date.today()))
        
        record = cursor.fetchone()
        if record:
            print(f"  ✓ Inserted record for {driver['username']} on {date.today()}")
            print(f"    Status: {record['status']}, Admin Status: {record['admin_status']}")
            cursor.close()
            conn.close()
            return True
        else:
            print("  ✗ Record not found after insert")
            cursor.close()
            conn.close()
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_attendance_query():
    """Test querying attendance records"""
    print("[TEST] Query Attendance Records...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get first driver
        cursor.execute("SELECT id FROM drivers LIMIT 1")
        driver = cursor.fetchone()
        
        if not driver:
            print("  ✗ No drivers found")
            cursor.close()
            conn.close()
            return False
        
        driver_id = driver['id']
        
        # Query today's attendance
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE driver_id = %s AND date = CURDATE()
        ''', (driver_id,))
        today = cursor.fetchone()
        
        # Query attendance history (last 7 days)
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE driver_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            ORDER BY date DESC
        ''', (driver_id,))
        history = cursor.fetchall()
        
        print(f"  ✓ Today's attendance: {'Marked' if today else 'Not marked'}")
        print(f"  ✓ Last 7 days records: {len(history)} records found")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_json_serialization():
    """Test that attendance records can be serialized to JSON"""
    print("[TEST] JSON Serialization...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            LIMIT 5
        ''')
        records = cursor.fetchall()
        
        # Convert date objects to strings for JSON serialization
        json_safe_records = []
        for record in records:
            json_record = dict(record)
            if 'date' in json_record and json_record['date']:
                json_record['date'] = str(json_record['date'])
            if 'approved_at' in json_record and json_record['approved_at']:
                json_record['approved_at'] = str(json_record['approved_at'])
            if 'created_at' in json_record and json_record['created_at']:
                json_record['created_at'] = str(json_record['created_at'])
            json_safe_records.append(json_record)
        
        json_str = json.dumps(json_safe_records)
        print(f"  ✓ Successfully serialized {len(records)} records to JSON")
        print(f"    Sample: {json_str[:100]}...")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("SmartAmbulance - Attendance System Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_database_connection,
        test_attendance_schema,
        test_driver_profile_pic,
        test_attendance_insert,
        test_attendance_query,
        test_json_serialization
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Attendance system is ready.")
    else:
        print(f"✗ {total - passed} test(s) failed.")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
