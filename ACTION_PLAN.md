# SMART AMBULANCE FYP - ACTION PLAN & IMPLEMENTATION ROADMAP
**Timeline:** 3-4 weeks to production-ready submission  
**Target Grade:** 90-95% (A)

---

## 📅 PHASE 1: CRITICAL FIXES (WEEK 1-2) — REQUIRED FOR SUBMISSION

### 1. ✅ Implement Machine Learning Component
**Status:** ❌ NOT STARTED  
**Priority:** 🔴 CRITICAL  
**Effort:** 40 hours  
**Deadline:** End of Week 1

#### What's Missing:
The project claims "**AI-Driven**" routing but has **ZERO** ML code. This will be the first question in your viva.

#### Implementation Tasks:

**A) Demand Prediction Model** (20 hours)
```
Task A1: Create time-series forecasting
- Analyze historical request patterns
- Implement ARIMA or Prophet model
- Predict hourly request volume
- Integrate with hospital allocation

File to create: `ml_demand_model.py`

Algorithm:
# Time slot analysis: Which hours get most requests?
# Weekend vs weekday patterns
# Seasonal trends
# Use scikit-learn or statsmodels
```

**Code Example:**
```python
# ml/demand_model.py
from sklearn.ensemble import RandomForestRegressor
import numpy as np

class DemandPredictor:
    """Predict ambulance demand by time of day"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.trained = False
    
    def train(self, historical_data):
        """
        historical_data: DataFrame with columns:
        - hour: 0-23
        - day_of_week: 0-6
        - request_count: actual requests
        """
        X = historical_data[['hour', 'day_of_week']].values
        y = historical_data['request_count'].values
        self.model.fit(X, y)
        self.trained = True
    
    def predict(self, hour, day_of_week):
        """Predict requests for given hour"""
        if not self.trained:
            return 5  # Default fallback
        return max(1, int(self.model.predict([[hour, day_of_week]])[0]))
```

**B) Route Optimization Algorithm** (20 hours)
```
Task B1: Nearest-Neighbor + Time-Window Algorithm
- Find closest available ambulance to patient
- Check ambulance ETA to patient
- Verify hospital has capacity when ambulance arrives
- Assign to minimize total response time

File to create: `ml_route_optimizer.py`

Algorithm:
1. Filter ambulances within 15km radius
2. For each ambulance:
   - Calculate distance to patient
   - Calculate distance to closest hospital
   - Estimate ETA = distance / avg_speed
3. Filter hospitals with available beds
4. Pick ambulance → hospital combo with lowest total time
```

**Code Example:**
```python
# ml/route_optimizer.py
from math import radians, sin, cos, sqrt, atan2

class RouteOptimizer:
    """Optimize ambulance assignment to minimize ETA"""
    
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points (km)"""
        R = 6371  # Earth radius in km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    def find_optimal_ambulance(self, patient_lat, patient_lon, 
                               available_ambulances, hospitals):
        """
        Find ambulance + hospital combo with lowest ETA
        
        Args:
            patient_lat, patient_lon: Emergency location
            available_ambulances: List of {id, lat, lon, status}
            hospitals: List of {id, lat, lon, available_beds}
        
        Returns:
            {ambulance_id, hospital_id, estimated_eta}
        """
        best_option = None
        best_eta = float('inf')
        
        for ambulance in available_ambulances:
            # Step 1: Distance from ambulance to patient
            dist_to_patient = self.haversine_distance(
                ambulance['lat'], ambulance['lon'],
                patient_lat, patient_lon
            )
            
            # Step 2: Find nearest hospital with beds
            for hospital in hospitals:
                if hospital['available_beds'] > 0:
                    dist_to_hospital = self.haversine_distance(
                        patient_lat, patient_lon,
                        hospital['lat'], hospital['lon']
                    )
                    
                    # Assume average speed of 40 km/h in emergency
                    eta_minutes = (dist_to_patient + dist_to_hospital) / 40 * 60
                    
                    if eta_minutes < best_eta:
                        best_eta = eta_minutes
                        best_option = {
                            'ambulance_id': ambulance['id'],
                            'hospital_id': hospital['id'],
                            'estimated_eta': eta_minutes
                        }
        
        return best_option
```

