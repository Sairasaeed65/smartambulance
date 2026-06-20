"""
Test driver and ambulance management routes
Tests the add/remove driver and ambulance functionality
"""

import sys
sys.path.insert(0, 'c:\\Users\\zohai\\OneDrive\\Desktop\\smart ambulance')

from app import app, DRIVERS, HOSPITALS, PATIENT_REQUESTS
import json

# Create a test client
client = app.test_client()

# Set up session context for hospital login
def test_with_hospital_session():
    """Test all management routes with hospital session"""
    with client:
        # First, login to hospital session
        with app.test_request_context():
            from flask import session
            
            # Simulate hospital login session
            with client.session_transaction() as sess:
                sess['user_type'] = 'hospital'
                sess['username'] = 'hospital1'
            
            print("\n" + "="*70)
            print("MANAGEMENT ROUTES TEST")
            print("="*70)
            
            # Get initial driver count
            response = client.get('/get-drivers')
            initial_drivers = response.get_json()['drivers']
            print(f"\n[Initial State] Hospital has {len(initial_drivers)} drivers")
            for driver in initial_drivers:
                print(f"  - {driver['id']}: {driver['name']} ({driver['ambulance']})")
            
            # Test 1: Add a new driver
            print("\n" + "-"*70)
            print("TEST 1: Add New Driver")
            print("-"*70)
            
            new_driver_data = {
                'driver_name': 'Ahmed Ali',
                'phone': '+971501234567',
                'cnic': '12345-6789012-3',
                'ambulance_id': 'SA-005'
            }
            
            response = client.post('/add-driver', 
                json=new_driver_data,
                content_type='application/json')
            
            add_driver_result = response.get_json()
            print(f"Status: {add_driver_result['status']}")
            print(f"Message: {add_driver_result['message']}")
            
            if add_driver_result['status'] == 'success':
                new_driver_id = add_driver_result['driver_id']
                print(f"✓ Driver added successfully: {new_driver_id}")
                print(f"  Name: {add_driver_result['driver']['name']}")
                print(f"  Ambulance: {add_driver_result['driver']['ambulance']}")
                print(f"  Status: {add_driver_result['driver']['status']}")
                
                # Verify driver was added
                response = client.get('/get-drivers')
                updated_drivers = response.get_json()['drivers']
                print(f"\nAfter add: Hospital has {len(updated_drivers)} drivers")
                
                # Test 2: Remove the driver
                print("\n" + "-"*70)
                print("TEST 2: Remove Driver")
                print("-"*70)
                
                remove_data = {'driver_id': new_driver_id}
                response = client.post('/remove-driver',
                    json=remove_data,
                    content_type='application/json')
                
                remove_result = response.get_json()
                print(f"Status: {remove_result['status']}")
                print(f"Message: {remove_result['message']}")
                
                if remove_result['status'] == 'success':
                    print(f"✓ Driver removed successfully")
                    
                    # Verify driver was removed
                    response = client.get('/get-drivers')
                    final_drivers = response.get_json()['drivers']
                    print(f"After remove: Hospital has {len(final_drivers)} drivers")
            
            # Test 3: Add an ambulance
            print("\n" + "-"*70)
            print("TEST 3: Add Ambulance with Auto-generated Driver")
            print("-"*70)
            
            ambulance_data = {
                'ambulance_id': 'SA-006',
                'driver_name': 'Hassan Mohamed',
                'driver_phone': '0300-1234567',
                'experience_years': 3,
                'vehicle_type': 'Advanced'
            }
            
            response = client.post('/add-ambulance',
                json=ambulance_data,
                content_type='application/json')
            
            add_ambulance_result = response.get_json()
            print(f"Status: {add_ambulance_result['status']}")
            print(f"Message: {add_ambulance_result['message']}")
            
            if add_ambulance_result['status'] == 'success':
                driver_id = add_ambulance_result['driver_id']
                ambulance_id = add_ambulance_result['ambulance_id']
                print(f"✓ Ambulance added successfully")
                print(f"  Ambulance: {ambulance_id}")
                print(f"  Driver ID: {driver_id}")
                print(f"  Driver Name: {add_ambulance_result['driver_name']}")
                
                # Test 4: Remove the ambulance
                print("\n" + "-"*70)
                print("TEST 4: Remove Ambulance (which also removes driver)")
                print("-"*70)
                
                response = client.get('/get-drivers')
                before_remove = len(response.get_json()['drivers'])
                print(f"Before remove: Hospital has {before_remove} drivers")
                
                remove_ambulance_data = {'ambulance_id': ambulance_id}
                response = client.post('/remove-ambulance',
                    json=remove_ambulance_data,
                    content_type='application/json')
                
                remove_ambulance_result = response.get_json()
                print(f"Status: {remove_ambulance_result['status']}")
                print(f"Message: {remove_ambulance_result['message']}")
                
                if remove_ambulance_result['status'] == 'success':
                    print(f"✓ Ambulance removed successfully")
                    
                    response = client.get('/get-drivers')
                    after_remove = len(response.get_json()['drivers'])
                    print(f"After remove: Hospital has {after_remove} drivers")
                    print(f"(Driver also removed: {after_remove < before_remove})")
            
            # Test 5: Get hospital stats (should reflect changes)
            print("\n" + "-"*70)
            print("TEST 5: Hospital Stats")
            print("-"*70)
            
            response = client.get('/get-hospital-stats')
            stats = response.get_json()
            print(f"Hospital: {stats['hospital']}")
            print(f"Beds: {stats['beds']['available']}/{stats['beds']['total']} available")
            print(f"Ambulances: {stats['ambulances']['available']}/{stats['ambulances']['total']} available")
            print(f"Active Emergencies: {stats['emergencies']}")
            
            print("\n" + "="*70)
            print("ALL TESTS COMPLETED ✓")
            print("="*70)

if __name__ == '__main__':
    test_with_hospital_session()
