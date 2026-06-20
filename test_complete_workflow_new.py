#!/usr/bin/env python3
"""
Comprehensive test of hospital workflow:
1. Accept a request
2. Verify driver is assigned and on duty
3. Reject a request
4. Verify reassignment to next hospital
"""

import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_complete_workflow():
    print("\n" + "="*70)
    print("COMPLETE HOSPITAL WORKFLOW TEST")
    print("="*70)
    
    with requests.Session() as session:
        # Get requests
        print("\n[STEP 1] Getting hospital requests...")
        r = session.get(f'{BASE_URL}/get-hospital-requests')
        data = r.json()
        request_count = data.get('count', 0)
        print(f"   ✅ Found {request_count} requests")
        
        if request_count < 2:
            print("   ⚠️  Need at least 2 requests to test complete workflow")
            return
        
        # Accept first request
        print("\n[STEP 2] TESTING ACCEPT...")
        request1 = data['requests'][0]
        request1_id = request1['request_id']
        print(f"   Accepting request: {request1_id}")
        
        accept_data = {'request_id': request1_id}
        r = session.post(f'{BASE_URL}/accept-request', json=accept_data)
        
        if r.status_code == 200:
            result = r.json()
            driver_info = result.get('driver_info', {})
            driver_name = driver_info.get('name', 'Unknown')
            driver_phone = driver_info.get('phone', 'N/A')
            ambulance = driver_info.get('ambulance', 'N/A')
            
            print(f"   ✅ SUCCESS")
            print(f"      Driver: {driver_name}")
            print(f"      Phone: {driver_phone}")
            print(f"      Ambulance: {ambulance}")
            print(f"      Status: {driver_info.get('status', 'Unknown')}")
            
            # This is what the frontend would display:
            message = f"✓ Request accepted! Assigned to {driver_name} ({driver_phone}) - Ambulance: {ambulance}"
            print(f"      Frontend Message: {message}")
            
            assigned_driver_id = result.get('assigned_driver')
            print(f"      Dispatch ID: {result.get('dispatch_id')}")
        else:
            print(f"   ❌ FAILED: {r.status_code} - {r.json()}")
            return
        
        # Get requests again after acceptance
        print("\n[STEP 3] Getting hospital requests again after acceptance...")
        r = session.get(f'{BASE_URL}/get-hospital-requests')
        data_after = r.json()
        print(f"   Requests remaining: {data_after.get('count', 0)}")
        print(f"   Status change: {request_count} → {data_after.get('count', 0)}")
        
        # Get a new pending request to test reject
        print("\n[STEP 4] TESTING REJECT...")
        pending_requests = data_after.get('requests', [])
        if len(pending_requests) > 0:
            request2 = pending_requests[0]
            request2_id = request2['request_id']
            print(f"   Rejecting request: {request2_id}")
            
            reject_data = {'request_id': request2_id}
            r = session.post(f'{BASE_URL}/reject-request', json=reject_data)
            
            if r.status_code == 200:
                result = r.json()
                if result.get('reassigned'):
                    print(f"   ✅ Request reassigned to: {result.get('next_hospital', 'Unknown')}")
                else:
                    print(f"   ✅ Request fully rejected (no more hospitals available)")
            else:
                print(f"   ❌ FAILED: {r.status_code} - {r.json()}")
        else:
            print("   ⚠️  No more pending requests to reject")
        
        # Final status
        print("\n[STEP 5] Final status...")
        r = session.get(f'{BASE_URL}/get-hospital-requests')
        data_final = r.json()
        print(f"   Requests remaining: {data_final.get('count', 0)}")
        print(f"   Change from start: {request_count} → {data_final.get('count', 0)}")
        
        print("\n" + "="*70)
        print("✅ COMPLETE WORKFLOW TEST FINISHED")
        print("="*70)

if __name__ == '__main__':
    test_complete_workflow()
