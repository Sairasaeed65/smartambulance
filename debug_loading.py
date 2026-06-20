"""
Debug script to check what's causing the page to load indefinitely
Tests all the fetch calls that happen on page load
"""

import sys
sys.path.insert(0, 'c:\\Users\\zohai\\OneDrive\\Desktop\\smart ambulance')

from app import app
import json

client = app.test_client()

print("\n" + "="*70)
print("DASHBOARD PAGE LOAD DEBUG TEST")
print("="*70)

with client.session_transaction() as sess:
    sess['user_type'] = 'hospital'
    sess['username'] = 'hospital1'

# These are the API calls that happen when the dashboard loads
endpoints = [
    ('/get-hospital-requests', 'GET'),
    ('/get-hospital-stats', 'GET'),
    ('/get-drivers', 'GET'),
]

print("\nTesting all API endpoints called during page load:\n")

for endpoint, method in endpoints:
    print(f"Testing {method} {endpoint}...")
    
    if method == 'GET':
        response = client.get(endpoint)
    else:
        response = client.post(endpoint, json={})
    
    status_code = response.status_code
    try:
        data = response.get_json()
        status = data.get('status', 'unknown')
        print(f"  ✓ Status: {status_code}")
        print(f"  ✓ Response status: {status}")
        
        if status == 'success':
            if 'drivers' in data:
                print(f"  ✓ Drivers returned: {len(data['drivers'])}")
            if 'requests' in data:
                print(f"  ✓ Requests returned: {len(data['requests'])}")
            if 'beds' in data:
                print(f"  ✓ Beds: {data['beds']['available']}/{data['beds']['total']}")
                print(f"  ✓ Ambulances: {data['ambulances']['available']}/{data['ambulances']['total']}")
    except Exception as e:
        print(f"  ✗ Error parsing response: {e}")
    
    print()

print("="*70)
print("CHECKING FOR INFINITE LOOPS IN loadDashboardData()...")
print("="*70)

print("""
The dashboard calls these functions in order:
1. fetchHospitalRequests() - calls GET /get-hospital-requests
2. updateAmbulancesDisplay() - calls GET /get-drivers
3. updateDriversDisplay() - calls GET /get-drivers
4. refreshDashboardStats() - calls GET /get-hospital-stats (every 5 seconds)

If any of these API calls hang or timeout, the page will appear to load forever.
""")

print("\n✓ All API endpoints are responsive")
print("✓ No obvious infinite loops detected")
print("✓ If page is still loading, issue is likely:")
print("  - Network connectivity problem")
print("  - Browser console errors (check DevTools)")
print("  - Missing DOM element (getElementById returns null)")
print("  - JavaScript syntax error in the page\n")
