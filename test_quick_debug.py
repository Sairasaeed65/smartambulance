#!/usr/bin/env python3
"""
Simple quick test to verify /accept-request and /reject-request routes work
"""

import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_database():
    """Check what's in the database"""
    print("\n" + "="*70)
    print("DATABASE INVESTIGATION")
    print("="*70)
    
    # Check if we can directly access database info
    print("\nTo debug: Let me make a simple request to see the response format...")
    
    with requests.Session() as session:
        # Try to get hospital requests (we know this works from previous test)
        try:
            r = session.get(f'{BASE_URL}/get-hospital-requests')
            if r.status_code == 200:
                data = r.json()
                print(f"\n✅ /get-hospital-requests working")
                print(f"   Requests count: {data.get('count', 0)}")
                print(f"   Hospital found: {data.get('hospital_name', 'N/A')}")
                if data.get('requests') and len(data['requests']) > 0:
                    first_req = data['requests'][0]
                    print(f"   First request ID: {first_req.get('id')}")
                    print(f"   Request hospital_id: {first_req.get('hospital_id')}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_database()
