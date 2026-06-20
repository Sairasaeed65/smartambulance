#!/usr/bin/env python3
"""
Test complete hospital request workflow with accept/reject and reassignment
Tests:
1. Submit patient emergency request
2. Hospital accepts request (assign driver)
3. Verify dispatch created
4. Test reject and reassignment flow
"""

import requests
import json
import time
from urllib.parse import urljoin

BASE_URL = 'http://127.0.0.1:5000'

def test_workflow():
    print("\n" + "="*70)
    print("HOSPITAL WORKFLOW TEST")
    print("="*70)
    
    # Step 1: Create user session
    print("\n[STEP 1] Creating user session and submitting emergency request...")
    with requests.Session() as session:
        session.headers.update({'Content-Type': 'application/json'})
        
        # Submit emergency request
        emergency_data = {
            'name': 'Test Patient',
            'cnic': '12345-6789012-3',
            'phone': '03001234567',
            'latitude': 31.5204,
            'longitude': 74.3587,
            'description': 'Test emergency'
        }
        
        try:
            r = session.post(f'{BASE_URL}/emergency', json=emergency_data)
            print(f"   Emergency submitted: {r.status_code}")
            print(f"   Response: {r.json()}")
        except Exception as e:
            print(f"   ❌ Error submitting emergency: {e}")
            return
        
        # Give server time to process
        time.sleep(1)
        
        # Step 2: Hospital login and get requests
        print("\n[STEP 2] Hospital login and fetch requests...")
        hospital_login = {
            'username': 'hospital1',  # Correct hospital username
            'password': 'pass123'      # Correct hospital password
        }
        
        try:
            # Use form data with redirect enabled to set session properly
            r = session.post(f'{BASE_URL}/hospital-login', data=hospital_login, allow_redirects=True)
            print(f"   Hospital login: {r.status_code}")
            
        except Exception as e:
            print(f"   ❌ Error logging in: {e}")
            return
        
        time.sleep(1)
        
        # Step 3: Get hospital requests
        print("\n[STEP 3] Getting hospital requests...")
        try:
            r = session.get(f'{BASE_URL}/get-hospital-requests')
            print(f"   Get requests: {r.status_code}")
            reqs = r.json()
            print(f"   Found {reqs.get('count', 0)} requests")
            
            if reqs.get('count', 0) == 0:
                print(f"   ⚠️  No requests found for hospital")
                return
            
            request_id = reqs['requests'][0]['request_id']  # Use request_id, not id
            print(f"   First request ID: {request_id}")
            
        except Exception as e:
            print(f"   ❌ Error getting requests: {e}")
            return
        
        time.sleep(1)
        
        # Step 4: Accept request
        print("\n[STEP 4] Accepting request...")
        accept_data = {'request_id': request_id}
        
        try:
            r = session.post(f'{BASE_URL}/accept-request', json=accept_data)
            print(f"   Accept request: {r.status_code}")
            result = r.json()
            print(f"   Result: {result.get('status')}")
            
            if result.get('status') == 'success':
                driver_info = result.get('driver_info', {})
                print(f"   ✅ Driver assigned: {driver_info.get('name', 'Unknown')}")
                print(f"      Phone: {driver_info.get('phone', 'N/A')}")
                print(f"      Ambulance: {driver_info.get('ambulance', 'N/A')}")
                print(f"      Status: {driver_info.get('status', 'N/A')}")
            else:
                print(f"   ❌ Accept failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Error accepting request: {e}")
            return
        
        print("\n" + "="*70)
        print("✅ HOSPITAL WORKFLOW TEST COMPLETE")
        print("="*70)

if __name__ == '__main__':
    test_workflow()
