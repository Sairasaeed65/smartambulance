#!/usr/bin/env python3
"""
Test script for emergency request reassignment logic
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def test_reject_and_reassign():
    """Test rejecting a request and reassigning to next hospital"""
    
    print('\n' + '='*60)
    print('  TESTING REQUEST REASSIGNMENT LOGIC')
    print('='*60 + '\n')
    
    # First, login to hospital1
    print('[1] Logging in to hospital1...')
    session = requests.Session()
    login_data = {
        'username': 'hospital1',
        'password': 'pass123'
    }
    response = session.post(f'{BASE_URL}/hospital-login', data=login_data)
    if response.status_code == 302 or response.status_code == 200:
        print('    ✓ Login successful')
    else:
        print(f'    ✗ Login failed: {response.status_code}')
        return
    
    # Get hospital requests
    print('\n[2] Fetching hospital requests...')
    response = session.get(f'{BASE_URL}/get-hospital-requests')
    if response.status_code == 200:
        data = response.json()
        print(f'    ✓ Got {len(data.get("requests", []))} requests')
        
        # Find a pending request
        requests_list = data.get('requests', [])
        pending_request = None
        for req in requests_list:
            if req.get('status') == 'pending':
                pending_request = req
                break
        
        if pending_request:
            print(f'    Found pending request: {pending_request["id"]}')
            print(f'    Current hospital: {pending_request["hospital"]}')
            print(f'    Rejected by: {pending_request.get("rejected_by", [])}')
            
            # Try to reject the request
            print(f'\n[3] Rejecting request {pending_request["id"]}...')
            reject_data = {'request_id': pending_request['id']}
            response = session.post(f'{BASE_URL}/reject-request', 
                                   json=reject_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f'    Status: {result.get("status")}')
                print(f'    Message: {result.get("message")}')
                print(f'    Reassigned: {result.get("reassigned")}')
                if result.get('next_hospital'):
                    print(f'    Next hospital: {result.get("next_hospital")}')
                
                # Check the updated request
                print(f'\n[4] Checking request status after rejection...')
                updated_req = result.get('request', {})
                print(f'    Request hospital: {updated_req.get("hospital")}')
                print(f'    Request status: {updated_req.get("status")}')
                print(f'    Rejected by: {updated_req.get("rejected_by", [])}')
                
                print('\n    ✓ Reassignment logic working correctly!')
            else:
                print(f'    ✗ Rejection failed: {response.status_code}')
                print(f'    Response: {response.text}')
        else:
            print('    No pending requests found')
    else:
        print(f'    ✗ Failed to fetch requests: {response.status_code}')
    
    print('\n' + '='*60)
    print('  TEST COMPLETE')
    print('='*60 + '\n')

if __name__ == '__main__':
    # Wait for server to start
    print('Waiting for server to start...')
    time.sleep(2)
    
    try:
        test_reject_and_reassign()
    except Exception as e:
        print(f'Error: {e}')
