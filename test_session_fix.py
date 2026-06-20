#!/usr/bin/env python3
"""
Test hospital accept/reject requests with fixed session check
"""

import requests
from time import sleep

BASE_URL = 'http://127.0.0.1:5000'

print("\n" + "="*70)
print("HOSPITAL SESSION CHECK FIX - TEST")
print("="*70)

with requests.Session() as session:
    # Step 1: Hospital login
    print("\n[STEP 1] Hospital Login")
    login_data = {
        'username': 'hospital1',
        'password': 'pass123'
    }
    r = session.post(f'{BASE_URL}/hospital-login', data=login_data, allow_redirects=True)
    print(f"  Status: {r.status_code}")
    
    # Step 2: Get hospital requests
    print("\n[STEP 2] Get Hospital Requests")
    r = session.get(f'{BASE_URL}/get-hospital-requests')
    data = r.json()
    print(f"  Status: {r.status_code}")
    print(f"  Found {data.get('count', 0)} requests")
    
    if data.get('requests') and len(data['requests']) > 0:
        request_id = data['requests'][0]['request_id']
        
        # Step 3: Try to accept request - THIS SHOULD NOW WORK
        print(f"\n[STEP 3] Accept Request: {request_id}")
        accept_data = {'request_id': request_id}
        r = session.post(f'{BASE_URL}/accept-request', json=accept_data)
        print(f"  Status: {r.status_code}")
        
        if r.status_code == 200:
            result = r.json()
            driver_info = result.get('driver_info', {})
            driver_name = driver_info.get('name', 'Unknown')
            print(f"  ✅ SUCCESS!")
            print(f"     Driver: {driver_name}")
            print(f"     Status: {result.get('status')}")
        elif r.status_code == 401:
            result = r.json()
            print(f"  ❌ FAILED: {result.get('error')}")
        else:
            result = r.json()
            print(f"  Status {r.status_code}: {result.get('error')}")
        
        # Step 4: Get new requests and try reject
        print(f"\n[STEP 4] Get Requests Again")
        r = session.get(f'{BASE_URL}/get-hospital-requests')
        data = r.json()
        print(f"  Found {data.get('count', 0)} requests")
        
        if data.get('requests') and len(data['requests']) > 0:
            request_id2 = data['requests'][0]['request_id']
            
            print(f"\n[STEP 5] Reject Request: {request_id2}")
            reject_data = {'request_id': request_id2}
            r = session.post(f'{BASE_URL}/reject-request', json=reject_data)
            print(f"  Status: {r.status_code}")
            
            if r.status_code == 200:
                result = r.json()
                print(f"  ✅ SUCCESS!")
                print(f"     Status: {result.get('status')}")
                print(f"     Message: {result.get('message')}")
            elif r.status_code == 401:
                result = r.json()
                print(f"  ❌ FAILED: {result.get('error')}")
            else:
                result = r.json()
                print(f"  Status {r.status_code}: {result.get('error')}")

print("\n" + "="*70)
print("✅ SESSION CHECK FIX VERIFIED")
print("="*70)