**Integration with Flask:**
```python
# In app.py, modify dispatch logic

from ml.route_optimizer import RouteOptimizer
from ml.demand_model import DemandPredictor

optimizer = RouteOptimizer()
demand_model = DemandPredictor()

@app.route('/dispatch', methods=['POST'])
def dispatch():
    """Create emergency request with optimized ambulance assignment"""
    
    patient_lat = request.json['lat']
    patient_lon = request.json['lon']
    
    # Get available ambulances within 15km
    available = get_available_ambulances(patient_lat, patient_lon)
    
    # Get hospitals with capacity
    hospitals_with_beds = get_hospitals_with_available_beds()
    
    # Use ML to find optimal assignment
    optimal_assignment = optimizer.find_optimal_ambulance(
        patient_lat, patient_lon,
        available, hospitals_with_beds
    )
    
    if optimal_assignment:
        ambulance_id = optimal_assignment['ambulance_id']
        hospital_id = optimal_assignment['hospital_id']
        eta = optimal_assignment['estimated_eta']
        
        # Create request with optimal assignment
        # Log ML decision for analysis
        log_ml_decision(ambulance_id, hospital_id, eta)
    else:
        # Fallback if no optimal route found
        ambulance_id = available[0]['id']
    
    # ... rest of dispatch logic
```

#### Documentation to Add:
Create a file: `ML_IMPLEMENTATION.md` with:
- Algorithm explanation
- Training data requirements
- Accuracy metrics
- Comparison with baseline (simple greedy approach)

---

### 2. ✅ Create Comprehensive Test Suite
**Status:** ❌ NEEDS COMPLETE OVERHAUL  
**Priority:** 🔴 CRITICAL  
**Effort:** 30 hours  
**Deadline:** End of Week 1

#### Current Issue:
- 14 test files but disorganized
- No test framework consistency
- No coverage metrics
- Tests are manual, not automated

#### Tasks:

**A) Set Up pytest** (3 hours)
```bash
pip install pytest pytest-cov pytest-mock

# Create structure:
tests/
├── __init__.py
├── conftest.py  # Shared fixtures
├── test_auth.py
├── test_driver.py
├── test_hospital.py
├── test_emergency.py
├── test_db.py
└── test_api.py
```

**B) Authentication Tests** (6 hours)
```python
# tests/test_auth.py
import pytest
from app import app, get_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestDriverLogin:
    """Test driver authentication"""
    
    def test_login_success(self, client):
        """Valid credentials should redirect to dashboard"""
        response = client.post('/driver-login', 
            data={'username': 'DRV-001', 'password': 'pass123'},
            follow_redirects=True)
        assert response.status_code == 200
        assert b'driver-dashboard' in response.data
    
    def test_login_invalid_username(self, client):
        """Invalid username should show error"""
        response = client.post('/driver-login',
            data={'username': 'INVALID', 'password': 'pass123'})
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data
    
    def test_login_empty_fields(self, client):
        """Empty fields should show error"""
        response = client.post('/driver-login',
            data={'username': '', 'password': ''})
        assert b'required' in response.data.lower()
    
    def test_logout(self, client):
        """Logout should clear session"""
        client.post('/driver-login',
            data={'username': 'DRV-001', 'password': 'pass123'})
        response = client.get('/logout', follow_redirects=True)
        assert b'Login' in response.data

class TestHospitalLogin:
    """Test hospital authentication"""
    # Similar tests as above
```

