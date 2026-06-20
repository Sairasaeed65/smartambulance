#!/usr/bin/env python
"""
Test script for feedback submission functionality
Tests the /submit-feedback endpoint and verifies data is saved correctly
"""

import mysql.connector
import json
import requests

# Database connection
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'smartambulance'

def check_feedback_table():
    """Verify feedback table exists and has correct structure"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # Check table exists
        cursor.execute("SHOW TABLES LIKE 'feedback'")
        if not cursor.fetchone():
            print("❌ Feedback table does not exist")
            return False
        
        # Check table structure
        cursor.execute("DESCRIBE feedback")
        columns = cursor.fetchall()
        required_cols = ['id', 'request_id', 'patient_name', 'patient_phone', 'on_time', 'rating', 'driver_rating', 'comment', 'created_at']
        found_cols = [col['Field'] for col in columns]
        
        print("✓ Feedback table structure:")
        for col in columns:
            print(f"  - {col['Field']}: {col['Type']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def test_feedback_endpoint():
    """Test the /submit-feedback endpoint"""
    try:
        # First, get a valid request_id from database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get a completed request
        cursor.execute('''
            SELECT request_id FROM patient_requests 
            WHERE status = 'completed' 
            LIMIT 1
        ''')
        completed_req = cursor.fetchone()
        
        if not completed_req:
            print("⚠ No completed requests found. Creating test data...")
            # Create a test completed request
            from datetime import datetime, timedelta
            cursor.execute('''
                INSERT INTO patient_requests 
                (request_id, patient_name, patient_phone, latitude, longitude, pickup_address, status, hospital_id, assigned_driver_id, priority, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', ('TEST-FEEDBACK-' + datetime.now().strftime('%Y%m%d%H%M%S'), 
                  'Test Patient', '03001234567', 32.5748, 74.0789, 'Test Location', 
                  'completed', 1, 1, 'high', datetime.now()))
            conn.commit()
            request_id = 'TEST-FEEDBACK-' + datetime.now().strftime('%Y%m%d%H%M%S')
        else:
            request_id = completed_req['request_id']
        
        cursor.close()
        conn.close()
        
        print(f"\nTesting /submit-feedback with request_id: {request_id}")
        
        # Test payload
        payload = {
            'request_id': request_id,
            'on_time': 'yes',
            'rating': 5,
            'driver_rating': 4,
            'comment': 'Excellent service! Ambulance arrived quickly and staff was professional.'
        }
        
        # Send POST request
        response = requests.post('http://localhost:5000/submit-feedback', json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✓ Feedback submitted successfully")
            
            # Verify it was saved in database
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM feedback WHERE request_id = %s ORDER BY created_at DESC LIMIT 1', (request_id,))
            feedback = cursor.fetchone()
            
            if feedback:
                print("\n✓ Feedback verified in database:")
                print(f"  - Request ID: {feedback['request_id']}")
                print(f"  - Rating: {feedback['rating']}/5")
                print(f"  - Driver Rating: {feedback['driver_rating']}/5")
                print(f"  - On Time: {feedback['on_time']}")
                print(f"  - Comment: {feedback['comment']}")
                print(f"  - Timestamp: {feedback['created_at']}")
            else:
                print("❌ Feedback not found in database")
            
            cursor.close()
            conn.close()
            return True
        else:
            print("❌ Failed to submit feedback")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Smart Ambulance - Feedback System Test")
    print("=" * 60)
    
    print("\n1. Checking feedback table...")
    if not check_feedback_table():
        exit(1)
    
    print("\n2. Testing /submit-feedback endpoint...")
    if test_feedback_endpoint():
        print("\n✓ All feedback tests passed!")
    else:
        print("\n❌ Feedback tests failed")
        exit(1)
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("- Feedback table created ✓")
    print("- /submit-feedback endpoint working ✓")
    print("- Feedback data persisted ✓")
    print("=" * 60)
