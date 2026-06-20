#!/usr/bin/env python3
"""
Test Driver and Ambulance Management Features
Tests: Add Driver, Remove Driver, Add Ambulance, Remove Ambulance
"""

from app import app, DRIVERS, HOSPITALS
import json

def test_driver_ambulance_management():
    client = app.test_client()
    
    print("\n" + "="*70)
    print("DRIVER AND AMBULANCE MANAGEMENT TEST SUITE")
    print("="*70)
    
    # ========== TEST 1: Add New Driver ==========
    print("\n[TEST 1] Add New Driver")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.post('/add-driver', 
            json={
                'driver_name': 'Test Driver',
                'phone': '03001111111',
                'cnic': '12345-5555555-1',
                'ambulance_id': 'AL-005'
            },
            content_type='application/json'
        )
        
        data = response.get_json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        
        if response.status_code == 201 and data.get('status') == 'success':
            print("✓ Driver added successfully")
            new_driver_id = data.get('driver_id')
            print(f"  Driver ID: {new_driver_id}")
            print(f"  Driver Name: {data.get('driver_name')}")
            print(f"  Ambulance: {data.get('ambulance')}")
        else:
            print("✗ Failed to add driver")
            return False
    
    # ========== TEST 2: Verify Driver in DRIVERS dict ==========
    print("\n[TEST 2] Verify Driver Added to DRIVERS dict")
    print("-" * 70)
    
    if new_driver_id in DRIVERS:
        driver = DRIVERS[new_driver_id]
        print(f"✓ Driver found in DRIVERS dict")
        print(f"  Name: {driver.get('name')}")
        print(f"  Phone: {driver.get('phone')}")
        print(f"  CNIC: {driver.get('cnic')}")
        print(f"  Ambulance: {driver.get('ambulance')}")
        print(f"  Status: {driver.get('status')}")
    else:
        print("✗ Driver not found in DRIVERS dict")
        return False
    
    # ========== TEST 3: Get Drivers (should include new driver) ==========
    print("\n[TEST 3] Get Drivers (verify new driver appears)")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.get('/get-drivers')
        data = response.get_json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Status: {data.get('status')}")
        print(f"Number of Drivers: {len(data.get('drivers', []))}")
        
        new_driver_found = False
        for driver in data.get('drivers', []):
            if driver.get('name') == 'Test Driver':
                new_driver_found = True
                print(f"✓ New driver found in /get-drivers response")
                print(f"  Name: {driver.get('name')}")
                print(f"  Phone: {driver.get('phone')}")
                break
        
        if not new_driver_found:
            print("✗ New driver not found in /get-drivers")
            return False
    
    # ========== TEST 4: Add New Ambulance ==========
    print("\n[TEST 4] Add New Ambulance")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.post('/add-ambulance',
            json={
                'ambulance_id': 'AL-006',
                'driver_name': 'Test Ambulance Driver',
                'driver_phone': '03002222222',
                'experience_years': 3,
                'vehicle_type': 'Advanced'
            },
            content_type='application/json'
        )
        
        data = response.get_json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        
        if response.status_code == 201 and data.get('status') == 'success':
            print("✓ Ambulance added successfully")
            print(f"  Ambulance ID: {data.get('ambulance_id')}")
            ambulance_driver_id = data.get('driver_id')
            print(f"  Driver ID: {ambulance_driver_id}")
        else:
            print("✗ Failed to add ambulance")
            return False
    
    # ========== TEST 5: Remove Driver ==========
    print("\n[TEST 5] Remove Driver")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.post('/remove-driver',
            json={
                'driver_id': new_driver_id
            },
            content_type='application/json'
        )
        
        data = response.get_json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        
        if response.status_code == 200 and data.get('status') == 'success':
            print("✓ Driver removed successfully")
        else:
            print("✗ Failed to remove driver")
            return False
    
    # ========== TEST 6: Verify Driver Removed ==========
    print("\n[TEST 6] Verify Driver Removed")
    print("-" * 70)
    
    if new_driver_id not in DRIVERS:
        print(f"✓ Driver {new_driver_id} removed from DRIVERS dict")
    else:
        print(f"✗ Driver {new_driver_id} still in DRIVERS dict")
        return False
    
    # ========== TEST 7: Remove Ambulance ==========
    print("\n[TEST 7] Remove Ambulance")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.post('/remove-ambulance',
            json={
                'ambulance_id': 'AL-006'
            },
            content_type='application/json'
        )
        
        data = response.get_json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        
        if response.status_code == 200 and data.get('status') == 'success':
            print("✓ Ambulance removed successfully")
        else:
            print("✗ Failed to remove ambulance")
            return False
    
    # ========== TEST 8: Verify Ambulance Removed ==========
    print("\n[TEST 8] Verify Ambulance Removed")
    print("-" * 70)
    
    hospital_ambulances = HOSPITALS['hospital1'].get('ambulances_assigned', [])
    if 'AL-006' not in hospital_ambulances:
        print(f"✓ Ambulance AL-006 removed from hospital1 ambulances_assigned")
        print(f"  Current ambulances: {hospital_ambulances}")
    else:
        print(f"✗ Ambulance AL-006 still in hospital1 ambulances_assigned")
        return False
    
    # ========== TEST 9: Verify Associated Driver Removed ==========
    print("\n[TEST 9] Verify Associated Driver Removed")
    print("-" * 70)
    
    if ambulance_driver_id not in DRIVERS:
        print(f"✓ Driver {ambulance_driver_id} (associated with ambulance) removed")
    else:
        print(f"✗ Driver {ambulance_driver_id} still exists")
        return False
    
    # ========== TEST 10: Hospital Stats Sync ==========
    print("\n[TEST 10] Hospital Stats Auto-Sync")
    print("-" * 70)
    
    with client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'hospital'
            sess['username'] = 'hospital1'
        
        response = client.get('/get-hospital-stats')
        data = response.get_json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Beds Total: {data['beds']['total']}")
        print(f"Beds Available: {data['beds']['available']}")
        print(f"Ambulances Total: {data['ambulances']['total']}")
        print(f"Ambulances Available: {data['ambulances']['available']}")
        print(f"Active Emergencies: {data['emergencies']}")
        
        if data.get('status') == 'success':
            print("✓ Hospital stats retrieved successfully")
        else:
            print("✗ Failed to get hospital stats")
            return False
    
    return True

if __name__ == '__main__':
    success = test_driver_ambulance_management()
    
    print("\n" + "="*70)
    if success:
        print("✓ ALL TESTS PASSED")
        print("Driver and ambulance management fully functional!")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*70 + "\n")
