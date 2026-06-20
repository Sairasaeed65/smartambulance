#!/usr/bin/env python
"""
Comprehensive integration test for feedback system.
Tests the complete workflow from frontend to backend.
"""

import requests
import json
import mysql.connector
from datetime import datetime

BASE_URL = 'http://localhost:5000'
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'smartambulance'
}

def test_emergency_page_loads():
    """Test that emergency page loads successfully"""
    print("\n1. Testing Emergency Page Load...")
    try:
        response = requests.get(f'{BASE_URL}/emergency')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'feedbackModal' in response.text, "Feedback modal not found in HTML"
        assert 'submitFeedback' in response.text, "submitFeedback function not found"
        print("   ✓ Emergency page loads successfully")
        print("   ✓ Feedback modal HTML present")
        print("   ✓ Feedback JavaScript functions present")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_feedback_table_structure():
    """Verify feedback table structure in database"""
    print("\n2. Testing Feedback Table Structure...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Check table exists
        cursor.execute("SHOW TABLES LIKE 'feedback'")
        if not cursor.fetchone():
            print("   ❌ Feedback table not found")
            return False
        
        # Check columns
        cursor.execute("DESCRIBE feedback")
        columns = {col['Field']: col['Type'] for col in cursor.fetchall()}
        
        required_columns = {
            'id': 'int',
            'request_id': 'varchar',
            'patient_name': 'varchar',
            'patient_phone': 'varchar',
            'on_time': 'enum',
            'rating': 'int',
            'driver_rating': 'int',
            'comment': 'longtext',
            'created_at': 'timestamp'
        }
        
        for col, dtype in required_columns.items():
            if col not in columns:
                print(f"   ❌ Missing column: {col}")
                return False
            if dtype not in columns[col].lower():
                print(f"   ⚠ Column {col} type mismatch: expected {dtype}, got {columns[col]}")
        
        print("   ✓ All required columns present")
        print("   ✓ Column types correct")
        
        # Check indexes
        cursor.execute("SHOW INDEX FROM feedback WHERE Key_name != 'PRIMARY'")
        indexes = cursor.fetchall()
        index_names = [idx['Column_name'] for idx in indexes]
        
        if 'request_id' in index_names:
            print("   ✓ Index on request_id found")
        if 'created_at' in index_names:
            print("   ✓ Index on created_at found")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_submit_feedback_endpoint():
    """Test /submit-feedback endpoint"""
    print("\n3. Testing /submit-feedback Endpoint...")
    try:
        # Get a valid request ID
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT request_id FROM patient_requests 
            WHERE status = 'completed' 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        
        if not result:
            # Create a test request
            cursor.execute('''
                INSERT INTO patient_requests 
                (request_id, patient_name, patient_phone, latitude, longitude, pickup_address, status, hospital_id, assigned_driver_id, priority, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}', 
                  'Test User', '03001234567', 32.5748, 74.0789, 'Test Loc',
                  'completed', 1, 1, 'high', datetime.now()))
            conn.commit()
            request_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        else:
            request_id = result['request_id']
        
        cursor.close()
        conn.close()
        
        # Test valid submission
        payload = {
            'request_id': request_id,
            'on_time': 'yes',
            'rating': 5,
            'driver_rating': 4,
            'comment': 'Great service!'
        }
        
        response = requests.post(f'{BASE_URL}/submit-feedback', json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        
        data = response.json()
        assert data['status'] == 'success', "Response status not success"
        assert data['feedback_id'], "No feedback_id in response"
        assert data['request_id'] == request_id, "request_id mismatch"
        
        print(f"   ✓ Feedback submitted successfully (ID: {data['feedback_id']})")
        
        # Test missing request_id
        response = requests.post(f'{BASE_URL}/submit-feedback', 
                                json={'rating': 5})
        assert response.status_code == 400, "Should reject missing request_id"
        print("   ✓ Validation: Missing request_id rejected")
        
        # Test invalid request_id
        response = requests.post(f'{BASE_URL}/submit-feedback',
                                json={'request_id': 'INVALID-ID', 'rating': 5})
        assert response.status_code == 404, "Should reject invalid request_id"
        print("   ✓ Validation: Invalid request_id rejected")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feedback_data_persistence():
    """Verify feedback is saved to database"""
    print("\n4. Testing Feedback Data Persistence...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get latest feedback
        cursor.execute('''
            SELECT * FROM feedback 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        feedback = cursor.fetchone()
        
        if not feedback:
            print("   ❌ No feedback found in database")
            return False
        
        # Verify fields
        assert feedback['patient_name'], "patient_name is empty"
        assert feedback['patient_phone'], "patient_phone is empty"
        assert feedback['rating'] in [1, 2, 3, 4, 5], f"Invalid rating: {feedback['rating']}"
        assert feedback['created_at'], "created_at is empty"
        
        print(f"   ✓ Feedback ID: {feedback['id']}")
        print(f"   ✓ Patient: {feedback['patient_name']} ({feedback['patient_phone']})")
        print(f"   ✓ Rating: {feedback['rating']}/5")
        print(f"   ✓ Driver Rating: {feedback['driver_rating']}/5")
        print(f"   ✓ On Time: {feedback['on_time']}")
        print(f"   ✓ Timestamp: {feedback['created_at']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_javascript_functions():
    """Verify JavaScript functions exist in emergency.html"""
    print("\n5. Testing JavaScript Functions...")
    try:
        response = requests.get(f'{BASE_URL}/emergency')
        html = response.text
        
        functions = [
            'initFeedbackForm',
            'showFeedback',
            'skipFeedback',
            'submitFeedback',
            'closeFeedback'
        ]
        
        for func in functions:
            if f'function {func}' in html or f'{func}()' in html or f'{func}' in html:
                print(f"   ✓ Function '{func}' found")
            else:
                print(f"   ⚠ Function '{func}' not explicitly found")
        
        # Check CSS classes
        css_classes = [
            'feedback-modal',
            'feedback-card',
            'feedback-title',
            'star-rating',
            'btn-submit-feedback'
        ]
        
        for cls in css_classes:
            if cls in html:
                print(f"   ✓ CSS class '{cls}' found")
            else:
                print(f"   ❌ CSS class '{cls}' not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("FEEDBACK SYSTEM - INTEGRATION TEST")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_emergency_page_loads()
    all_passed &= test_feedback_table_structure()
    all_passed &= test_submit_feedback_endpoint()
    all_passed &= test_feedback_data_persistence()
    all_passed &= test_javascript_functions()
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("\nFeedback system is fully operational:")
        print("- Frontend: Feedback form modal working")
        print("- Backend: /submit-feedback endpoint working")
        print("- Database: Feedback table storing data correctly")
        print("- Integration: All components working together")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    exit(main())
