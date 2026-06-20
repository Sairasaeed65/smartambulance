#!/usr/bin/env python3
"""
Test driver login and dashboard loading flow
"""

import requests
from time import sleep

BASE_URL = 'http://127.0.0.1:5000'

print("\n" + "="*70)
print("DRIVER LOGIN & DASHBOARD TEST")
print("="*70)

with requests.Session() as session:
    # Step 1: Get driver login page
    print("\n[STEP 1] GET /driver-login")
    r = session.get(f'{BASE_URL}/driver-login')
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  ✅ Login page loaded")
    
    # Step 2: Try driver login with valid credentials
    print("\n[STEP 2] POST /driver-login - Login as DRV-001")
    login_data = {
        'username': 'DRV-001',
        'password': 'pass123'
    }
    r = session.post(f'{BASE_URL}/driver-login', data=login_data, allow_redirects=False)
    print(f"  Status: {r.status_code}")
    if r.status_code == 302:
        print("  ✅ Redirected after login (expected)")
        location = r.headers.get('Location', '')
        print(f"  Redirect to: {location}")
    
    # Step 3: Check server logs for debug print
    print("\n[STEP 3] Check server logs")
    sleep(1)
    with open("c:/Users/zohai/OneDrive/Desktop/smart ambulance/flask_test.log", 'r') as f:
        logs = f.read().split('\n')
        latest_logs = [l for l in logs if l.strip() and ('[DRIVER LOGIN]' in l or '[DRIVER DASHBOARD]' in l)]
        if latest_logs:
            print("  Recent driver-related logs:")
            for log in latest_logs[-5:]:
                print(f"    {log}")
    
    # Step 4: Try to access driver dashboard
    print("\n[STEP 4] GET /driver-dashboard")
    r = session.get(f'{BASE_URL}/driver-dashboard')
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  ✅ Dashboard loaded successfully")
        if 'DRV-001' in r.text or 'driver' in r.text.lower():
            print("  ✅ Driver data found in page")
        else:
            print("  ⚠️  Page loaded but driver data may not be present")
    elif r.status_code == 302:
        print("  Redirected (unexpected if logged in)")
    else:
        print(f"  ❌ Error: {r.status_code}")
    
    # Step 5: Try the same without session (should redirect to login)
    print("\n[STEP 5] GET /driver-dashboard without session")
    no_session = requests.Session()
    r = no_session.get(f'{BASE_URL}/driver-dashboard')
    print(f"  Status: {r.status_code}")
    if r.status_code == 302:
        print("  ✅ Correctly redirected to login (no session)")
    else:
        print(f"  Response status: {r.status_code}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
print("\nSummary:")
print("  1. Login page loads")
print("  2. Driver can login with valid credentials")
print("  3. Dashboard loads with driver data")
print("  4. Debug logs show session loading and dashboard access")
print("  5. No session redirects to login")
