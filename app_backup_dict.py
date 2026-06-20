"""
================================================
    SMARTAMBULANCE - FLASK APPLICATION
    AI-Driven Emergency Ambulance Routing System
================================================

Routes:
- / : Home page (landing)
- /emergency : Emergency dispatch endpoint
- /driver-login : Driver authentication
- /hospital-login : Hospital dashboard login
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import os
import threading
import random

# Initialize Flask Application with static folder configuration
app = Flask(__name__, 
            static_folder='static',      # Specify static folder path
            static_url_path='/static')   # URL path for static files
app.secret_key = 'smartambulance_secret_key_2026'

# ==================== PERFORMANCE OPTIMIZATIONS ====================

# Add caching headers for static files
@app.after_request
def add_header(response):
    """Add caching and compression headers for better performance"""
    # Cache static files for 30 days (86400 * 30 seconds)
    if response.content_type and ('javascript' in response.content_type or 
                                   'css' in response.content_type or
                                   'image' in response.content_type or
                                   'font' in response.content_type):
        response.cache_control.max_age = 2592000  # 30 days
        response.cache_control.public = True
    
    # Add more cache control headers for fast reload
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    return response

# Thread-safe lock for request operations
request_lock = threading.Lock()

# ==================== DISPATCH SYSTEM HELPERS ====================

def check_duplicate_request(phone_number):
    """
    Check if a request from same phone number exists within last 10 minutes
    Returns the existing request if found, None otherwise
    """
    cutoff_time = datetime.now() - timedelta(minutes=10)
    
    for req_id, req_data in PATIENT_REQUESTS.items():
        if req_data['patient_phone'] == phone_number:
            req_timestamp = datetime.fromisoformat(req_data['timestamp'])
            if req_timestamp > cutoff_time and not req_data['cancelled']:
                return req_data
    
    return None

def lock_request(request_id, driver_username):
    """
    Atomically lock a request for a specific driver
    Prevents other drivers from accepting it
    Returns: (success: bool, message: str, request: dict or None)
    """
    with request_lock:
        if request_id not in PATIENT_REQUESTS:
            return False, "Request not found", None
        
        req = PATIENT_REQUESTS[request_id]
        
        # Check if already locked by another driver
        if req['locked'] and req['locked_by'] != driver_username:
            return False, f"Request locked by {req['locked_by']}", None
        
        # Check if cancelled
        if req['cancelled']:
            return False, "Request has been cancelled", None
        
        # Lock the request
        req['locked'] = True
        req['locked_by'] = driver_username
        req['locked_at'] = datetime.now().isoformat()
        req['assigned_driver'] = driver_username
        
        print(f'[LOCK] Request {request_id} locked by {driver_username}')
        return True, "Request locked successfully", req

def unlock_request(request_id):
    """
    Unlock a request for reassignment to another driver
    Called when driver cancels or times out
    """
    with request_lock:
        if request_id not in PATIENT_REQUESTS:
            return False, "Request not found"
        
        req = PATIENT_REQUESTS[request_id]
        req['locked'] = False
        req['locked_by'] = None
        req['locked_at'] = None
        req['assigned_driver'] = None
        req['reassignment_count'] += 1
        
        print(f'[UNLOCK] Request {request_id} unlocked for reassignment (attempt {req["reassignment_count"]})')
        return True, f"Request unlocked and available for reassignment"

def get_available_requests(driver_username):
    """
    Get requests available for a specific driver
    - Unassigned and unlocked requests
    - Requests assigned to this driver
    Excludes:
    - Requests locked by other drivers
    - Cancelled requests
    - Duplicate requests (same phone within 10 min)
    """
    available = []
    
    for req_id, req_data in PATIENT_REQUESTS.items():
        # Skip cancelled requests
        if req_data['cancelled']:
            continue
        
        # Include if assigned to this driver
        if req_data['assigned_driver'] == driver_username:
            available.append(req_data)
            continue
        
        # Include if unlocked and unassigned
        if not req_data['locked'] and req_data['assigned_driver'] is None:
            available.append(req_data)
    
    return available

def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calculate distance between two lat/lng points using Haversine formula
    Returns distance in kilometers
    """
    import math
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(dlng/2) * math.sin(dlng/2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def find_next_nearest_hospital(current_hospital_name, request_id):
    """
    Find next nearest hospital with available beds and ambulances
    that hasn't rejected the request yet
    
    Returns: (hospital_username: str or None, hospital_info: dict or None)
    """
    req = PATIENT_REQUESTS.get(request_id)
    if not req:
        return None, None
    
    # Get current hospital coordinates
    current_hospital = None
    for username, info in HOSPITALS.items():
        if info['name'] == current_hospital_name:
            current_hospital = (username, info)
            break
    
    if not current_hospital:
        return None, None
    
    curr_username, curr_info = current_hospital
    curr_lat = curr_info.get('latitude', 25.2)
    curr_lng = curr_info.get('longitude', 55.2)
    
    # Get list of hospitals that have rejected this request
    rejected_by = req.get('rejected_by', [])
    
    # Find all available hospitals with their distances
    available_hospitals = []
    for username, hospital_info in HOSPITALS.items():
        # Skip current hospital and already rejected hospitals
        if username == curr_username or hospital_info['name'] in rejected_by:
            continue
        
        # Check if has available beds
        if hospital_info.get('available_beds', 0) <= 0:
            continue
        
        # Check if has available ambulances (count drivers with Available status)
        available_ambulances = 0
        hospital_drivers = hospital_info.get('drivers_assigned', [])
        for driver_id in hospital_drivers:
            driver_info = DRIVERS.get(driver_id, {})
            if driver_info.get('status') == 'Available':
                available_ambulances += 1
        
        if available_ambulances <= 0:
            continue
        
        # Calculate distance
        hosp_lat = hospital_info.get('latitude', 25.2)
        hosp_lng = hospital_info.get('longitude', 55.2)
        distance = calculate_distance(curr_lat, curr_lng, hosp_lat, hosp_lng)
        
        available_hospitals.append({
            'username': username,
            'info': hospital_info,
            'distance': distance
        })
    
    # Sort by distance and return nearest
    if available_hospitals:
        available_hospitals.sort(key=lambda x: x['distance'])
        nearest = available_hospitals[0]
        return nearest['username'], nearest['info']
    
    return None, None

# ==================== DUMMY DATA ====================
# Dummy users for authentication (for FYP demo purposes)
DRIVERS = {
    'driver1': {
        'username': 'DRV-001',
        'password': 'pass123',
        'name': 'Ahmed Al-Mansouri',
        'phone': '+971501234567',
        'email': 'ahmed.driver@smartambulance.ae',
        'hospital': 'hospital1',
        'hospital_name': 'City General Hospital',
        'assigned_ambulance': 'SA-001',
        'vehicle_type': 'Advanced Life Support',
        'status': 'Available',
        'experience_years': 8,
        'license': 'DRV-LIC-2026-001',
        'certifications': ['EMT-P', 'BLS', 'ACLS', 'PALS'],
        'registration_date': datetime.now().isoformat()
    },
    'driver2': {
        'username': 'DRV-002',
        'password': 'pass123',
        'name': 'Fatima Al-Zaabi',
        'phone': '+971509876543',
        'email': 'fatima.driver@smartambulance.ae',
        'hospital': 'hospital1',
        'hospital_name': 'City General Hospital',
        'assigned_ambulance': 'SA-002',
        'vehicle_type': 'Advanced Life Support',
        'status': 'Available',
        'experience_years': 5,
        'license': 'DRV-LIC-2026-002',
        'certifications': ['EMT-P', 'BLS', 'ACLS'],
        'registration_date': datetime.now().isoformat()
    },
    'driver3': {
        'username': 'DRV-003',
        'password': 'pass123',
        'name': 'Mohammed Al-Ketbi',
        'phone': '+971505555555',
        'email': 'mohammed.driver@smartambulance.ae',
        'hospital': 'hospital2',
        'hospital_name': 'Metro Medical Center',
        'assigned_ambulance': 'SA-003',
        'vehicle_type': 'Basic Life Support',
        'status': 'Available',
        'experience_years': 3,
        'license': 'DRV-LIC-2026-003',
        'certifications': ['EMT-B', 'BLS', 'First Aid'],
        'registration_date': datetime.now().isoformat()
    },
    'driver4': {
        'username': 'DRV-004',
        'password': 'pass123',
        'name': 'Sara Johnson',
        'phone': '+971507777777',
        'email': 'sara.driver@smartambulance.ae',
        'hospital': 'hospital2',
        'hospital_name': 'Metro Medical Center',
        'assigned_ambulance': 'SA-004',
        'vehicle_type': 'Advanced Life Support',
        'status': 'Available',
        'experience_years': 6,
        'license': 'DRV-LIC-2026-004',
        'certifications': ['EMT-P', 'BLS', 'ACLS', 'PALS'],
        'registration_date': datetime.now().isoformat()
    }
}

# Ambulances - Separate dictionary for ambulance management
AMBULANCES = {
    'SA-001': {
        'id': 'SA-001',
        'type': 'Advanced Life Support',
        'registration': 'D-2026-001',
        'hospital': 'hospital1',
        'assigned_driver': 'driver1',
        'status': 'Available',
        'last_service': '2026-02-15',
        'equipment': ['Defibrillator', 'Oxygen Tank', 'Emergency Stretcher']
    },
    'SA-002': {
        'id': 'SA-002',
        'type': 'Advanced Life Support',
        'registration': 'D-2026-002',
        'hospital': 'hospital1',
        'assigned_driver': 'driver2',
        'status': 'Available',
        'last_service': '2026-02-18',
        'equipment': ['Defibrillator', 'Oxygen Tank', 'Emergency Stretcher']
    },
    'SA-003': {
        'id': 'SA-003',
        'type': 'Basic Life Support',
        'registration': 'D-2026-003',
        'hospital': 'hospital2',
        'assigned_driver': 'driver3',
        'status': 'Available',
        'last_service': '2026-02-20',
        'equipment': ['Oxygen Tank', 'Emergency Stretcher', 'First Aid Kit']
    },
    'SA-004': {
        'id': 'SA-004',
        'type': 'Advanced Life Support',
        'registration': 'D-2026-004',
        'hospital': 'hospital2',
        'assigned_driver': 'driver4',
        'status': 'Available',
        'last_service': '2026-02-19',
        'equipment': ['Defibrillator', 'Oxygen Tank', 'Emergency Stretcher', 'Portable Monitor']
    }
}

HOSPITALS = {
    'hospital1': {
        'password': 'pass123',
        'name': 'City General Hospital',
        'beds': 150,
        'available_beds': 150,
        'occupied_beds': 0,
        'address': '123 Medical Street, Dubai',
        'phone': '+971421234567',
        'email': 'emergency@citygen.ae',
        'ambulances_assigned': [],
        'drivers_assigned': [],
        'specialties': ['Emergency Medicine', 'Trauma Care', 'Cardiology'],
        'website': 'www.citygenhospital.ae',
        'latitude': 25.1972,
        'longitude': 55.2744
    },
    'hospital2': {
        'password': 'pass123',
        'name': 'Metro Medical Center',
        'beds': 200,
        'available_beds': 200,
        'occupied_beds': 0,
        'address': '456 Health Avenue, Dubai',
        'phone': '+971429876543',
        'email': 'emergency@metromedical.ae',
        'ambulances_assigned': [],
        'drivers_assigned': [],
        'specialties': ['General Medicine', 'Orthopedics', 'Pediatrics'],
        'website': 'www.metromedical.ae',
        'latitude': 25.2165,
        'longitude': 55.2659
    }
}

# Update hospital drivers_assigned lists
for driver_id, driver_info in DRIVERS.items():
    hospital_key = driver_info.get('hospital')
    if hospital_key in HOSPITALS:
        HOSPITALS[hospital_key]['drivers_assigned'].append(driver_id)

# Dummy users for public access (optional login)
USERS = {
    'user1': {
        'password': 'pass123',
        'name': 'Ahmed Hassan',
        'email': 'ahmed@gmail.com',
        'phone': '+971501111111',
        'address': 'Dubai, UAE',
        'emergency_contacts': [
            {'name': 'Fatima Hassan', 'phone': '+971502222222', 'relation': 'Sister'}
        ],
        'medical_history': 'Type 2 Diabetes',
        'blood_type': 'O+'
    },
    'user2': {
        'password': 'pass123',
        'name': 'Sarah Johnson',
        'email': 'sarah@gmail.com',
        'phone': '+971503333333',
        'address': 'Abu Dhabi, UAE',
        'emergency_contacts': [
            {'name': 'John Johnson', 'phone': '+971504444444', 'relation': 'Husband'}
        ],
        'medical_history': 'Hypertension',
        'blood_type': 'A+'
    }
}

# Smart Patient Authentication System - CNIC based
PATIENT_USERS = {
    '12345-1234567-1': {
        'cnic': '12345-1234567-1',
        'full_name': 'Test Patient',
        'phone': '+92 300 1234567',
        'registered_at': datetime.now().isoformat(),
        'emergency_contacts': [],
        'medical_history': '',
        'blood_type': 'Unknown'
    }
}

# Active Dispatches - Tracks ambulance dispatches for requests
DISPATCHES = {}

# Patient Requests - Simulated incoming requests with status tracking
PATIENT_REQUESTS = {
    'REQ-001': {
        'id': 'REQ-001',
        'patient_name': 'Ahmed Hassan',
        'patient_phone': '+971501234567',
        'pickup_address': 'Al Wasl Road, Dubai',
        'hospital': 'City General Hospital',
        'reason': 'Chest Pain',
        'priority': 'High',
        'status': 'pending',  # pending, accepted, en_route, picked_up, completed
        'status_step': 0,
        'assigned_driver': None,
        'timestamp': datetime.now().isoformat(),
        'age': 45,
        'symptoms': 'Severe chest pain and shortness of breath',
        # NEW FIELDS FOR DISPATCH SYSTEM
        'locked': False,  # Is request locked by a driver
        'locked_by': None,  # Which driver locked it
        'locked_at': None,  # When it was locked
        'cancelled': False,  # Has request been cancelled
        'reassignment_count': 0,  # Number of times reassigned
        'rejected_by': []  # List of hospitals that rejected this request
    },
    'REQ-002': {
        'id': 'REQ-002',
        'patient_name': 'Fatima Al-Mansouri',
        'patient_phone': '+971509876543',
        'pickup_address': 'Dubai Marina, Dubai',
        'hospital': 'City General Hospital',
        'reason': 'Leg Fracture',
        'priority': 'Medium',
        'status': 'accepted',
        'status_step': 1,
        'assigned_driver': 'driver1',
        'timestamp': datetime.now().isoformat(),
        'age': 32,
        'symptoms': 'Suspected fracture in left leg after fall',
        'locked': True,
        'locked_by': 'driver1',
        'locked_at': datetime.now().isoformat(),
        'cancelled': False,
        'reassignment_count': 0,
        'rejected_by': []
    },
    'REQ-003': {
        'id': 'REQ-003',
        'patient_name': 'Mohammed Al-Zaabi',
        'patient_phone': '+971505555555',
        'pickup_address': 'Business Bay, Dubai',
        'hospital': 'Metro Medical Center',
        'reason': 'Sudden Dizziness',
        'priority': 'Medium',
        'status': 'en_route',
        'status_step': 2,
        'assigned_driver': 'driver2',
        'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
        'age': 58,
        'symptoms': 'Sudden dizziness and loss of balance',
        'locked': True,
        'locked_by': 'driver2',
        'locked_at': (datetime.now() - timedelta(minutes=10)).isoformat(),
        'cancelled': False,
        'reassignment_count': 0,
        'rejected_by': []
    },
    'REQ-004': {
        'id': 'REQ-004',
        'patient_name': 'Layla Ahmed',
        'patient_phone': '+971507777777',
        'pickup_address': 'Downtown Dubai, Dubai',
        'hospital': 'City General Hospital',
        'reason': 'Allergic Reaction',
        'priority': 'High',
        'status': 'picked_up',
        'status_step': 3,
        'assigned_driver': 'driver1',
        'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
        'age': 28,
        'symptoms': 'Severe allergic reaction to unknown substance',
        'locked': True,
        'locked_by': 'driver1',
        'locked_at': (datetime.now() - timedelta(minutes=4)).isoformat(),
        'cancelled': False,
        'reassignment_count': 0,
        'rejected_by': []
    }
}

# ==================== HOME ROUTE ====================
@app.route('/')
def home():
    """
    Render the home/landing page
    @route GET /
    @return Rendered index.html template
    """
    return render_template('index.html')

# ==================== EMERGENCY ROUTE ====================
@app.route('/emergency', methods=['GET', 'POST'])
def emergency():
    """
    Handle emergency dispatch request
    - Triggered by EMERGENCY HELP button
    - Gets user's live geolocation (latitude/longitude)
    - Creates emergency alert and finds nearest ambulance
    
    @route POST /emergency
    @param latitude: User's latitude from Geolocation API
    @param longitude: User's longitude from Geolocation API
    @param accuracy: Accuracy of geolocation in meters
    @param location_method: 'device_gps' or 'fallback'
    @return JSON response with emergency details
    """
    if request.method == 'POST':
        try:
            # Get emergency data from request
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Extract geolocation data
            latitude = data.get('latitude', 25.2048)  # Dubai city center fallback
            longitude = data.get('longitude', 55.2708)
            accuracy = data.get('accuracy')
            location_method = data.get('location_method', 'unknown')
            
            # Log geolocation info
            location_info = f'{latitude:.4f}, {longitude:.4f}'
            if accuracy:
                location_info += f' (±{accuracy:.1f}m)'
            print(f'[GEOLOCATION] Emergency at {location_info} ({location_method})')
            
            # Create emergency record with location data
            emergency_data = {
                'status': 'success',
                'message': 'Emergency response initiated',
                'emergency_id': f'EMG-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'timestamp': datetime.now().isoformat(),
                'dispatcher': 'AI System',
                # Location details
                'location': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'accuracy_meters': accuracy,
                    'method': location_method
                },
                'nearest_ambulance': {
                    'id': 'SA-001',
                    'driver': 'John Doe',
                    'eta_minutes': 5,
                    'location': '2.5 km away',
                    'status': 'En Route'
                },
                'hospital_prepared': {
                    'name': 'City General Hospital',
                    'beds_available': 12,
                    'department': 'Emergency Ward'
                }
            }
            
            # Log emergency with location
            print(f'[EMERGENCY ALERT] {emergency_data["emergency_id"]} at {emergency_data["timestamp"]}')
            print(f'[LOCATION] Lat: {latitude:.4f}, Lng: {longitude:.4f}')
            
            return jsonify(emergency_data), 200
            
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # GET request - show emergency page
    return render_template('emergency.html')

