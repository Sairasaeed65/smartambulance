#!/usr/bin/env python3
"""Test the new comprehensive attendance UI system"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000'
SESSION = requests.Session()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_result(test_name, success, details=''):
    status = f'{GREEN}✓ PASS{RESET}' if success else f'{RED}✗ FAIL{RESET}'
    print(f'{status} | {test_name}')
    if details:
        print(f'       {details}')

def test_driver_login():
    """Test driver login"""
    print('\n=== DRIVER LOGIN ===')
    
    login_data = {
        'username': 'driver1',
        'password': 'driver123'
    }
    
    response = SESSION.post(f'{BASE_URL}/driver-login', data=login_data)
    success = response.status_code in [200, 302]
    print_result('POST /driver-login', success, f'Status: {response.status_code}')
    
    return success

def test_get_dashboard_with_attendance():
    """Test getting driver dashboard with attendance data"""
    print('\n=== GET DASHBOARD WITH ATTENDANCE ===')
    
    response = SESSION.get(f'{BASE_URL}/driver-dashboard')
    success = response.status_code == 200
    
    if success:
        # Check if attendance data is in HTML
        has_attendance_section = 'section-attendance' in response.text
        has_stat_cards = 'statPresent' in response.text and 'statLeave' in response.text
        has_calendar = 'calendarGrid' in response.text
        has_modals = 'markAttendanceModal' in response.text and 'leaveReasonModal' in response.text
        
        all_elements = has_attendance_section and has_stat_cards and has_calendar and has_modals
        
        print_result('GET /driver-dashboard', all_elements, 
                    f'Attendance: {has_attendance_section}, Stats: {has_stat_cards}, ' +
                    f'Calendar: {has_calendar}, Modals: {has_modals}')
        return all_elements
    else:
        print_result('GET /driver-dashboard', False, f'Status: {response.status_code}')
        return False

def test_mark_attendance_present():
    """Test marking attendance as present"""
    print('\n=== MARK ATTENDANCE PRESENT ===')
    
    data = {
        'status': 'Present'
    }
    
    response = SESSION.post(f'{BASE_URL}/mark-attendance', 
                           json=data,
                           headers={'Content-Type': 'application/json'})
    
    success = response.status_code == 200
    
    if success:
        try:
            result = response.json()
            is_success = result.get('status') == 'success'
            print_result('POST /mark-attendance (Present)', is_success, 
                        f'Response: {result.get("message")}')
            return is_success
        except:
            print_result('POST /mark-attendance (Present)', False, 'Invalid JSON response')
            return False
    else:
        print_result('POST /mark-attendance (Present)', False, f'Status: {response.status_code}')
        return False

def test_mark_attendance_leave():
    """Test requesting leave with reason"""
    print('\n=== MARK ATTENDANCE LEAVE ===')
    
    data = {
        'status': 'On Leave',
        'leave_reason': 'Medical appointment scheduled'
    }
    
    response = SESSION.post(f'{BASE_URL}/mark-attendance', 
                           json=data,
                           headers={'Content-Type': 'application/json'})
    
    success = response.status_code == 200
    
    if success:
        try:
            result = response.json()
            is_success = result.get('status') == 'success'
            print_result('POST /mark-attendance (Leave)', is_success, 
                        f'Response: {result.get("message")}')
            return is_success
        except:
            print_result('POST /mark-attendance (Leave)', False, 'Invalid JSON response')
            return False
    else:
        print_result('POST /mark-attendance (Leave)', False, f'Status: {response.status_code}')
        return False

def test_invalid_leave_reason():
    """Test validation of short leave reason"""
    print('\n=== VALIDATION: SHORT LEAVE REASON ===')
    
    data = {
        'status': 'On Leave',
        'leave_reason': 'Sick'  # Less than 10 characters
    }
    
    response = SESSION.post(f'{BASE_URL}/mark-attendance', 
                           json=data,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        try:
            result = response.json()
            is_error = result.get('status') == 'error'
            print_result('Reject Short Leave Reason', is_error, 
                        f'Response: {result.get("message")}')
            return is_error
        except:
            print_result('Reject Short Leave Reason', False, 'Invalid JSON response')
            return False
    else:
        print_result('Reject Short Leave Reason', response.status_code == 400, 
                    f'Status: {response.status_code}')
        return response.status_code == 400

def main():
    print(f'{YELLOW}=== New Attendance UI Test Suite ==={RESET}')
    print(f'{YELLOW}Base URL: {BASE_URL}{RESET}')
    
    # Run tests
    results = []
    
    # Step 1: Login
    if test_driver_login():
        # Step 2: Get dashboard with attendance data
        results.append(('Dashboard Load', test_get_dashboard_with_attendance()))
        
        # Step 3: Test marking attendance
        results.append(('Mark Present', test_mark_attendance_present()))
        
        # Step 4: Test leave request validation
        results.append(('Leave Validation', test_invalid_leave_reason()))
        
        # Step 5: Test valid leave request
        results.append(('Mark Leave', test_mark_attendance_leave()))
    else:
        print(f'{RED}Login failed - cannot continue tests{RESET}')
        return
    
    # Summary
    print(f'\n{YELLOW}=== TEST SUMMARY ==={RESET}')
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f'Passed: {passed}/{total}')
    
    for test_name, result in results:
        status = f'{GREEN}✓{RESET}' if result else f'{RED}✗{RESET}'
        print(f'{status} {test_name}')
    
    if passed == total:
        print(f'\n{GREEN}ALL TESTS PASSED!{RESET}')
    else:
        print(f'\n{RED}SOME TESTS FAILED!{RESET}')

if __name__ == '__main__':
    main()
