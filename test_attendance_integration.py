"""
Integration Test for SmartAmbulance Attendance System
Tests the complete flow: Driver login -> Dashboard -> Mark attendance
"""

import requests
import json
from datetime import date

BASE_URL = "http://localhost:5000"
SESSION = requests.Session()

def print_result(name, success, details=""):
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")

def test_driver_login():
    """Test driver login"""
    print("\n[TEST] Driver Login")
    try:
        response = SESSION.post(f"{BASE_URL}/driver-login", data={
            'username': 'DRV-001',
            'password': 'pass123'
        })
        
        success = response.status_code == 200
        print_result("POST /driver-login", success, f"Status: {response.status_code}")
        
        # Check if redirected to dashboard
        if response.url == f"{BASE_URL}/driver-dashboard" or "driver_dashboard.html" in response.text:
            print_result("Redirected to dashboard", True)
            return True
        else:
            print_result("Redirected to dashboard", False, f"Redirected to: {response.url}")
            return False
            
    except Exception as e:
        print_result("Driver login", False, str(e))
        return False

def test_dashboard_load():
    """Test dashboard loads with attendance data"""
    print("\n[TEST] Dashboard Load")
    try:
        response = SESSION.get(f"{BASE_URL}/driver-dashboard")
        
        success = response.status_code == 200
        print_result("GET /driver-dashboard", success, f"Status: {response.status_code}")
        
        # Check if HTML contains attendance elements
        checks = {
            "Attendance navigation item": "section-attendance" in response.text or "attendance" in response.text.lower(),
            "Calendar grid element": "calendarGrid" in response.text,
            "Today attendance content": "todayAttendanceContent" in response.text,
            "Recent records element": "recentRecords" in response.text,
            "Leave modal": "leaveModal" in response.text,
        }
        
        for check_name, check_result in checks.items():
            print_result(check_name, check_result)
        
        return all(checks.values())
        
    except Exception as e:
        print_result("Dashboard load", False, str(e))
        return False

def test_mark_attendance():
    """Test marking attendance"""
    print("\n[TEST] Mark Attendance")
    try:
        # First, ensure we're logged in
        if not SESSION.cookies:
            test_driver_login()
        
        response = SESSION.post(f"{BASE_URL}/mark-attendance", 
            json={"status": "Present"},
            headers={"Content-Type": "application/json"}
        )
        
        success = response.status_code == 200
        print_result("POST /mark-attendance", success, f"Status: {response.status_code}")
        
        try:
            data = response.json()
            if data.get('status') == 'success':
                print_result("Response status", True, data.get('message', ''))
                return True
            else:
                print_result("Response status", False, f"Got: {data.get('status')}")
                return False
        except:
            print_result("Parse JSON response", False, "Response was not valid JSON")
            return False
            
    except Exception as e:
        print_result("Mark attendance", False, str(e))
        return False

def test_leave_request():
    """Test requesting leave"""
    print("\n[TEST] Request Leave")
    try:
        # First, ensure we're logged in
        if not SESSION.cookies:
            test_driver_login()
        
        response = SESSION.post(f"{BASE_URL}/mark-attendance", 
            json={
                "status": "On Leave",
                "leave_reason": "Personal medical appointment required for health checkup"
            },
            headers={"Content-Type": "application/json"}
        )
        
        success = response.status_code == 200
        print_result("POST /mark-attendance (leave)", success, f"Status: {response.status_code}")
        
        try:
            data = response.json()
            if data.get('status') == 'success':
                print_result("Leave request submitted", True, data.get('message', ''))
                return True
            else:
                print_result("Leave request", False, f"Got: {data.get('status')}")
                return False
        except:
            print_result("Parse response", False, "Response was not valid JSON")
            return False
            
    except Exception as e:
        print_result("Leave request", False, str(e))
        return False

def test_invalid_attendance():
    """Test invalid attendance request"""
    print("\n[TEST] Invalid Attendance (Negative Test)")
    try:
        # First, ensure we're logged in
        if not SESSION.cookies:
            test_driver_login()
        
        # Try invalid status
        response = SESSION.post(f"{BASE_URL}/mark-attendance", 
            json={"status": "Invalid"},
            headers={"Content-Type": "application/json"}
        )
        
        success = response.status_code == 400  # Should return 400 for invalid input
        print_result("Invalid status rejected", success, f"Status: {response.status_code}")
        
        # Try short leave reason
        response = SESSION.post(f"{BASE_URL}/mark-attendance", 
            json={
                "status": "On Leave",
                "leave_reason": "short"
            },
            headers={"Content-Type": "application/json"}
        )
        
        success = response.status_code == 400  # Should return 400 for invalid reason
        print_result("Short leave reason rejected", success, f"Status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print_result("Invalid attendance test", False, str(e))
        return False

def main():
    print("=" * 70)
    print("SmartAmbulance - Attendance System Integration Test")
    print("=" * 70)
    print(f"\nBase URL: {BASE_URL}")
    print("This test requires Flask app running on http://localhost:5000\n")
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print("✓ Flask server is running\n")
    except:
        print("✗ Flask server is NOT running!")
        print("  Please start Flask app with: python app.py")
        print("\nExiting tests...")
        return
    
    results = []
    
    # Run tests in sequence (each depends on previous)
    results.append(("Driver Login", test_driver_login()))
    results.append(("Dashboard Load", test_dashboard_load()))
    results.append(("Mark Attendance", test_mark_attendance()))
    results.append(("Request Leave", test_leave_request()))
    results.append(("Invalid Requests", test_invalid_attendance()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All integration tests passed!")
        print("✓ Attendance system is fully operational!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        print("Please check the errors above and the Flask logs")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