**C) Emergency Dispatch Tests** (8 hours)
```python
# tests/test_emergency.py
class TestEmergencyDispatch:
    """Test emergency request creation and dispatch"""
    
    def test_create_emergency_request_success(self, client):
        """Creating emergency should create DB record"""
        response = client.post('/emergency',
            json={
                'patient_name': 'Test Patient',
                'patient_phone': '971501234567',
                'lat': 25.2048,
                'lon': 55.2708,
                'symptoms': 'Chest pain',
                'priority': 'High'
            })
        assert response.status_code == 201
        data = response.get_json()
        assert 'request_id' in data
    
    def test_create_emergency_missing_fields(self, client):
        """Missing required fields should return 400"""
        response = client.post('/emergency', json={
            'patient_name': 'Test'  # Missing other fields
        })
        assert response.status_code == 400
    
    def test_dispatch_selects_closest_ambulance(self, client):
        """Dispatch should select ambulance with best ETA"""
        # Create request and verify correct ambulance assigned
        pass
    
    def test_nearby_hospitals_returned(self, client):
        """Should return hospitals within radius"""
        pass
    
    def test_request_locking_mechanism(self, client):
        """Request should lock when driver accepts"""
        pass
```

**D) Database Tests** (6 hours)
```python
# tests/test_db.py
class TestDatabaseSchema:
    """Verify database schema integrity"""
    
    def test_hospitals_table_exists(self):
        """Hospitals table should exist with correct columns"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DESCRIBE hospitals")
        columns = [col[0] for col in cursor.fetchall()]
        assert 'id' in columns
        assert 'username' in columns
        assert 'available_beds' in columns
    
    def test_foreign_key_constraints(self):
        """Foreign keys should be enforced"""
        # Try to insert invalid hospital_id → should fail
        pass
    
    def test_cascade_delete(self):
        """Deleting hospital should delete related records"""
        pass

class TestDataIntegrity:
    """Verify data consistency"""
    
    def test_bed_count_never_negative(self):
        """available_beds should never go below 0"""
        pass
    
    def test_request_status_valid_values(self):
        """Request status should be one of valid statuses"""
        pass
```

**E) Generate Coverage Report** (2 hours)
```bash
# Run tests with coverage
pytest tests/ --cov=. --cov-report=html

# Should generate htmlcov/index.html showing:
# - Overall coverage (target: 70%+)
# - File-by-file breakdown
# - Lines covered vs. missed
```

#### Target Coverage Metrics:
```
Target: 70%+ overall
- app.py routes: 80%
- Database functions: 85%
- Authentication: 90%
- Emergency dispatch: 85%
```

---

### 3. ✅ Security Hardening
**Status:** ⚠️ PARTIALLY ADDRESSED  
**Priority:** 🔴 CRITICAL  
**Effort:** 15 hours  
**Deadline:** Middle of Week 1

#### Critical Fixes:

**A) Password Hashing** (3 hours)
```python
# Install required package
pip install werkzeug

# Update user creation (EVERYWHERE passwords are stored)
from werkzeug.security import generate_password_hash, check_password_hash

# When creating/updating password:
password_hash = generate_password_hash('plaintext_password', 
                                      method='pbkdf2:sha256')
cursor.execute("UPDATE drivers SET password = %s WHERE id = %s",
               (password_hash, driver_id))

# When checking password during login:
stored_hash = cursor.fetchone()['password']
if check_password_hash(stored_hash, provided_password):
    # Login successful
else:
    # Login failed
```

**B) Environment Variables** (3 hours)
```python
# Install python-dotenv
pip install python-dotenv

# Create .env file (add to .gitignore)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_actual_password
DB_NAME=smartambulance
SECRET_KEY=your_secret_key_here

# Update app.py
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
app.secret_key = os.getenv('SECRET_KEY')
```

**C) HTTPS in Development** (3 hours)
```python
# For development testing only
pip install pyopenssl

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Run Flask with SSL
if __name__ == "__main__":
    app.run(ssl_context=('cert.pem', 'key.pem'))
```

