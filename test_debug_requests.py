#!/usr/bin/env python3
"""
Debug test to understand hospital requests structure
"""

import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_requests_structure():
    print("\n" + "="*70)
    print("HOSPITAL REQUESTS DEBUG")
    print("="*70)
    
    with requests.Session() as session:
        # Get hospital requests
        print("\n[STEP 1] Getting hospital requests...")
        try:
            r = session.get(f'{BASE_URL}/get-hospital-requests')
            data = r.json()
            print(f"   Status: {r.status_code}")
            print(f"   Requests count: {data.get('count', 0)}")
            
            if data.get('requests') and len(data['requests']) > 0:
                first_req = data['requests'][0]
                print(f"\n   First request details:")
                for key, value in first_req.items():
                    if not isinstance(value, (dict, list)):
                        print(f"      {key}: {value}")
                    else:
                        print(f"     {key}: {type(value).__name__}")
                
                # Try accepting this request
                request_id = first_req.get('request_id')  # Use request_id, not id
                print(f"\n[STEP 2] Attempting to accept request {request_id}...")
                accept_data = {'request_id': request_id}
                
                r = session.post(f'{BASE_URL}/accept-request', json=accept_data)
                print(f"   Response status: {r.status_code}")
                try:
                    result = r.json()
                    print(f"   Response: {json.dumps(result, indent=2)}")
                except:
                    print(f"   Response text: {r.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_requests_structure()
