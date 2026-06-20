#!/usr/bin/env python3
import requests
from requests.exceptions import Timeout, ConnectionError
import time

def test_login_flow():
    print('=' * 70)
    print('COMPREHENSIVE HOSPITAL LOGIN FLOW TEST')
    print('=' * 70)
    print()
    
    session = requests.Session()
    BASE_URL = 'http://localhost:5000'
    
    # Test 1: Get login page
    print('[TEST 1] GET /hospital-login')
    try:
        r = session.get(BASE_URL + '/hospital-login', timeout=5)
        print('  Status:', r.status_code)
        print('  Response time:', f'{r.elapsed.total_seconds():.2f}s')
        print('  Has login form:', 'method=' in r.text and 'password' in r.text)
    except Exception as e:
        print('  ERROR:', e)
        return
    print()
    
    # Test 2: Submit login form
    print('[TEST 2] POST /hospital-login with valid credentials')
    try:
        r = session.post(
            BASE_URL + '/hospital-login',
            data={'username': 'hospital1', 'password': 'pass123'},
            allow_redirects=False,
            timeout=5
        )
        print('  Status:', r.status_code)
        print('  Response time:',f'{r.elapsed.total_seconds():.2f}s')
        
        if r.status_code == 302:
            location = r.headers.get('Location', 'N/A')
            print('  Redirect to:', location)
            print('  Session cookies set:', len(session.cookies) > 0)
        elif r.status_code == 200:
            print('  ERROR: Expected redirect (302), got', r.status_code)
            print('  Response contains error:', 'Invalid' in r.text or 'error' in r.text)
        else:
            print('  ERROR: Unexpected status', r.status_code)
    except Exception as e:
        print('  ERROR:', e)
        return
    print()
    
    # Test 3: Access hospital dashboard  
    print('[TEST 3] GET /hospital-dashboard (follow redirect)')
    try:
        print('  Requesting dashboard...')
        start_time = time.time()
        r = session.get(BASE_URL + '/hospital-dashboard', timeout=10)
        elapsed = time.time() - start_time
        
        print('  Status:', r.status_code)
        print('  Response time:', f'{elapsed:.2f}s')
        print('  Response size:', len(r.text), 'bytes')
        
        if r.status_code == 200:
            print('  ✓ Dashboard loaded successfully')
            print('  Has Hospital Dashboard title:', 'Hospital Dashboard' in r.text)
            print('  Has DOMContentLoaded:', 'DOMContentLoaded' in r.text)
            print('  Has refresh functions:', 'refreshDashboardStats' in r.text)
            
            if elapsed > 5:
                print('  WARNING: Dashboard took', f'{elapsed:.2f}s', 'to load (slow)')
        else:
            print('  ERROR: Unexpected status', r.status_code)
    except Timeout:
        print('  TIMEOUT: Dashboard took too long to load (>10s)')
    except Exception as e:
        print('  ERROR:', e)
    
    print()
    print('=' * 70)
    print('TEST COMPLETE')
    print('=' * 70)

if __name__ == '__main__':
    try:
        test_login_flow()
    except Exception as e:
        print('Fatal error:', e)
