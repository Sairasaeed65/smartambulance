#!/usr/bin/env python3
"""
Test script to verify request is fully rejected when all hospitals reject it
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def test_full_rejection():
    """Test that request is fully rejected when all hospitals reject it"""
    
    print('\n' + '='*60)
    print('  TESTING FULL REJECTION WHEN ALL HOSPITALS REJECT')
    print('='*60 + '\n')
    
    # First check REQ-001 status 
    print('[1] Checking REQ-001 status (should be at Metro Medical Center now)...')
    session = requests.Session()
    
    # Login to hospital2 (Metro Medical Center)
    login_data = {'username': 'hospital2', 'password': 'pass123'}
    response = session.post(f'{BASE_URL}/hospital-login', data=login_data)
    print('    ✓ Logged in to hospital2')
    
    # Get hospital requests
    response = session.get(f'{BASE_URL}/get-hospital-requests')
    if response.status_code == 200:
        data = response.json()
        requests_list = data.get('requests', [])
        
        # Find REQ-001
        req_001 = None
        for req in requests_list:
            if req.get('id') == 'REQ-001':
                req_001 = req
                break
        
        if req_001:
            print(f'    ✓ Found REQ-001 at hospital2')
            print(f'    Current hospital: {req_001["hospital"]}')
            print(f'    Status: {req_001["status"]}')
            print(f'    Rejected by: {req_001.get("rejected_by", [])}')
            
            # Now hospital2 rejects it
            print(f'\n[2] Hospital2 (Metro Medical Center) rejecting REQ-001...')
            reject_data = {'request_id': req_001['id']}
            response = session.post(f'{BASE_URL}/reject-request', json=reject_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f'    Status: {result.get("status")}')
                print(f'    Message: {result.get("message")}')
                print(f'    Reassigned: {result.get("reassigned")}')
                
                updated_req = result.get('request', {})
                print(f'    Request status after rejection: {updated_req.get("status")}')
                print(f'    Rejected by all hospitals: {updated_req.get("rejected_by", [])}')
                
                if not result.get('reassigned'):
                    print('\n    ✓ Request fully rejected - no other hospitals available!')
                else:
                    print(f'\n    Request reassigned to: {result.get("next_hospital")}')
            else:
                print(f'    Error: {response.status_code}')
        else:
            print('    REQ-001 not found at hospital2')
    
    print('\n' + '='*60)
    print('  TEST COMPLETE')
    print('='*60 + '\n')

if __name__ == '__main__':
    time.sleep(1)
    try:
        test_full_rejection()
    except Exception as e:
        print(f'Error: {e}')