**D) Input Validation** (3 hours)
```python
# Add to all endpoints
from flask import escape
import re

def validate_phone(phone):
    """Validate phone number format"""
    pattern = r'^\+?[1-9]\d{1,14}$'  # E.164 format
    return re.match(pattern, phone) is not None

def validate_coordinates(lat, lon):
    """Validate latitude/longitude"""
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except ValueError:
        return False

# In endpoints:
@app.route('/emergency', methods=['POST'])
def emergency():
    data = request.json
    
    # Validate phone
    if not validate_phone(data.get('patient_phone')):
        return {'error': 'Invalid phone format'}, 400
    
    # Validate location
    if not validate_coordinates(data.get('lat'), data.get('lon')):
        return {'error': 'Invalid coordinates'}, 400
    
    # Sanitize text inputs
    patient_name = escape(data.get('patient_name', ''))
    
    # ... rest of logic
```

**E) Rate Limiting** (3 hours)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/driver-login', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent brute force
def driver_login():
    # ... login logic
```

#### Security Checklist:
- [ ] All passwords hashed with bcrypt/pbkdf2
- [ ] Database credentials in .env file
- [ ] Input validation on all endpoints
- [ ] Rate limiting on auth endpoints
- [ ] HTTPS in development version
- [ ] No sensitive data in logs
- [ ] SQL injection protection (already using parameterized queries ✓)
- [ ] CSRF token validation (if using forms)

---

### 4. ✅ Create API Documentation
**Status:** ❌ NOT STARTED  
**Priority:** 🔴 CRITICAL  
**Effort:** 20 hours  
**Deadline:** End of Week 1

#### Option A: Swagger/OpenAPI (15 hours)
```python
pip install flask-swagger-ui flasgger

from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/emergency', methods=['POST'])
def emergency():
    """
    Create emergency ambulance request
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            patient_name:
              type: string
              example: "Ahmed Hassan"
            patient_phone:
              type: string
              example: "+971501234567"
            lat:
              type: number
              example: 25.2048
            lon:
              type: number
              example: 55.2708
            symptoms:
              type: string
              example: "Chest pain"
            priority:
              type: string
              enum: [Low, Medium, High, Critical]
    responses:
      201:
        description: Emergency request created successfully
        schema:
          properties:
            request_id:
              type: string
            status:
              type: string
            assigned_ambulance:
              type: string
      400:
        description: Invalid input
      500:
        description: Server error
    """
    # ... implementation
```

Visit `/apidocs` for interactive documentation.

#### Option B: Markdown Documentation (10 hours)
Create `API_DOCUMENTATION.md`:

```markdown
# Smart Ambulance API Documentation

## Emergency Endpoints

### POST /emergency
Create a new emergency ambulance request.

**Request Body:**
```json
{
  "patient_name": "Ahmed Hassan",
  "patient_phone": "+971501234567",
  "lat": 25.2048,
  "lon": 55.2708,
  "symptoms": "Chest pain",
  "priority": "High"
}
```

**Response (201 Created):**
```json
{
  "request_id": "REQ-2026-001",
  "status": "pending",
  "assigned_ambulance": "SA-001",
  "estimated_eta_minutes": 12
}
```

**Error Examples:**
- 400: Missing required field "patient_phone"
- 400: Invalid coordinates
- 500: Database connection error
```

Create detailed docs for all 30+ endpoints.

---

## 📅 PHASE 2: IMPORTANT ENHANCEMENTS (WEEK 2-3) — FOR BETTER GRADING

### 5. WebSocket Real-Time Updates (20 hours)
Replace polling with WebSocket for:
- Instant request notifications (no 10-second delay)
- Live ambulance position updates
- Real-time status changes
- Reduced server load by 70%

### 6. Persistent Location Tracking (20 hours)
- Track ambulance GPS every 10 seconds
- Store in `ambulance_location_history` table
- Show route polyline on map
- Calculate actual vs. predicted ETA accuracy
- Enable analytics: average response times, route efficiency

### 7. Performance Testing (15 hours)
- Load test with 100+ concurrent users using Apache JMeter or Locust
- Measure response times, throughput
- Identify bottlenecks
- Database query optimization (add indexes)
- Results should show: "System handles 100 concurrent users with <200ms response time"

### 8. Docker Deployment (10 hours)
```dockerfile
# Dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
  app:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - db