@app.route('/dispatch', methods=['POST'])
def dispatch():
    """
    Handle ambulance dispatch for selected hospital
    - Called after user selects a hospital on emergency page
    - Creates a patient request entry with real patient data from session
    - Assigns to nearest available ambulance
    
    @route POST /dispatch
    @param hospital_name: Name of selected hospital
    @param lat: User's latitude
    @param lng: User's longitude
    @return JSON response with emergency_id and dispatch details
    """
    try:
        # Get dispatch data from request
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Extract parameters
        hospital_name = data.get('hospital_name', 'Selected Hospital')
        lat = data.get('lat', 25.2048)
        lng = data.get('lng', 55.2708)
        
        # Get patient data from session (if logged in)
        patient_name = session.get('patient_name', 'Guest Patient')
        patient_phone = session.get('patient_phone', 'Not Provided')
        
        # If still not provided, use defaults
        if not patient_name or patient_name is None:
            patient_name = 'Guest Patient'
        if not patient_phone or patient_phone is None:
            patient_phone = 'Not Provided'
        
        # Generate emergency ID
        emergency_id = f'EMG-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        request_id = f'REQ-{len(PATIENT_REQUESTS) + 1:03d}'
        
        # Create patient request with atomic lock
        with request_lock:
            # Create new request entry with real patient data
            new_request = {
                'id': request_id,
                'emergency_id': emergency_id,
                'patient_name': patient_name,
                'patient_phone': patient_phone,
                'pickup_address': f'{lat:.4f}, {lng:.4f}',
                'hospital': hospital_name,
                'hospital_id': None,
                'reason': 'Emergency Call',
                'priority': 'High',
                'status': 'pending',
                'status_step': 0,
                'assigned_driver': None,
                'timestamp': datetime.now().isoformat(),
                'age': 0,
                'symptoms': 'Emergency dispatch from mobile app',
                'locked': False,
                'locked_by': None,
                'locked_at': None,
                'cancelled': False,
                'reassignment_count': 0,
                'location': {
                    'latitude': lat,
                    'longitude': lng
                }
            }
            
            # Add to PATIENT_REQUESTS
            PATIENT_REQUESTS[request_id] = new_request
        
        print(f'[DISPATCH] {emergency_id} - Patient: {patient_name} ({patient_phone}) - Hospital: {hospital_name} at ({lat:.4f}, {lng:.4f})')
        
        # Return dispatch confirmation
        return jsonify({
            'status': 'success',
            'message': 'Ambulance dispatch initiated',
            'emergency_id': emergency_id,
            'request_id': request_id,
            'patient_name': patient_name,
            'patient_phone': patient_phone,
            'hospital': hospital_name,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f'[DISPATCH ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 400

# ==================== AMBULANCE TRACKING ROUTE ====================
@app.route('/track')
def track_ambulance():
    """
    Patient/Public-facing ambulance tracking page
    - Shows real-time location of dispatched ambulance
    - No authentication required for patients to track their ambulance
    - Uses simulated movement with fallback to mock location
    
    @route GET /track : Show ambulance tracking page
    @return Rendered track.html template
    """
    return render_template('track.html')

# ==================== PATIENT REQUESTS API ====================
@app.route('/get-requests')
def get_requests():
    """
    Get incoming patient requests for driver dashboard
    - Returns only available requests (unassigned + assigned to current driver)
    - Filters out requests locked by other drivers
    - Filters out cancelled requests
    - Implements duplicate prevention by phone number (10 min window)
    - Requires driver session
    
    @route GET /get-requests
    @return JSON array of available patient requests
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = session.get('username')
    
    # Get available requests for this driver
    available_requests = get_available_requests(username)
    
    # Enrich with hospital details
    for req in available_requests:
        hospital_name = req.get('hospital')
        for hosp_key, hosp_data in HOSPITALS.items():
            if hosp_data['name'] == hospital_name:
                req['hospital_phone'] = hosp_data.get('phone')
                req['hospital_email'] = hosp_data.get('email')
                req['hospital_address'] = hosp_data.get('address')
                break
    
    return jsonify({
        'status': 'success',
        'current_driver': username,  # Include current driver for frontend lock status check
        'requests': available_requests
    }), 200

@app.route('/get-driver-info/<driver_username>')
def get_driver_info(driver_username):
    """
    Get detailed driver information
    - Returns driver details, certifications, experience
    - Requires authentication
    
    @route GET /get-driver-info/<driver_username>
    @return JSON response with driver details
    """
    if 'user_type' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    if driver_username not in DRIVERS:
        return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
    
    driver = DRIVERS[driver_username].copy()
    # Remove password from response
    driver.pop('password', None)
    
    return jsonify({
        'status': 'success',
        'driver': driver
    }), 200

@app.route('/get-hospital-info/<hospital_username>')
def get_hospital_info(hospital_username):
    """
    Get detailed hospital information
    - Returns hospital details, specialties, contact info
    - Requires authentication
    
    @route GET /get-hospital-info/<hospital_username>
    @return JSON response with hospital details
    """
    if 'user_type' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    if hospital_username not in HOSPITALS:
        return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
    
    hospital = HOSPITALS[hospital_username].copy()
    # Remove password from response
    hospital.pop('password', None)
    
    return jsonify({
        'status': 'success',
        'hospital': hospital
    }), 200

@app.route('/lock-request', methods=['POST'])
def lock_request_endpoint():
    """
    Lock/accept a patient request for a specific driver
    - Atomically locks request to prevent other drivers from accepting
    - Checks for duplicates (same phone within 10 minutes)
    - Implements thread-safe locking
    
    @route POST /lock-request
    @param request_id: ID of request to lock
    @return JSON response with lock result
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        username = session.get('username')
        
        if request_id not in PATIENT_REQUESTS:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        req = PATIENT_REQUESTS[request_id]
        
        # Check for duplicate requests by phone number
        duplicate = check_duplicate_request(req['patient_phone'])
        if duplicate and duplicate['id'] != request_id and not duplicate['locked']:
            return jsonify({
                'status': 'error',
                'message': f'Duplicate request detected from same phone number. Request {duplicate["id"]} already exists.',
                'duplicate_request_id': duplicate['id']
            }), 409
        
        # Attempt to lock the request
        success, message, locked_req = lock_request(request_id, username)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': message
            }), 409
        
        return jsonify({
            'status': 'success',
            'message': 'Request locked successfully',
            'request': locked_req
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/update-request-status', methods=['POST'])
def update_request_status():
    """
    Update the status of a patient request
    - Driver can only update requests they have locked
    - Prevents unauthorized status changes
    
    @route POST /update-request-status
    @param request_id: ID of request to update
    @param status: New status (accepted, en_route, picked_up, completed)
    @return JSON response
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        new_status = data.get('status')
        username = session.get('username')
        
        if request_id not in PATIENT_REQUESTS:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        req = PATIENT_REQUESTS[request_id]
        
        # Check if request is locked by this driver
        if not req['locked'] or req['locked_by'] != username:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to update this request'
            }), 403
        
        # Status progression mapping
        status_map = {
            'accepted': 1,
            'en_route': 2,
            'picked_up': 3,
            'completed': 4
        }
        
        if new_status not in status_map:
            return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
        
        # Update request
        req['status'] = new_status
        req['status_step'] = status_map[new_status]
        
        print(f'[REQUEST UPDATE] {request_id} - Status: {new_status} - Driver: {username}')
        
        return jsonify({
            'status': 'success',
            'message': f'Request status updated to {new_status}',
            'request': req
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/cancel-request/<request_id>', methods=['POST'])
def cancel_request(request_id):
    """
    Cancel a patient request and unlock for reassignment
    - Called when driver declines or times out
    - Makes request available for other drivers
    - Tracks reassignment count
    
    @route POST /cancel-request/<request_id>
    @return JSON response
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        if request_id not in PATIENT_REQUESTS:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        req = PATIENT_REQUESTS[request_id]
        username = session.get('username')
        
        # Only driver who locked it can cancel
        if req['locked_by'] != username:
            return jsonify({
                'status': 'error',
                'message': 'Only the assigned driver can cancel this request'
            }), 403
        
        # Attempt reassignment
        success, message = unlock_request(request_id)
        
        if not success:
            return jsonify({'status': 'error', 'message': message}), 400
        
        # Check if max reassignment attempts reached
        max_attempts = 3
        if req['reassignment_count'] >= max_attempts:
            req['cancelled'] = True
            return jsonify({
                'status': 'success',
                'message': f'Request cancelled after {max_attempts} reassignment attempts',
                'request': req
            }), 200
        
        return jsonify({
            'status': 'success',
            'message': f'Request cancelled and reassigned (attempt {req["reassignment_count"]})',
            'request': req
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/timeout-request/<request_id>', methods=['POST'])
def timeout_request(request_id):
    """
    Handle request timeout (driver didn't respond within 2 minutes)
    - Automatically unlocks and reassigns to another driver
    - Called by client-side timeout
    
    @route POST /timeout-request/<request_id>
    @return JSON response
    """
    try:
        if request_id not in PATIENT_REQUESTS:
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        req = PATIENT_REQUESTS[request_id]
        
        # Unlock for reassignment
        success, message = unlock_request(request_id)
        
        if not success:
            return jsonify({'status': 'error', 'message': message}), 400
        
        # Check if max reassignment attempts reached
        max_attempts = 3
        if req['reassignment_count'] >= max_attempts:
            req['cancelled'] = True
            return jsonify({
                'status': 'success',
                'message': f'Request timeout and cancelled after {max_attempts} attempts',
                'request': req
            }), 200
        
        print(f'[TIMEOUT] Request {request_id} timed out - Reassigning (attempt {req["reassignment_count"]})')
        
        return jsonify({
            'status': 'success',
            'message': f'Request timed out and reassigned',
            'request': req
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# ==================== USER LOGIN ROUTE ====================
@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    """
    Handle user authentication and login (optional)
    - Users can login to access personalized features
    - Users can also use the app without logging in
    - Creates session for authenticated users
    
    @route GET /user-login : Show login form
    @route POST /user-login : Process login
    @return Rendered template or redirect
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate credentials (dummy authentication)
        if username in USERS and USERS[username]['password'] == password:
            # Create session
            session['user_type'] = 'user'
            session['username'] = username
            session['name'] = USERS[username]['name']
            session['email'] = USERS[username]['email']
            # Also set patient_name and patient_phone for emergency dispatch
            session['patient_name'] = USERS[username]['name']
            session['patient_phone'] = USERS[username]['phone']
            
            print(f'[USER LOGIN] {username} ({USERS[username]["name"]}) logged in')
            return redirect(url_for('user_dashboard'))
        else:
            return render_template('user_login.html', 
                                   error='Invalid username or password',
                                   demo_users=list(USERS.keys()))
    
    # GET request - show login form with demo credentials
    return render_template('user_login.html', demo_users=list(USERS.keys()))

# ==================== USER DASHBOARD ====================
@app.route('/user-dashboard')
def user_dashboard():
    """
    Display user dashboard (optional authentication)
    - Shows user profile information
    - Emergency request history
    - Health information and emergency contacts
    
    @route GET /user-dashboard
    @return Rendered user dashboard
    """
    if 'user_type' not in session or session['user_type'] != 'user':
        return redirect(url_for('user_login'))
    
    username = session.get('username')
    user_info = USERS.get(username, {})
    
    # User dashboard data
    dashboard_data = {
        'user_name': user_info.get('name'),
        'email': user_info.get('email'),
        'phone': user_info.get('phone'),
        'address': user_info.get('address'),
        'blood_type': user_info.get('blood_type'),
        'medical_history': user_info.get('medical_history'),
        'emergency_contacts': user_info.get('emergency_contacts', []),
        'request_history': []  # Would show past emergency requests
    }
    
    return render_template('user_dashboard.html', data=dashboard_data)

# ==================== SMART PATIENT AUTHENTICATION ROUTE ====================
@app.route('/user-smart-login', methods=['POST'])
def user_smart_login():
    """
    Smart Patient Authentication with Security
    - Validates CNIC and Phone Number together (must belong to same record)
    - Prevents duplicate phone numbers and CNICs during registration
    - Auto-registers new patients with both CNIC and phone validation
    
    @route POST /user-smart-login
    @return JSON: {success: bool, user_id: str, message: str}
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        cnic = data.get('cnic', '').strip()
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validate input
        if not cnic or not full_name or not phone:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Validate CNIC format (13 digits)
        cnic_digits_only = ''.join(c for c in cnic if c.isdigit())
        if len(cnic_digits_only) != 13:
            return jsonify({
                'success': False,
                'message': 'CNIC must contain exactly 13 digits'
            }), 400
        
        # Validate phone format (exactly 11 digits, starts with 03)
        if len(phone) != 11 or not phone.startswith('03') or not phone.isdigit():
            return jsonify({
                'success': False,
                'message': 'Phone number must be 11 digits starting with 03 (e.g., 03001234567)'
            }), 400
        
        # ==================== LOGIN LOGIC ====================
        # Check if CNIC already exists
        if cnic in PATIENT_USERS:
            # CNIC exists - verify phone number matches the same record
            patient = PATIENT_USERS[cnic]
            
            if patient['phone'].replace(' ', '') == phone.replace(' ', ''):
                # Both CNIC and phone match - allow login
                session['user_type'] = 'patient'
                session['patient_cnic'] = cnic
                session['patient_name'] = patient['full_name']
                session['patient_phone'] = patient['phone']
                
                print(f'[PATIENT LOGIN] {patient["full_name"]} ({cnic}) logged in - credentials verified')
                
                return jsonify({
                    'success': True,
                    'user_id': cnic,
                    'message': 'Welcome back! Logging in...'
                }), 200
            else:
                # CNIC exists but phone doesn't match - security check failed
                print(f'[LOGIN FAILED] CNIC {cnic} attempted login with mismatched phone: {phone}')
                return jsonify({
                    'success': False,
                    'message': 'Invalid credentials'
                }), 401
        
        # ==================== REGISTRATION LOGIC ====================
        # CNIC is new - check for duplicate phone number
        phone_normalized = phone.replace(' ', '').replace('-', '')
        for existing_cnic, existing_patient in PATIENT_USERS.items():
            existing_phone_normalized = existing_patient['phone'].replace(' ', '').replace('-', '')
            
            if existing_phone_normalized == phone_normalized:
                # Phone number already registered with different CNIC
                print(f'[REGISTRATION FAILED] Duplicate phone number: {phone}')
                return jsonify({
                    'success': False,
                    'message': 'This phone number is already registered'
                }), 409
        
        # Check if CNIC is already registered (shouldn't happen but double-check)
        if cnic in PATIENT_USERS:
            print(f'[REGISTRATION FAILED] Duplicate CNIC: {cnic}')
            return jsonify({
                'success': False,
                'message': 'This CNIC is already registered'
            }), 409
        
        # All checks passed - create new patient account
        new_patient = {
            'cnic': cnic,
            'full_name': full_name,
            'phone': phone,
            'registered_at': datetime.now().isoformat(),
            'emergency_contacts': [],
            'medical_history': '',
            'blood_type': 'Unknown'
        }
        
        # Add to patient database
        PATIENT_USERS[cnic] = new_patient
        
        # Create session
        session['user_type'] = 'patient'
        session['patient_cnic'] = cnic
        session['patient_name'] = full_name
        session['patient_phone'] = phone
        
        print(f'[PATIENT REGISTRATION] {full_name} ({cnic}) registered and logged in (new) - Phone: {phone}')
        
        return jsonify({
            'success': True,
            'user_id': cnic,
            'message': 'Account created and logged in successfully!'
        }), 200
    
    except Exception as e:
        print(f'[ERROR] Smart login error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Server error during authentication'
        }), 500

# ==================== PATIENT PROFILE UPDATE ROUTE ====================
@app.route('/user-update-profile', methods=['POST'])
def user_update_profile():
    """
    Update patient profile information with duplicate phone check
    - Only Full Name and Phone can be updated
    - CNIC cannot be changed
    - Phone number cannot be changed to one already in use
    
    @route POST /user-update-profile
    @return JSON: {success: bool, message: str}
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        cnic = data.get('cnic', '').strip()
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validate input
        if not cnic or not full_name or not phone:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Check if CNIC exists
        if cnic not in PATIENT_USERS:
            return jsonify({
                'success': False,
                'message': 'Patient not found'
            }), 404
        
        # Validate input
        if len(full_name) < 3:
            return jsonify({
                'success': False,
                'message': 'Full name must be at least 3 characters'
            }), 400
        
        # Validate phone format (exactly 11 digits, starts with 03)
        if len(phone) != 11 or not phone.startswith('03') or not phone.isdigit():
            return jsonify({
                'success': False,
                'message': 'Phone number must be 11 digits starting with 03 (e.g., 03001234567)'
            }), 400
        
        # Check if phone number is being changed
        current_patient = PATIENT_USERS[cnic]
        phone_normalized = phone.replace(' ', '').replace('-', '')
        current_phone_normalized = current_patient['phone'].replace(' ', '').replace('-', '')
        
        if phone_normalized != current_phone_normalized:
            # Phone number is being changed - check if new phone is already in use
            for existing_cnic, existing_patient in PATIENT_USERS.items():
                if existing_cnic != cnic:  # Don't check against self
                    existing_phone_normalized = existing_patient['phone'].replace(' ', '').replace('-', '')
                    if existing_phone_normalized == phone_normalized:
                        # New phone number already in use by another account
                        print(f'[PROFILE UPDATE FAILED] Duplicate phone number attempt: {phone}')
                        return jsonify({
                            'success': False,
                            'message': 'This phone number is already registered'
                        }), 409
        
        # Update patient profile
        PATIENT_USERS[cnic]['full_name'] = full_name
        PATIENT_USERS[cnic]['phone'] = phone
        
        # Update session if user is currently logged in
        if 'patient_cnic' in session and session['patient_cnic'] == cnic:
            session['patient_name'] = full_name
            session['patient_phone'] = phone
        
        print(f'[PATIENT PROFILE UPDATE] {full_name} ({cnic}) profile updated - Phone: {phone}')
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200
    
    except Exception as e:
        print(f'[ERROR] Profile update error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Server error during profile update'
        }), 500
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200
    
    except Exception as e:
        print(f'[ERROR] Profile update error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Server error during profile update'
        }), 500

# ==================== DRIVER LOGIN ROUTE ====================
@app.route('/driver-login', methods=['GET', 'POST'])
def driver_login():
    """
    Handle driver authentication and login
    - Uses username (DRV-001 format) and 6-digit password
    - Creates session for authenticated drivers
    
    @route GET /driver-login : Show login form
    @route POST /driver-login : Process login
    @return Rendered template or redirect
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Find driver by username (DRV-001 format)
        authenticated_driver = None
        authenticated_driver_id = None
        
        for driver_id, driver_info in DRIVERS.items():
            if driver_info.get('username') == username and driver_info.get('password') == password:
                authenticated_driver = driver_info
                authenticated_driver_id = driver_id
                break
        
        if authenticated_driver:
            # Create session
            session['user_type'] = 'driver'
            session['username'] = authenticated_driver_id  # Store driver ID
            session['driver_username'] = username  # Store the DRV-xxx format for display
            session['name'] = authenticated_driver['name']
            session['ambulance'] = authenticated_driver.get('assigned_ambulance')
            session['hospital'] = authenticated_driver.get('hospital')
            
            print(f'[DRIVER LOGIN] {username} ({authenticated_driver["name"]}) logged in')
            return redirect(url_for('driver_dashboard'))
        else:
            # Show demo users (DRV-xxx format)
            demo_users = [f"{driver_info.get('username', 'UNKNOWN')} ({driver_info.get('name', 'Unknown')})" for driver_info in DRIVERS.values()]
            return render_template('driver_login.html', 
                                   error='Invalid username or password',
                                   demo_users=demo_users)
    
    # GET request - show login form with demo credentials
    demo_users = [f"{driver_info.get('username', 'UNKNOWN')} ({driver_info.get('name', 'Unknown')})" for driver_info in DRIVERS.values()]
    return render_template('driver_login.html', demo_users=demo_users)

# ==================== DRIVER DASHBOARD ====================
@app.route('/driver-dashboard')
def driver_dashboard():
    """
    Display driver dashboard (requires authentication)
    - Shows active assignments
    - Route information
    - Real-time tracking
    
    @route GET /driver-dashboard
    @return Rendered driver dashboard
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return redirect(url_for('driver_login'))
    
    username = session.get('username')
    driver_info = DRIVERS.get(username, {})
    
    # Find active assignment for this driver
    active_assignment = None
    assignment_status_step = 0
    
    for req_id, req_data in PATIENT_REQUESTS.items():
        if req_data.get('assigned_driver') == username and req_data.get('status') != 'completed':
            active_assignment = req_data
            assignment_status_step = req_data.get('status_step', 0)
            break
    
    # Count completed trips today
    completed_today = sum(1 for req_id, req_data in PATIENT_REQUESTS.items() 
                         if req_data.get('assigned_driver') == username and req_data.get('status') == 'completed')
    
    # Dashboard data with active assignment
    dashboard_data = {
        'driver_name': driver_info.get('name'),
        'ambulance_id': driver_info.get('assigned_ambulance'),
        'status': driver_info.get('status', 'Available'),
        'current_location': 'Main Station',
        'active_calls': 1 if active_assignment else 0,
        'completed_today': completed_today,
        'response_time_avg': '6.2 minutes',
        'active_assignment': active_assignment,
        'assignment_status_step': assignment_status_step,
        # Driver details
        'phone': driver_info.get('phone'),
        'experience': driver_info.get('experience_years'),
        'license': driver_info.get('license'),
        'hospital_name': driver_info.get('hospital_name'),
        'vehicle_type': driver_info.get('vehicle_type'),
        'certifications': driver_info.get('certifications', [])
    }
    
    return render_template('driver_dashboard.html', data=dashboard_data)

# ==================== DRIVER CHANGE PASSWORD ====================
@app.route('/driver-change-password', methods=['POST'])
def driver_change_password():
    """
    Change driver password
    - Requires driver session
    - Verify old password matches current password in DRIVERS dict
    - Update to new password
    
    @route POST /driver-change-password
    @param old_password: Current password to verify
    @param new_password: New password to set
    @return JSON response with success/error
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        driver_id = session.get('username')
        if driver_id not in DRIVERS:
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        data = request.get_json() if request.is_json else request.form.to_dict()
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        # Validate inputs
        if not old_password or not new_password:
            return jsonify({'status': 'error', 'message': 'Both passwords are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters'}), 400
        
        driver = DRIVERS[driver_id]
        
        # Verify old password
        if driver.get('password') != old_password:
            return jsonify({'status': 'error', 'message': 'Old password is incorrect'}), 401
        
        # Update password
        driver['password'] = new_password
        
        driver_name = driver.get('name', driver_id)
        driver_username = driver.get('username', 'Unknown')
        
        print(f'[DRIVER PASSWORD CHANGE] Driver {driver_username} ({driver_name}) changed password')
        
        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        print(f'[ERROR] driver_change_password: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOSPITAL LOGIN ROUTE ====================
@app.route('/hospital-login', methods=['GET', 'POST'])
def hospital_login():
    """
    Handle hospital staff authentication and login
    - Dummy authentication for hospital staff
    - Creates session for authenticated hospitals
    
    @route GET /hospital-login : Show login form
    @route POST /hospital-login : Process login
    @return Rendered template or redirect
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate credentials (dummy authentication)
        if username in HOSPITALS and HOSPITALS[username]['password'] == password:
            # Create session
            session['user_type'] = 'hospital'
            session['username'] = username
            session['hospital_name'] = HOSPITALS[username]['name']
            session['total_beds'] = HOSPITALS[username]['beds']
            
            print(f'[HOSPITAL LOGIN] {username} ({HOSPITALS[username]["name"]}) logged in')
            return redirect(url_for('hospital_dashboard'))
        else:
            return render_template('hospital_login.html',
                                   error='Invalid username or password',
                                   demo_users=list(HOSPITALS.keys()))
    
    # GET request - show login form with demo credentials
    return render_template('hospital_login.html', demo_users=list(HOSPITALS.keys()))

# ==================== HOSPITAL DASHBOARD ====================
@app.route('/hospital-dashboard')
def hospital_dashboard():
    """
    Display hospital management dashboard (requires authentication)
    - Real-time ambulance status
    - Incoming patients
    - Bed availability
    - Emergency cases
    
    @route GET /hospital-dashboard
    @return Rendered hospital dashboard
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return redirect(url_for('hospital_login'))
    
    username = session.get('username')
    hospital_info = HOSPITALS.get(username, {})
    
    # Get assigned drivers info
    assigned_drivers = []
    for driver_id in hospital_info.get('drivers_assigned', []):
        if driver_id in DRIVERS:
            driver = DRIVERS[driver_id].copy()
            assigned_drivers.append({
                'username': driver_id,
                'name': driver.get('name'),
                'ambulance': driver.get('ambulance'),
                'status': driver.get('status'),
                'phone': driver.get('phone'),
                'experience': driver.get('experience_years')
            })
    
    # Dummy hospital data
    dashboard_data = {
        'hospital_name': hospital_info.get('name'),
        'hospital_address': hospital_info.get('address'),
        'hospital_phone': hospital_info.get('phone'),
        'hospital_email': hospital_info.get('email'),
        'total_beds': hospital_info.get('beds'),
        'available_beds': 43,
        'occupied_beds': 157,
        'incoming_ambulances': 3,
        'emergency_cases': 2,
        'average_response': '5.8 minutes',
        'assigned_drivers': assigned_drivers,
        'ambulances_in_area': [
            {'id': 'SA-001', 'status': 'En Route', 'eta': '4 min'},
            {'id': 'SA-002', 'status': 'Available', 'eta': '-'},
            {'id': 'SA-003', 'status': 'En Route', 'eta': '7 min'}
        ],
        'specialties': hospital_info.get('specialties', [])
    }
    
    return render_template('hospital_dashboard.html', data=dashboard_data)

# ==================== HOSPITAL API ROUTES ====================

@app.route('/get-hospital-requests', methods=['GET'])
def get_hospital_requests():
    """
    Get all patient requests for the logged-in hospital
    - Filters PATIENT_REQUESTS by hospital name
    - Returns JSON array of requests
    
    @route GET /get-hospital-requests
    @return JSON array of requests for the hospital
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    username = session.get('username')
    hospital_info = HOSPITALS.get(username, {})
    hospital_name = hospital_info.get('name')
    
    # Filter requests by hospital name
    hospital_requests = []
    for req_id, req_data in PATIENT_REQUESTS.items():
        if req_data.get('hospital') == hospital_name:
            hospital_requests.append(req_data)
    
    print(f'[GET REQUESTS] Hospital {hospital_name} requested {len(hospital_requests)} requests')
    return jsonify({
        'status': 'success',
        'hospital': hospital_name,
        'count': len(hospital_requests),
        'requests': hospital_requests
    }), 200

@app.route('/accept-request', methods=['POST'])
def accept_request():
    """
    Accept an incoming patient request and assign ambulance
    - Changes request status to 'accepted'
    - Assigns the nearest available ambulance
    - Locks the request for the assigned driver
    
    @route POST /accept-request
    @param request_id: ID of the request to accept
    @return JSON response with updated request
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        request_id = data.get('request_id')
        
        if not request_id or request_id not in PATIENT_REQUESTS:
            return jsonify({'error': 'Request not found', 'status': 404}), 404
        
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        # Get the request
        req = PATIENT_REQUESTS[request_id]
        
        # Verify request belongs to this hospital
        if req.get('hospital') != hospital_name:
            return jsonify({'error': 'Request does not belong to this hospital', 'status': 403}), 403
        
        # Check if already accepted/completed
        if req['status'] not in ['pending', 'accepted']:
            return jsonify({'error': f'Cannot accept request with status: {req["status"]}', 'status': 400}), 400
        
        # Find first available driver from DRIVERS dict (not from hospital_info)
        assigned_driver = None
        for driver_id, driver_info in DRIVERS.items():
            if driver_info.get('hospital') == username and driver_info.get('status') == 'Available':
                assigned_driver = driver_id
                break
        
        if not assigned_driver:
            return jsonify({'error': 'No available drivers', 'status': 400}), 400
        
        # Update request and driver status
        with request_lock:
            req['status'] = 'accepted'
            req['assigned_driver'] = assigned_driver
            req['locked'] = True
            req['locked_by'] = assigned_driver
            req['locked_at'] = datetime.now().isoformat()
            req['status_step'] = 1
            
            # Update driver status to On Duty
            driver = DRIVERS.get(assigned_driver, {})
            driver['status'] = 'On Duty'
            
            # Create dispatch entry
            dispatch_id = f"DSP-2026-{len(DISPATCHES) + 1:03d}"
            DISPATCHES[dispatch_id] = {
                'id': dispatch_id,
                'request_id': request_id,
                'patient_name': req.get('patient_name'),
                'patient_phone': req.get('patient_phone'),
                'location': req.get('pickup_address'),
                'assigned_driver': assigned_driver,
                'driver_name': driver.get('name'),
                'ambulance_id': driver.get('ambulance'),
                'hospital': hospital_name,
                'status': 'dispatched',  # dispatched, picked_up, completed
                'timestamp': datetime.now().isoformat(),
                'priority': req.get('priority', 'Medium')
            }
            print(f'[CREATE DISPATCH] {dispatch_id} created for {req.get("patient_name")}')
        
        driver_name = driver.get('name', assigned_driver)
        print(f'[ACCEPT REQUEST] {request_id} accepted and assigned to {driver_name} - status changed to On Duty')
        
        return jsonify({
            'status': 'success',
            'message': f'Request accepted and assigned to {driver_name}',
            'request': req,
            'assigned_driver': assigned_driver,
            'dispatch_id': dispatch_id,
            'driver_info': {
                'id': assigned_driver,
                'name': driver_name,
                'phone': driver.get('phone'),
                'ambulance': driver.get('ambulance'),
                'status': 'On Duty'
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/reject-request', methods=['POST'])
def reject_request():
    """
    Reject an incoming patient request
    - Adds current hospital to rejected_by list
    - Finds next nearest hospital with available beds and ambulances
    - Reassigns request to next nearest hospital (resets timer)
    - Only marks as rejected if ALL hospitals have rejected it
    
    @route POST /reject-request
    @param request_id: ID of the request to reject
    @return JSON response with reassignment info
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        request_id = data.get('request_id')
        
        if not request_id or request_id not in PATIENT_REQUESTS:
            return jsonify({'error': 'Request not found', 'status': 404}), 404
        
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        # Get the request
        req = PATIENT_REQUESTS[request_id]
        
        # Verify request belongs to this hospital
        if req.get('hospital') != hospital_name:
            return jsonify({'error': 'Request does not belong to this hospital', 'status': 403}), 403
        
        # Check if can be rejected
        if req['status'] in ['completed']:
            return jsonify({'error': f'Cannot reject request with status: {req["status"]}', 'status': 400}), 400
        
        # Get assigned driver to release them
        assigned_driver = req.get('assigned_driver')
        
        # Add current hospital to rejected_by list
        with request_lock:
            if hospital_name not in req.get('rejected_by', []):
                req['rejected_by'].append(hospital_name)
            
            # Release driver back to Available if one was assigned
            if assigned_driver:
                driver = DRIVERS.get(assigned_driver, {})
                driver['status'] = 'Available'
                req['assigned_driver'] = None
            
            req['locked'] = False
            req['locked_by'] = None
            req['locked_at'] = None
        
        # Try to find next nearest hospital with available beds and ambulances
        next_hospital_username, next_hospital_info = find_next_nearest_hospital(hospital_name, request_id)
        
        if next_hospital_username and next_hospital_info:
            # Reassign to next nearest hospital
            next_hospital_name = next_hospital_info.get('name')
            
            with request_lock:
                req['hospital'] = next_hospital_name
                req['status'] = 'pending'  # Reset to pending for new hospital
                req['status_step'] = 0
                # Reset timer by resetting timestamp (optionally can add explicit timer logic)
            
            print(f'[REJECT REQUEST] {request_id} rejected by {hospital_name}, reassigned to {next_hospital_name}')
            print(f'[REASSIGN] Request forwarded to nearest hospital: {next_hospital_name}')
            
            return jsonify({
                'status': 'success',
                'message': f'Request forwarded to next nearest hospital: {next_hospital_name}',
                'reassigned': True,
                'next_hospital': next_hospital_name,
                'request': req
            }), 200
        else:
            # No other hospitals available - must reject this request
            with request_lock:
                req['status'] = 'rejected'
            
            print(f'[REJECT REQUEST] {request_id} fully rejected - no other hospitals available')
            
            return jsonify({
                'status': 'success',
                'message': 'No hospitals available. Request marked as rejected.',
                'reassigned': False,
                'request': req
            }), 200
    
    except Exception as e:
        print(f'[ERROR] reject_request: {str(e)}')
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/update-beds', methods=['POST'])
def update_beds():
    """
    Update available beds count for the hospital
    - Updates the available_beds count in HOSPITALS dict
    - Can be adjusted up or down based on patient intake/discharge
    
    @route POST /update-beds
    @param available_beds: Number of available beds (integer)
    @return JSON response with updated bed count
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        available_beds = data.get('available_beds')
        
        if available_beds is None:
            return jsonify({'error': 'available_beds parameter required', 'status': 400}), 400
        
        try:
            available_beds = int(available_beds)
        except (ValueError, TypeError):
            return jsonify({'error': 'available_beds must be an integer', 'status': 400}), 400
        
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        
        if not hospital_info:
            return jsonify({'error': 'Hospital not found', 'status': 404}), 404
        
        # Validate bed count
        total_beds = hospital_info.get('beds', 0)
        if available_beds < 0 or available_beds > total_beds:
            return jsonify({
                'error': f'Invalid bed count. Must be between 0 and {total_beds}',
                'status': 400
            }), 400
        
        # Update beds
        hospital_info['available_beds'] = available_beds
        hospital_info['occupied_beds'] = total_beds - available_beds
        
        print(f'[UPDATE BEDS] Hospital {hospital_info.get("name")} updated beds to {available_beds}/{total_beds}')
        
        return jsonify({
            'status': 'success',
            'message': f'Beds updated successfully',
            'hospital': hospital_info.get('name'),
            'available_beds': available_beds,
            'occupied_beds': hospital_info['occupied_beds'],
            'total_beds': total_beds
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/update-dispatch-status', methods=['POST'])
def update_dispatch_status():
    """
    Update dispatch/request status from driver dashboard
    - Changes status: en_route, picked_up, completed
    - Called by drivers when updating dispatch progress
    - Updates the underlying patient request status
    
    @route POST /update-dispatch-status
    @param status: New status (en_route, picked_up, completed)
    @return JSON response with updated request
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        new_status = data.get('status', '').lower()
        driver_id = session.get('username')
        
        # Find active request for this driver
        request_id = None
        for req_id, req_data in PATIENT_REQUESTS.items():
            if req_data.get('assigned_driver') == driver_id and req_data.get('status') != 'completed':
                request_id = req_id
                break
        
        if not request_id:
            return jsonify({'status': 'error', 'message': 'No active request found'}), 404
        
        valid_statuses = ['en_route', 'picked_up', 'completed']
        if new_status not in valid_statuses:
            return jsonify({'status': 'error', 'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        req = PATIENT_REQUESTS[request_id]
        old_status = req.get('status')
        
        # Status progression mapping
        status_map = {
            'accepted': 1,
            'en_route': 2,
            'picked_up': 3,
            'completed': 4
        }
        
        with request_lock:
            req['status'] = new_status
            req['status_step'] = status_map.get(new_status, 0)
        
        driver_info = DRIVERS.get(driver_id, {})
        driver_name = driver_info.get('name', driver_id)
        
        print(f'[UPDATE DISPATCH] Request {request_id} status updated from {old_status} to {new_status} by {driver_name}')
        
        return jsonify({
            'status': 'success',
            'message': f'Dispatch status updated to {new_status}',
            'request_id': request_id,
            'request': req
        }), 200
    
    except Exception as e:
        print(f'[ERROR] update_dispatch_status: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get-ambulances', methods=['GET'])
def get_ambulances():
    """
    Get all ambulances for the logged-in hospital with their assigned drivers
    - Returns ambulances with type, status, and list of drivers assigned to each
    
    @route GET /get-ambulances
    @return JSON array of ambulances for the hospital with driver assignments
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        # Get all ambulances for this hospital
        ambulances_list = []
        for ambulance_id, ambulance_data in AMBULANCES.items():
            if ambulance_data.get('hospital') == username:
                # Get all drivers assigned to this ambulance
                drivers_assigned = []
                for driver_id, driver_info in DRIVERS.items():
                    if driver_info.get('assigned_ambulance') == ambulance_id:
                        drivers_assigned.append({
                            'id': driver_id,
                            'name': driver_info.get('name'),
                            'status': driver_info.get('status')
                        })
                
                ambulances_list.append({
                    'id': ambulance_data.get('id'),
                    'type': ambulance_data.get('type'),
                    'status': ambulance_data.get('status'),
                    'drivers_assigned': drivers_assigned
                })
        
        print(f'[GET AMBULANCES] Hospital {hospital_name} retrieved {len(ambulances_list)} ambulances')
        
        return jsonify({
            'status': 'success',
            'hospital': hospital_name,
            'count': len(ambulances_list),
            'ambulances': ambulances_list
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/get-drivers', methods=['GET'])
def get_drivers():
    """
    Get all drivers for the logged-in hospital with their ambulance assignments
    - Returns drivers with name, phone, cnic, experience, shift, assigned ambulance, and credentials
    
    @route GET /get-drivers
    @return JSON array of drivers for the hospital
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        # Get all drivers for this hospital
        drivers_list = []
        for driver_id, driver_info in DRIVERS.items():
            if driver_info.get('hospital') == username:
                drivers_list.append({
                    'id': driver_id,
                    'username': driver_info.get('username'),
                    'password': driver_info.get('password'),
                    'name': driver_info.get('name'),
                    'phone': driver_info.get('phone'),
                    'cnic': driver_info.get('cnic'),
                    'experience_years': driver_info.get('experience_years'),
                    'assigned_ambulance': driver_info.get('assigned_ambulance'),
                    'shift': driver_info.get('shift'),
                    'status': driver_info.get('status'),
                    'certifications': driver_info.get('certifications', [])
                })
        
        print(f'[GET DRIVERS] Hospital {hospital_name} retrieved {len(drivers_list)} drivers')
        
        return jsonify({
            'status': 'success',
            'hospital': hospital_name,
            'count': len(drivers_list),
            'drivers': drivers_list
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/get-dispatches', methods=['GET'])
def get_dispatches():
    """
    Get all dispatches for the logged-in hospital or driver
    - Hospital users: Returns dispatches assigned to their hospital
    - Driver users: Returns dispatches assigned to them
    - Returns dispatch status, patient info, location, and driver assignment
    
    @route GET /get-dispatches
    @return JSON array of dispatches
    """
    if 'user_type' not in session:
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        user_type = session.get('user_type')
        dispatches_list = []
        
        if user_type == 'hospital':
            # Get dispatches for this hospital
            username = session.get('username')
            hospital_info = HOSPITALS.get(username, {})
            hospital_name = hospital_info.get('name')
            
            # Filter dispatches by hospital
            for dispatch_id, dispatch in DISPATCHES.items():
                if dispatch.get('hospital') == hospital_name:
                    dispatches_list.append(dispatch)
            
            print(f'[GET DISPATCHES] Hospital {hospital_name} retrieved {len(dispatches_list)} dispatches')
            
            return jsonify({
                'status': 'success',
                'user_type': 'hospital',
                'hospital': hospital_name,
                'count': len(dispatches_list),
                'dispatches': dispatches_list
            }), 200
        
        elif user_type == 'driver':
            # Get dispatches for this driver
            username = session.get('username')
            driver_info = DRIVERS.get(username, {})
            driver_name = driver_info.get('name')
            
            # Filter dispatches by assigned driver
            for dispatch_id, dispatch in DISPATCHES.items():
                if dispatch.get('assigned_driver') == username or dispatch.get('driver_name') == driver_name:
                    dispatches_list.append(dispatch)
            
            print(f'[GET DISPATCHES] Driver {driver_name} retrieved {len(dispatches_list)} dispatches')
            
            return jsonify({
                'status': 'success',
                'user_type': 'driver',
                'driver': driver_name,
                'count': len(dispatches_list),
                'dispatches': dispatches_list
            }), 200
        
        else:
            return jsonify({'error': 'Invalid user type for dispatch retrieval', 'status': 403}), 403
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/get-hospital-stats', methods=['GET'])
def get_hospital_stats():
    """
    Get real-time hospital statistics for dashboard
    - Available beds and total beds
    - Total ambulances and currently assigned ambulances
    - Active emergencies count
    
    @route GET /get-hospital-stats
    @return JSON with hospital statistics
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        # Get bed information
        total_beds = hospital_info.get('beds', 0)
        available_beds = hospital_info.get('available_beds', int(total_beds * 0.3))
        occupied_beds = total_beds - available_beds
        occupancy_rate = int((occupied_beds / total_beds) * 100) if total_beds > 0 else 0
        
        # Get ambulance information from AMBULANCES dict (not hospital_info)
        total_ambulances = 0
        available_ambulances = 0
        for ambulance_id, ambulance_info in AMBULANCES.items():
            if ambulance_info.get('hospital') == username:
                total_ambulances += 1
                if ambulance_info.get('status') == 'Available':
                    available_ambulances += 1
        
        assigned_ambulances = total_ambulances - available_ambulances
        
        # Count active emergencies (pending + accepted)
        active_emergencies = 0
        for req_id, req_data in PATIENT_REQUESTS.items():
            if req_data.get('hospital') == hospital_name and req_data.get('status') in ['pending', 'accepted', 'en_route', 'picked_up']:
                active_emergencies += 1
        
        print(f'[GET STATS] Hospital {hospital_name}: {available_beds}/{total_beds} beds, {available_ambulances}/{total_ambulances} ambulances, {active_emergencies} active')
        
        return jsonify({
            'status': 'success',
            'hospital': hospital_name,
            'beds': {
                'total': total_beds,
                'available': available_beds,
                'occupied': occupied_beds,
                'occupancy_rate': occupancy_rate,
                'is_full': available_beds == 0
            },
            'ambulances': {
                'total': total_ambulances,
                'available': available_ambulances,
                'assigned': assigned_ambulances
            },
            'emergencies': active_emergencies
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/add-ambulance', methods=['POST'])
def add_ambulance():
    """
    Add a new ambulance to the hospital
    - Only creates entry in AMBULANCES dict
    - Does NOT create any driver
    
    @route POST /add-ambulance
    @param ambulance_id: Unique ambulance identifier (e.g., AL-006)
    @param type: Ambulance type (Basic or Advanced)
    @return JSON response with new ambulance info
    """
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        ambulance_id = data.get('ambulance_id', '').strip()
        ambulance_type = data.get('type', '').strip()
        
        if not ambulance_id or not ambulance_type:
            return jsonify({
                'error': 'Missing required fields: ambulance_id, type',
                'status': 400
            }), 400
        
        if ambulance_type not in ['Basic', 'Advanced']:
            return jsonify({
                'error': 'Type must be either Basic or Advanced',
                'status': 400
            }), 400
        
        username = session.get('username')
        hospital_info = HOSPITALS.get(username, {})
        hospital_name = hospital_info.get('name')
        
        if not hospital_info:
            return jsonify({'error': 'Hospital not found', 'status': 404}), 404
        
        # Check if ambulance already exists
        if ambulance_id in AMBULANCES:
            return jsonify({'error': f'Ambulance {ambulance_id} already exists', 'status': 400}), 400
        
        # Create new ambulance entry
        AMBULANCES[ambulance_id] = {
            'id': ambulance_id,
            'type': ambulance_type,
            'hospital': username,
            'status': 'Available'
        }
        
        print(f'[ADD AMBULANCE] Hospital {hospital_name} added ambulance {ambulance_id} (Type: {ambulance_type})')
        
        return jsonify({
            'status': 'success',
            'message': f'Ambulance {ambulance_id} added successfully',
            'ambulance_id': ambulance_id,
            'ambulance': AMBULANCES[ambulance_id]
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/add-driver', methods=['POST'])
def add_driver():
    """Add a new driver to the hospital with auto-generated credentials"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = session.get('username')
    if username not in HOSPITALS:
        return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
    
    try:
        data = request.get_json()
        driver_name = data.get('driver_name', '').strip()
        phone = data.get('phone', '').strip()
        cnic = data.get('cnic', '').strip()
        experience_years = int(data.get('experience_years', 0))
        shift = data.get('shift', 'Any').strip()
        assigned_ambulance = data.get('assigned_ambulance', None)
        
        if not all([driver_name, phone, cnic]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
        
        if experience_years < 0 or experience_years > 40:
            return jsonify({'status': 'error', 'message': 'Experience must be between 0 and 40 years'}), 400
        
        if shift not in ['Morning', 'Night', 'Any']:
            return jsonify({'status': 'error', 'message': 'Shift must be Morning, Night, or Any'}), 400
        
        # If ambulance specified, verify it exists and belongs to this hospital
        if assigned_ambulance:
            if assigned_ambulance not in AMBULANCES:
                return jsonify({'status': 'error', 'message': f'Ambulance {assigned_ambulance} not found'}), 404
            if AMBULANCES[assigned_ambulance]['hospital'] != username:
                return jsonify({'status': 'error', 'message': 'Ambulance does not belong to your hospital'}), 403
        
        # Generate new driver ID (internal, for database)
        existing_ids = [int(did.replace('driver', '')) for did in DRIVERS.keys() if did.startswith('driver')]
        new_driver_id = f'driver{max(existing_ids) + 1 if existing_ids else 1}'
        
        # Generate auto credentials for driver login
        # Username: DRV-001, DRV-002, etc. (count all drivers across all hospitals)
        all_drivers_count = len(DRIVERS) + 1
        driver_username = f'DRV-{str(all_drivers_count).zfill(3)}'
        driver_password = str(random.randint(100000, 999999))
        
        # Create new driver entry
        DRIVERS[new_driver_id] = {
            'username': driver_username,
            'password': driver_password,
            'name': driver_name,
            'phone': phone,
            'cnic': cnic,
            'experience_years': experience_years,
            'assigned_ambulance': assigned_ambulance,
            'shift': shift,
            'hospital': username,
            'status': 'Available',
            'certifications': ['Basic EMT']
        }
        
        print(f'[ADD DRIVER] Hospital {HOSPITALS[username]["name"]} added driver {new_driver_id} ({driver_name}) with username {driver_username}')
        
        return jsonify({
            'status': 'success',
            'message': f'Driver {driver_name} added successfully',
            'driver_id': new_driver_id,
            'driver_username': driver_username,
            'driver_password': driver_password,
            'driver': DRIVERS[new_driver_id]
        }), 201
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/remove-driver', methods=['POST'])
def remove_driver():
    """Remove a driver from the system - only removes driver, ambulance stays untouched"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = session.get('username')
    if username not in HOSPITALS:
        return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
    
    try:
        data = request.get_json()
        driver_id = data.get('driver_id', '').strip()
        
        if not driver_id or driver_id not in DRIVERS:
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        # Check if driver belongs to the hospital
        if DRIVERS[driver_id]['hospital'] != username:
            return jsonify({'status': 'error', 'message': 'Driver does not belong to your hospital'}), 403
        
        driver_name = DRIVERS[driver_id]['name']
        
        # Remove driver from DRIVERS dict only - do NOT touch ambulance
        del DRIVERS[driver_id]
        
        print(f'[REMOVE DRIVER] Hospital {HOSPITALS[username]["name"]} removed driver {driver_id} ({driver_name})')
        
        return jsonify({
            'status': 'success',
            'message': f'Driver {driver_name} removed successfully'
        }), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/remove-ambulance', methods=['POST'])
def remove_ambulance():
    """Remove an ambulance from the system - clears assigned_ambulance for all drivers who had it"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = session.get('username')
    if username not in HOSPITALS:
        return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
    
    try:
        data = request.get_json()
        ambulance_id = data.get('ambulance_id', '').strip()
        
        if not ambulance_id:
            return jsonify({'status': 'error', 'message': 'Ambulance ID is required'}), 400
        
        if ambulance_id not in AMBULANCES:
            return jsonify({'status': 'error', 'message': 'Ambulance not found'}), 404
        
        # Verify ambulance belongs to this hospital
        if AMBULANCES[ambulance_id]['hospital'] != username:
            return jsonify({'status': 'error', 'message': 'Ambulance does not belong to your hospital'}), 403
        
        # Remove ambulance from AMBULANCES dict
        del AMBULANCES[ambulance_id]
        
        # Set assigned_ambulance to None for all drivers who had this ambulance
        for driver_id, driver_info in DRIVERS.items():
            if driver_info.get('assigned_ambulance') == ambulance_id:
                driver_info['assigned_ambulance'] = None
        
        print(f'[REMOVE AMBULANCE] Hospital {HOSPITALS[username]["name"]} removed ambulance {ambulance_id}')
        
        return jsonify({
            'status': 'success',
            'message': f'Ambulance {ambulance_id} removed successfully'
        }), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/change-driver-password', methods=['POST'])
def change_driver_password():
    """Change a driver's password (hospital only)"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    username = session.get('username')
    if username not in HOSPITALS:
        return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
    
    try:
        data = request.get_json()
        driver_id = data.get('driver_id', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not driver_id or not new_password:
            return jsonify({'status': 'error', 'message': 'Driver ID and new password are required'}), 400
        
        if driver_id not in DRIVERS:
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        # Verify driver belongs to this hospital
        if DRIVERS[driver_id]['hospital'] != username:
            return jsonify({'status': 'error', 'message': 'Driver does not belong to your hospital'}), 403
        
        # Update password
        old_password = DRIVERS[driver_id]['password']
        DRIVERS[driver_id]['password'] = new_password
        
        driver_username = DRIVERS[driver_id]['username']
        driver_name = DRIVERS[driver_id]['name']
        
        print(f'[CHANGE PASSWORD] Hospital {HOSPITALS[username]["name"]} changed password for {driver_username} ({driver_name})')
        
        return jsonify({
            'status': 'success',
            'message': f'Password changed successfully for {driver_username}',
            'driver_username': driver_username,
            'new_password': new_password
        }), 200
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== LOGOUT ROUTE ====================
@app.route('/logout')
def logout():
    """
    Clear session and logout user
    @route GET /logout
    @return Redirect to home
    """
    username = session.get('username', 'Unknown')
    user_type = session.get('user_type', 'unknown')
    print(f'[LOGOUT] {user_type} user {username} logged out')
    
    session.clear()
    return redirect(url_for('home'))

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def page_not_found(error):
    """
    Handle 404 - Page Not Found
    @return Error page
    """
    return jsonify({'error': 'Page not found', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 - Internal Server Error
    @return Error page
    """
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

# ==================== APPLICATION ENTRY POINT ====================
if __name__ == '__main__':
    print('\n' + '='*60)
    print('  SMARTAMBULANCE - Emergency Routing System')
    print('  AI-Driven Emergency Ambulance Routing')
    print('='*60)
    print('\n  Routes:')
    print('  - Home           : http://localhost:5000/')
    print('  - Emergency      : http://localhost:5000/emergency')
    print('  - Driver Login   : http://localhost:5000/driver-login')
    print('  - Hospital Login : http://localhost:5000/hospital-login')
    print('\n  Demo Credentials:')
    print('  - Driver   : username=driver1, password=pass123')
    print('  - Hospital : username=hospital1, password=pass123')
    print('\n' + '='*60 + '\n')
    
    # Run Flask development server
    app.run(debug=True, host='localhost', port=5000)