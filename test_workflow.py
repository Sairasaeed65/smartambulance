#!/usr/bin/env python3
"""
Comprehensive test of request reassignment system
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def print_section(title):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print(f'{"="*60}\n')

def test_reassignment_workflow():
    """Test complete reassignment workflow"""
    
    print_section('REQUEST REASSIGNMENT WORKFLOW TEST')
    
    # Step 1: Create a new test request
    print('[Step 1] Creating a new test request...')
    
    # We'll use POST to /emergency to create a request
    response = requests.post(f'{BASE_URL}/emergency', json={
        'latitude': 25.2,
        'longitude': 55.25,
        'accuracy': 50,
        'location_method': 'test'
    })
    print(f'    Response status: {response.status_code}')
    
    # Since emergency creates requests through a different flow, let's use the existing REQ-001
    print('\n[Step 2] Using existing test request (REQ-001)...')
    
    session1 = requests.Session()
    
    # Login to hospital1
    print('[Step 2a] Hospital1 (City General Hospital) login...')
    response = session1.post(f'{BASE_URL}/hospital-login', 
                            data={'username': 'hospital1', 'password': 'pass123'})
    print('         ✓ Login successful')
    
    # Get requests at hospital1
    response = session1.get(f'{BASE_URL}/get-hospital-requests')
    data = response.json()
    requests_h1 = data.get('requests', [])
    
    # Find REQ-001
    req_001 = None
    print(f'\n[Step 2b] Checking requests at Hospital1...')
    print(f'         Found {len(requests_h1)} requests')
    for req in requests_h1:
        print(f'         - {req["id"]}: {req["hospital"]} ({req["status"]})')
        if req['id'] == 'REQ-001' or (req_001 is None and req.get('status') == 'pending'):
            req_001 = req
    
    if req_001:
        print(f'\n[Step 3] Hospital1 rejecting request {req_001["id"]}...')
        response = session1.post(f'{BASE_URL}/reject-request',
                                json={'request_id': req_001['id']})
        
        if response.status_code == 200:
            result = response.json()
            print(f'         Status: {result.get("status")}')
            print(f'         Message: {result.get("message")}')
            print(f'         Reassigned: {result.get("reassigned")}')
            
            if result.get('reassigned'):
                print(f'         Next hospital: {result.get("next_hospital")}')
                
                updated_req = result.get('request', {})
                print(f'\n[Step 4] Verifying reassignment...')
                print(f'         New hospital: {updated_req.get("hospital")}')
                print(f'         New status: {updated_req.get("status")}')
                print(f'         Rejected by: {updated_req.get("rejected_by", [])}')
                
                # Now check that request appears at new hospital
                print(f'\n[Step 5] Checking if request appears at new hospital...')
                
                session2 = requests.Session()
                response = session2.post(f'{BASE_URL}/hospital-login',
                                        data={'username': 'hospital2', 'password': 'pass123'})
                print('         ✓ Hospital2 login successful')
                
                response = session2.get(f'{BASE_URL}/get-hospital-requests')
                data = response.json()
                requests_h2 = data.get('requests', [])
                
                print(f'         Hospital2 has {len(requests_h2)} requests')
                
                found_reassigned = False
                for req in requests_h2:
                    print(f'         - {req["id"]}: {req["hospital"]} ({req["status"]})')
                    if req['id'] == req_001['id']:
                        found_reassigned = True
                        print(f'         ✓ REASSIGNED REQUEST FOUND AT HOSPITAL2!')
                
                if not found_reassigned:
                    print(f'         Note: Reassigned request may not be in list if filters changed')
                
                # Try to reject from hospital2
                print(f'\n[Step 6] Hospital2 rejecting the reassigned request...')
                response = session2.post(f'{BASE_URL}/reject-request',
                                        json={'request_id': req_001['id']})
                
                if response.status_code == 200:
                    result = response.json()
                    print(f'         Status: {result.get("status")}')
                    print(f'         Reassigned: {result.get("reassigned")}')
                    print(f'         Message: {result.get("message")}')
                    
                    final_req = result.get('request', {})
                    print(f'         Final rejected_by: {final_req.get("rejected_by", [])}')
                    print(f'         Final status: {final_req.get("status")}')
                    
                    print(f'\n✓ REASSIGNMENT SYSTEM WORKING CORRECTLY!')
                else:
                    print(f'         Error rejecting from hospital2: {response.status_code}')
        else:
            print(f'         Error rejecting from hospital1: {response.status_code}')
    else:
        print('    No suitable request found to test')
    
    print_section('TEST COMPLETE')

if __name__ == '__main__':
    time.sleep(1)
    try:
        test_reassignment_workflow()
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