```

---

## 📅 WEEK-BY-WEEK BREAKDOWN

### **WEEK 1: Foundation (40-50 hours)**
- [ ] Mon-Tue: Implement ML module (demand + routing) — 20 hrs
- [ ] Tue-Wed: Create pytest test suite — 15 hrs
- [ ] Wed: Security fixes (passwords, .env, validation) — 8 hrs
- [ ] Thu-Fri: API documentation — 12 hrs
- [ ] **Deliverable**: Working ML, 70%+ test coverage, secure credentials, API docs

### **WEEK 2: Enhancement (30 hours)**
- [ ] Mon-Tue: WebSocket integration — 15 hrs
- [ ] Wed-Thu: Location tracking — 12 hrs
- [ ] Fri: Performance testing + optimization — 8 hrs
- [ ] **Deliverable**: Real-time system, location history, performance metrics

### **WEEK 3: Polish (20 hours)**
- [ ] Mon-Tue: Docker setup — 8 hrs
- [ ] Wed-Thu: Create unified architecture doc — 8 hrs
- [ ] Fri: Final testing, bug fixes — 4 hrs
- [ ] **Deliverable**: Containerized app, single architecture doc, production-ready

### **WEEK 4: Presentation Prep (10 hours)**
- [ ] Viva presentation slides
- [ ] Code walkthroughs
- [ ] Performance demos
- [ ] Live system demo

---

## 🎯 SUCCESS METRICS

Track your progress:

```
Week 1 Goals:
✓ ML module implemented and tested
✓ 70%+ test coverage achieved
✓ All passwords hashed
✓ API docs complete
✓ Zero hardcoded credentials

Week 2 Goals:
✓ WebSocket working (real-time notifications instant)
✓ 10 million location records stored efficiently
✓ Load test: 100 concurrent users supported
✓ Average response time <200ms

Week 3 Goals:
✓ Docker build succeeds
✓ Single 15-page architecture doc created
✓ All tests passing (100% pass rate)
✓ Zero security warnings from code review

Ready for Viva:
✓ Can explain every design decision
✓ Can walk through code confidently
✓ Performance metrics show scalability
✓ ML component clearly demonstrates understanding
```

---

## ⚠️ COMMON PITFALLS TO AVOID

❌ **Don't:**
1. Add ML code without understanding the algorithm
2. Just copy-paste test code—write meaningful tests
3. Implement features you can't explain
4. Submit before running full test suite
5. Leave debugging code/print statements

✅ **Do:**
1. Understand every line before adding it
2. Test edge cases (empty requests, invalid data, etc.)
3. Comment complex logic
4. Run `pytest --cov` before submission
5. Clean up logs; add proper logging instead of print()

---

## 📞 QUICK REFERENCE: FILES TO MODIFY

| File | Changes | Hours |
|------|---------|-------|
| Create `ml_demand_model.py` | New ML module | 20 |
| Create `ml_route_optimizer.py` | New optimization | 20 |
| Modify `app.py` | Integrate ML, add validation, rate limiting | 15 |
| Create `tests/` folder | Complete test suite | 15 |
| Update `templates/` | Add WebSocket integration | 20 |
| Create `requirements.txt` | New dependencies | 1 |
| Create `.env.example` | Environment config | 1 |
| Create `API_DOCUMENTATION.md` | API docs | 12 |
| Create `Dockerfile` & `docker-compose.yml` | Containerization | 8 |
| Create `ARCHITECTURE.md` | Unified design doc | 15 |

**Total: ~127 hours** (3-4 weeks × 35-40 hrs/week)

---

**Remember:** The goal isn't just to make it work—it's to make it professional, testable, and defensible in front of examiners. Every line of code should be something you can explain and justify.

Good luck! 🚀
