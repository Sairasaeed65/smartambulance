#!/usr/bin/env python3
"""
Test hospital login redirect flow
"""
import requests
import time

# Start a session to maintain cookies
session = requests.Session()

# Test URL
BASE_URL = 'http://localhost:5000'

print("=" * 60)
print("Testing Hospital Login Flow")
print("=" * 60)

# Step 1: Get the login page (should work)
print("\n[STEP 1] Getting hospital login page...")
try:
    r = session.get(f'{BASE_URL}/hospital-login')
    print(f"✓ Status: {r.status_code}")
    if r.status_code == 200:
        print(f"✓ Page loaded successfully")
        if 'Hospital Code' in r.text:
            print(f"✓ Hospital login form found")
    else:
        print(f"✗ Unexpected status code: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Step 2: Test login with POST (should redirect)
print("\n[STEP 2] Attempting hospital login POST...")
try:
    # Test with default hospital credentials
    login_data = {
        'username': 'test_hospital',
        'password': 'password123'
    }
    
    # Use allow_redirects=False to see the actual redirect response
    r = session.post(f'{BASE_URL}/hospital-login', data=login_data, allow_redirects=False)
    print(f"✓ POST response status: {r.status_code}")
    
    if r.status_code == 302:
        redirect_location = r.headers.get('Location')
        print(f"✓ Redirect detected to: {redirect_location}")
        
        # Step 3: Follow the redirect manually
        print("\n[STEP 3] Following redirect to hospital dashboard...")
        redirect_url = redirect_location if redirect_location.startswith('http') else f'{BASE_URL}{redirect_location}'
        r_dashboard = session.get(redirect_url)
        print(f"✓ Dashboard status: {r_dashboard.status_code}")
        
        if r_dashboard.status_code == 200:
            print(f"✓ Dashboard page loaded successfully")
            if '<title>' in r_dashboard.text and 'Hospital Dashboard' in r_dashboard.text:
                print(f"✓ Dashboard HTML contains expected title")
            else:
                print(f"⚠ Warning: Dashboard title not found")
                
            # Check for JavaScript errors
            if 'refreshDashboardStats' in r_dashboard.text:
                print(f"✓ Dashboard functions found in HTML")
            
            # Check for syntax errors in console
            if 'console.error' in r_dashboard.text or 'Uncaught' in r_dashboard.text:
                print(f"⚠ Warning: Potential JavaScript errors detected")
        else:
            print(f"✗ Dashboard returned status {r_dashboard.status_code}")
            
    elif r.status_code == 200:
        print(f"✗ Expected redirect (302) but got 200 - login failed (user not found?)")
    else:
        print(f"✗ Unexpected status code: {r.status_code}")
        
except Exception as e:
    print(f"✗ Error: {e}")

# Step 4: Verify session
print("\n[STEP 4] Checking session data...")
try:
    r = session.get(f'{BASE_URL}/hospital-dashboard')
    print(f"✓ Dashboard access status: {r.status_code}")
    if r.status_code == 200:
        print(f"✓ Session is valid - can access dashboard")
    elif r.status_code == 302:
        print(f"✗ Redirected - session not established or expired")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
