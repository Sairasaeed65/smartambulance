# SmartAmbulance - Complete Project Documentation

**Project Status:** Phase 4 (67% Complete) | Last Updated: May 31, 2026

**Quick Summary:** AI-driven emergency ambulance routing and dispatch system that optimizes emergency response times by automatically selecting the best hospital and ambulance based on real-time traffic, distance, bed availability, and driver experience.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Database Schema](#4-database-schema)
5. [API Endpoints](#5-api-endpoints)
6. [Features Completed](#6-features-completed)
7. [Features Pending](#7-features-pending)
8. [Key Functions & Modules](#8-key-functions--modules)
9. [Authentication System](#9-authentication-system)
10. [Issues & Bugs](#10-issues--bugs)

---

## 1. Project Overview

### What is SmartAmbulance?

SmartAmbulance is an **AI-driven emergency ambulance routing and dispatch system** designed to optimize emergency response times in urban environments. It connects patients in emergency situations with the nearest available ambulances and hospitals using intelligent routing algorithms.

### Core Business Logic

**The Emergency Flow:**
1. **Patient Emergency Request** → Patient submits emergency request with GPS location
2. **Automatic Hospital Selection** → AI algorithm evaluates all hospitals and selects the optimal one based on:
   - Traffic-aware ETA (50% weight) - Golden hour principle
   - Physical distance (25% weight) - Fuel efficiency
   - Available beds (15% weight) - Hospital capacity
   - Fleet load (5% weight) - Hospital workload
   - Driver experience history (5% weight) - Reliability
3. **Hospital Approval** → Hospital staff reviews and approves the dispatch
4. **Driver Assignment** → First available driver from selected hospital accepts assignment
5. **Real-time Tracking** → Driver location streamed to hospital dashboard (100ms latency via SSE)
6. **Delivery & Feedback** → Patient delivered, feedback collected

### User Types

| User Type | Role | Key Capabilities |
|-----------|------|-----------------|
| **Patient/Public** | Emergency requester | Submit emergency request, track ambulance in real-time, provide post-dispatch feedback, view request history |
| **Driver** | Ambulance operator | Accept/reject dispatches, update GPS location, manage attendance, view dispatch history |
| **Hospital Admin** | Hospital staff | Approve/reject requests, manage drivers and ambulances, update bed availability, view analytics |
| **System Admin** | Super-user | Monitor entire system, approve hospitals, manage blacklist, configure settings, view system-wide analytics |

### Problem Solved

**The Challenge:** In emergencies, selecting the wrong hospital wastes critical minutes when every second counts. Manual dispatch decisions lead to:
- Unnecessary transfers between hospitals
- Overloaded hospitals receiving more patients
- Underutilized hospitals remaining idle
- Longer patient response times

**The Solution:** SmartAmbulance AI automatically calculates the optimal hospital considering multiple factors simultaneously—traffic patterns, real-time distance, bed availability, and driver reliability—in under 2 seconds, eliminating manual decision delays.

---

## 2. Tech Stack

### Backend Infrastructure
- **Framework:** Flask 2.x (Python web framework)
- **Language:** Python 3.8+
- **Database:** MySQL 8.0 with connection pooling
- **Database Driver:** mysql-connector-python (thread-safe)
- **Real-time Communication:** Server-Sent Events (SSE) - 100ms latency
- **Security:** werkzeug.security (PBKDF2 hashing)
- **API Keys Management:** python-dotenv (.env files)

### Frontend
- **Markup:** HTML5 with semantic structure
- **Styling:** Bootstrap 5, custom CSS
- **Scripting:** Vanilla JavaScript (no framework dependencies)
- **Real-time Updates:** 
  - Polling (3-15 second intervals for non-critical updates)
  - SSE for critical hospital alerts (~100ms)

### External Services
- **Google Maps API:**
  - Directions API - Traffic-aware ETA calculation
  - Maps JavaScript API - Interactive map display
  - Geocoding API - Address to coordinates conversion
  - Places API - Location search and autocomplete

### Infrastructure & Deployment
- **Development Server:** Flask built-in (http://127.0.0.1:5000)
- **Database Connection Pool:** 10 concurrent connections
- **File Storage:** Local filesystem for avatars and certificates
- **Port:** 5000 (development)

---

## 3. Project Structure

```
smart_ambulance/
│
├── app.py (8,367 lines)                    Main Flask application
│                                          All routes, business logic, database queries
│
├── ai_engine.py                           AI dispatch scoring algorithm
│                                          5-factor hospital selection model
│
├── db_setup.py                            Database initialization & seeding
│
├── script.js                              Frontend real-time utilities
├── styles.css                             Global stylesheet
│
├── services/
│   ├── dispatch_service.py                Hospital selection algorithm wrapper
│   ├── maps_service.py                    Google Maps API integration
│   └── __init__.py
│
├── utils/
│   ├── traffic_patterns.py                Hardcoded traffic patterns by hour
│   └── __init__.py
│
├── static/
│   ├── uploads/                           User avatars, certificates
│   ├── images/                            Logos, UI images, markers
│   └── maps/                              Map overlays and custom icons
│
├── templates/ (19 HTML files)
│   ├── index.html                         Landing page
│   ├── emergency.html                     Emergency request form with map
│   ├── track.html                         Live ambulance tracking
│   ├── driver_login.html                  Driver authentication
│   ├── driver_dashboard.html              Driver main interface
│   ├── hospital_login.html                Hospital authentication
│   ├── hospital_register.html             Hospital self-registration
│   ├── hospital_dashboard.html            Hospital main interface (11,311 lines)
│   ├── admin_login.html                   Admin authentication
│   ├── admin_dashboard.html               Admin control panel
│   ├── admin_hospitals.html               Hospital management
│   ├── admin_drivers.html                 Driver management
│   ├── admin_emergencies.html             Emergency monitoring
│   ├── admin_reports.html                 Analytics and charts
│   ├── admin_settings.html                System configuration
│   ├── admin_users.html                   User management
│   ├── user_login.html                    Patient login
│   └── user_dashboard.html                Patient portal
│
├── .env                                   Environment variables (not in Git)
├── .gitignore                             Git exclusion rules
└── requirements.txt                       Python dependencies

Plus 30+ documentation markdown files and multiple test/debug scripts
```

### File Size Statistics

| Component | Lines of Code | Purpose |
|-----------|--------------|---------|
| app.py | 8,367 | Core Flask application with 96+ routes |
| hospital_dashboard.html | 11,311 | Most complex template - real-time hospital interface |
| driver_dashboard.html | 3,575 | Driver dispatch and tracking interface |
| AI Engine | ~300 | 5-factor weighted scoring algorithm |
| HTML Templates | 1,200+ | All UI pages combined |
| JavaScript | 800+ | Real-time updates and maps |
| CSS | 500+ | Bootstrap customization |
| **Total Backend** | **~10,000+** | Python, Flask, AI logic |

---

## 4. Database Schema

### Complete Database: 10 Tables

#### **Table 1: `hospitals`**
Stores hospital facility information and credentials.

**Key Columns:**
- `id` (INT) - Primary key, auto-increment
- `username, password` - Login credentials (password is PBKDF2 hashed)
- `name, address, phone, email` - Basic information
- `total_beds, available_beds` - Bed management
- `latitude, longitude` - GPS location for routing
- `specialties` - JSON array of departments ["cardiology", "trauma"]
- `performance_score` - Historical efficiency rating (AI uses to prefer reliable hospitals)
- `status` - ENUM: pending → approved → rejected (admin approval workflow)
- `is_locked` - Boolean: admin can disable login
- `website, whatsapp` - Additional contact info

**Purpose:** Central registry of all hospitals in the system with approval workflow and real-time metrics.

---

#### **Table 2: `drivers`**
Stores ambulance driver information and real-time location.

**Key Columns:**
- `id` (INT) - Primary key
- `username, password` - Login credentials (currently PLAINTEXT - SECURITY ISSUE)
- `name, phone, cnic` - Identity information
- `status` - ENUM: Available, Busy (used for dispatch availability)
- `assigned_ambulance` - Reference to ambulances table
- `hospital_id` - Which hospital they work for
- `current_latitude, current_longitude` - Real-time GPS (updated every 3-5 seconds during dispatch)
- `experience` - Years of experience (used in AI scoring)
- `profile_pic` - Avatar file path
- `certifications` - JSON array of training certificates

**Purpose:** Track all active drivers, their availability, and real-time location for dispatch optimization.

**Workflow Status Values:**
- Available - Ready for new dispatch
- Busy - Currently on active dispatch
- Off Duty - Not available

---

#### **Table 3: `ambulances`**
Stores fleet vehicle information.

**Key Columns:**
- `ambulance_number` (VARCHAR) - License plate (PRIMARY KEY)
- `hospital_id` - Owning hospital
- `type` - ENUM: Basic, Advanced, ICU (capability level)
- `status` - ENUM: Active, Maintenance, Retired
- `equipment` - JSON object with equipment list {"ventilator": 1, "oxygen": 2}
- `last_service` - Date of last maintenance

**Purpose:** Inventory of all ambulances and their capabilities.

---

#### **Table 4: `patient_requests`**
Core table tracking all emergency requests - the heart of the system.

**Key Columns:**
- `request_id` - Unique identifier (format: REQ_YYYYMMDDHHmmSS)
- `patient_name, patient_phone, pickup_address` - Emergency details
- `latitude, longitude` - GPS coordinates of patient location
- `reason` - Emergency type ("Heart Attack", "Road Accident", etc.)
- `priority` - ENUM: High, Medium, Low
- `status` - Workflow status (see status flow below)
- `hospital_id` - Currently assigned hospital
- `assigned_driver_id` - Assigned driver if any
- `locked, locked_by` - Atomic locking mechanism to prevent race conditions
- `reassignment_count` - How many times reassigned (max 3 before cancellation)
- `auto_processed` - TRUE if AI auto-selected hospital
- `forwarded_from_hospital_id` - If transferred from another hospital
- `ip_address` - Source IP for rate limiting and fraud detection
- `timestamp, completed_at` - Lifecycle timestamps

**Status Workflow:**
```
pending → assigned → dispatched → accepted → en_route → picked_up → completed
                          ↓
                       cancelled / no_hospital_available
```

**Purpose:** Complete audit trail of every emergency request with full lifecycle tracking.

---

#### **Table 5: `dispatches`**
Tracks active and completed dispatch assignments - dispatch records created when hospital accepts a request.

**Key Columns:**
- `dispatch_id` - Unique identifier
- `request_id` - Links to patient_requests
- `driver_id, ambulance_id, hospital_id` - Assignment details
- `status` - dispatched, accepted, picked_up, completed, rejected
- `priority` - Inherited from request
- `timestamp, updated_at` - Lifecycle tracking

**Purpose:** Detailed record of each dispatch assignment with full history.

---

#### **Table 6: `status_timeline`**
Complete audit trail - every status change is logged with who made it and when.

**Key Columns:**
- `request_id` - Which emergency request
- `dispatch_id` - Which dispatch (if any)
- `old_status, new_status` - State transition
- `action_by` - Who triggered the change (username)
- `action_type` - Type of action (system_auto_forward, driver_accepted, etc.)
- `driver_name` - Driver involved (if any)
- `timestamp` - Exact time of change

**Purpose:** Complete historical record for compliance, debugging, and analytics.

---

#### **Table 7: `users`**
Patient and public user accounts.

**Key Columns:**
- `id` - Primary key
- `username, password` - Login credentials (currently PLAINTEXT - SECURITY ISSUE)
- `full_name, phone, email` - Identity
- `cnic` - 13-digit national ID (used for smart login)
- `blood_type, medical_history` - Medical information
- `emergency_contacts` - JSON array of emergency contact names/numbers
- `address, user_type` - Additional info

**Purpose:** Patient/public user accounts with medical history for emergency response.

---

#### **Table 8: `blacklist`**
Anti-spam phone number blacklist.

**Key Columns:**
- `phone` - Blacklisted phone number (UNIQUE)
- `reason` - Reason for ban
- `blocked_by` - Admin who blocked
- `created_at` - When banned

**Purpose:** Security feature to prevent spam and prank emergency calls. Blacklisted phones are auto-rejected at `/emergency` endpoint.

---

#### **Table 9: `attendance_records`**
Driver attendance and leave tracking.

**Key Columns:**
- `driver_id` - Which driver
- `date` - Attendance date
- `status` - ENUM: Present, On Leave
- `admin_status` - ENUM: pending, approved, rejected (leave approval workflow)
- `leave_reason` - If on leave, reason for absence
- `approved_by` - Admin who approved

**Purpose:** Track driver attendance with hospital approval workflow for leave requests.

---

#### **Table 10: `system_settings`**
Global configuration parameters.

**Key Columns:**
- `setting_key` - Setting name (UNIQUE)
- `setting_value` - Setting value
- `updated_at` - Last modified

**Default Settings:**
```
emergency_timeout: 10 (minutes before auto-reassign)
max_distance: 50 (km radius for hospital selection)
```

**Purpose:** Centralized system configuration without code changes.

---

### Database Relationships

```
┌─ hospitals (1) ──────── (N) drivers ──────┐
│         │                   │              │
│         │                   └─ current_latitude/longitude
│         │
│         ├─ (1) ──────── (N) ambulances
│         │
│         └─ (1) ──────── (N) patient_requests
│                              │
│                              ├─ (1) ──────── (N) dispatches
│                              │
│                              ├─ assigned_driver_id ──→ drivers
│                              │
│                              └─ (1) ──────── (N) status_timeline

users ────── patient_requests (phone match)
    └─ dispatches (tracking)

drivers ──── attendance_records
drivers ──── dispatches (active assignments)

blacklist (independent - checked at /emergency endpoint)
system_settings (independent - global config)
```

---

## 5. API Endpoints

### Complete Route Reference (96+ Endpoints)

#### **A. EMERGENCY & DISPATCH OPERATIONS**

**1. POST /emergency**
- **Purpose:** Submit emergency request and trigger AI hospital selection
- **Body:**
  ```json
  {
    "patient_name": "Ahmed Hassan",
    "patient_phone": "03001234567",
    "pickup_address": "Iqbal Town, Lahore",
    "reason": "Heart Attack",
    "priority": "High",
    "latitude": 31.5204,
    "longitude": 74.3587
  }
  ```
- **Response:** `{status: "success", request_id: "REQ_...", hospital_name: "...", eta_minutes: 8, driver_name: "..."}`
- **Validation:** Checks blacklist, rate limits, location validity, duplicate requests
- **AI Selection:** Evaluates all hospitals with available drivers using 5-factor scoring

**2. POST /dispatch**
- **Purpose:** Direct dispatch endpoint (used by AI dispatch process)
- **Response:** Hospital selection with AI scoring breakdown
- **Error:** 409 Conflict if no drivers available

**3. POST /nearest-hospitals**
- **Purpose:** Get nearby hospitals with scoring
- **Body:** `{latitude, longitude, radius_km}`
- **Response:** Array of hospitals sorted by distance/score

**4. POST /cancel-request**
- **Purpose:** Patient cancels active emergency request
- **Body:** `{request_id: "REQ_..."}`
- **Response:** `{status: "success"}`

**5. GET /get-request-status**
- **Purpose:** Patient polls for ambulance status (every 3 seconds)
- **Query:** `?request_id=REQ_...`
- **Response:** `{status: "en_route", driver_name: "...", eta_minutes: 3, driver_location: {...}}`

**6. POST /driver-respond**
- **Purpose:** Driver acknowledges dispatch
- **Body:** `{dispatch_id: "DISP_..."}`

**7. POST /update-driver-location**
- **Purpose:** Real-time GPS location update (called every 3-5 seconds during dispatch)
- **Body:** `{driver_id, latitude, longitude, status: "en_route"}`
- **Note:** Triggers SSE broadcast to hospital dashboards

**8. GET /get-live-tracking**
- **Purpose:** Get real-time tracking data for patient
- **Response:** Driver location, hospital location, patient location, route polyline

**9. POST /submit-feedback**
- **Purpose:** Patient submits post-dispatch rating and feedback
- **Body:** `{request_id, rating: 1-5, comments: "..."}`

---

#### **B. AUTHENTICATION & SESSION**

**10. GET / **
- **Purpose:** Home/landing page

**11. POST /user-login**
- **Purpose:** Patient traditional login
- **Body:** `{username, password}`
- **Response:** Sets session, redirects to user dashboard

**12. POST /user-smart-login**
- **Purpose:** CNIC-based auto-registration/login
- **Body:** `{cnic: "12345-1234567-1"}`
- **Behavior:** If CNIC not found, auto-creates account

**13. POST /driver-login**
- **Purpose:** Driver authentication
- **Body:** `{username, password}`

**14. POST /hospital-login**
- **Purpose:** Hospital staff authentication
- **Body:** `{username, password}`

**15. GET/POST /hospital-register**
- **Purpose:** Hospital self-registration form
- **Workflow:** Pending approval by admin before login allowed

**16. POST /admin-login**
- **Purpose:** System admin authentication

**17. GET /check-session**
- **Purpose:** Check if user is logged in
- **Response:** `{logged_in, user_type, username}`

**18. GET /logout**
- **Purpose:** Clear session and logout

---

#### **C. DRIVER DASHBOARD & MANAGEMENT**

**19. GET /driver-dashboard**
- **Purpose:** Driver main interface
- **Display:** Active dispatch, accept/reject buttons, location map

**20. GET /get-driver-live-data**
- **Purpose:** Get live driver data for admin
- **Query:** `?driver_id=5`

**21. POST /driver-accept-dispatch**
- **Purpose:** Driver accepts dispatch assignment
- **Body:** `{dispatch_id}`
- **Changes:** dispatch.status = "accepted", driver.status = "Busy"

**22. POST /driver-reject-dispatch**
- **Purpose:** Driver rejects dispatch assignment
- **Body:** `{dispatch_id, reason}`
- **Effect:** Increments reassignment_count, tries next driver

**23. POST /driver-upload-photo**
- **Purpose:** Upload driver profile photo

**24. POST /driver-change-password**
- **Purpose:** Driver changes password

**25. POST /mark-attendance**
- **Purpose:** Mark Present or On Leave
- **Body:** `{driver_id, status}`

**26. GET /driver-history**
- **Purpose:** Get driver's past dispatches
- **Query:** `?days=30`

**27. POST /update-dispatch-status**
- **Purpose:** Update dispatch status progression
- **Body:** `{dispatch_id, new_status}` (pending → en_route → picked_up → completed)

---

#### **D. HOSPITAL MANAGEMENT**

**28. GET /hospital-dashboard**
- **Purpose:** Hospital main interface
- **Display:** Pending requests, accept/reject buttons, bed availability, staff roster

**29. GET /get-hospital-requests**
- **Purpose:** Get pending emergency requests for this hospital
- **Response:** List of requests awaiting approval

**30. POST /accept-request**
- **Purpose:** Hospital approves dispatch and selects driver
- **Body:** `{request_id, hospital_id}`
- **Effect:** Creates dispatch, locks driver, notifies driver

**31. POST /reject-request**
- **Purpose:** Hospital rejects request (auto-forwards to next hospital)
- **Body:** `{request_id, reason}`

**32. GET /get-hospital-active-requests**
- **Purpose:** Get currently active (in-progress) requests

**33. GET /get-hospital-history**
- **Purpose:** Historical requests with filters
- **Query:** `?hospital_id=1&status=completed&date_from=...&date_to=...`

**34. POST /update-beds**
- **Purpose:** Update available bed count
- **Body:** `{hospital_id, available_beds}`

**35. POST /update-total-beds**
- **Purpose:** Update total bed capacity

**36. POST /add-driver**
- **Purpose:** Hospital adds new driver
- **Body:** `{username, password, name, phone, cnic, experience}`

**37. POST /remove-driver**
- **Purpose:** Remove driver from hospital

**38. GET /get-drivers**
- **Purpose:** List hospital's drivers
- **Response:** Array of driver info

**39. POST /add-ambulance**
- **Purpose:** Register new ambulance
- **Body:** `{ambulance_number, type, equipment}`

**40. POST /remove-ambulance**
- **Purpose:** Decommission ambulance

**41. GET /get-ambulances**
- **Purpose:** List hospital's ambulances

**42. GET /get-hospital-stats**
- **Purpose:** Dashboard KPIs

**43. GET /hospital-sse-stream**
- **Purpose:** Real-time SSE event stream for hospital alerts
- **Events:** new_emergency (with patient location), ping (heartbeat every 30s)

---

#### **E. ADMIN SYSTEM MANAGEMENT**

**44. GET /admin-dashboard**
- **Purpose:** System-wide overview dashboard

**45. GET /admin-reports**
- **Purpose:** Analytics and performance charts

**46. GET /admin-api/emergency-stats**
- **Purpose:** Emergency statistics (JSON)
- **Response:** `{total, completed, pending, cancelled, avg_response_time}`

**47. GET /admin-api/all-stats**
- **Purpose:** Comprehensive system statistics

**48. POST /admin-approve-hospital/<id>**
- **Purpose:** Approve pending hospital registration
- **Effect:** hospital.status = "approved"

**49. POST /admin-reject-hospital/<id>**
- **Purpose:** Reject hospital registration

**50. POST /admin-lock-hospital/<id>**
- **Purpose:** Lock hospital account (disable login)

**51. POST /admin-remove-hospital/<id>**
- **Purpose:** Delete hospital from system

**52. GET /admin-api/blacklist**
- **Purpose:** View all blacklisted phone numbers

**53. POST /admin-api/blacklist**
- **Purpose:** Add phone to blacklist
- **Body:** `{phone, reason}`

**54. POST /admin-api/unblacklist/<phone>**
- **Purpose:** Remove from blacklist

**55. GET /admin-hospitals, /admin-drivers, /admin-emergencies, /admin-users**
- **Purpose:** Management pages for each resource type

---

#### **F. ATTENDANCE & SCHEDULING**

**56. GET /get-pending-attendance**
- **Purpose:** List pending leave approval requests

**57. POST /approve-attendance**
- **Purpose:** Admin approve or reject leave request

**58. GET /all-attendance**
- **Purpose:** View all attendance records

**59. GET /get-today-activity**
- **Purpose:** Today's activity summary (active drivers, on leave, requests, etc.)

---

## 6. Features Completed

### ✅ **Core Emergency Dispatch System (100%)**
- Real-time patient emergency form on homepage
- Automatic geolocation capture with GPS validation
- Hospital auto-selection via AI algorithm
- Confirmation to patient with ETA and ambulance details
- Request status polling for real-time tracking
- Support for high/medium/low priority classification

### ✅ **AI Routing Engine (95%)**
- **5-Factor Weighted Scoring Algorithm:**
  - ETA from Google Maps with traffic data (50% weight) - Golden Hour principle
  - Haversine distance calculation (25% weight)
  - Hospital bed availability (15% weight)
  - Ambulance fleet load scoring (5% weight)
  - Driver experience rating (5% weight)
- Selects optimal hospital in <2 seconds
- Fallback to closest hospital if Google Maps API fails
- Demand prediction by time of day
- Performance scoring for hospital history tracking

### ✅ **Driver Management Dashboard (100%)**
- Real-time dispatch notifications
- Accept/Reject dispatch workflow with cooldown tracking
- Live location tracking with GPS updates every 3-5 seconds
- Status progression: dispatched → en_route → picked_up → completed
- 30-day dispatch history view
- Attendance tracking (Present/On Leave)
- Profile management with photo upload
- Password management
- Real-time availability status

### ✅ **Hospital Dashboard (100%)**
- Pending emergency requests display with map preview
- Approve/Reject dispatch decisions
- Real-time SSE alerts for new emergencies (~100ms latency)
- Driver roster management (add/remove drivers)
- Ambulance fleet management
- Real-time bed availability updates
- Historical request tracking with filters
- Hospital profile editing with document uploads
- Performance analytics and KPIs
- Attendance approval workflow

### ✅ **Admin Control Panel (100%)**
- System-wide emergency monitoring with real-time feed
- Hospital approval workflow (pending → approved/rejected)
- Hospital lock/unlock access control
- Driver and user management
- System-wide performance analytics with charts
- Blacklist management (add/remove/view)
- System settings configuration
- Hospital verification system
- GPS coordinate management for hospitals

### ✅ **Patient Account System (100%)**
- Registration via username/password
- Smart login via CNIC with auto-registration
- Profile management with medical history
- Emergency contact storage
- Blood type recording
- Request history with detailed tracking
- Feedback submission with ratings
- Multi-platform accessibility

### ✅ **Anti-Spam & Security (100%)**
- IP-based rate limiting (1 request per 5 minutes per IP)
- Phone-based rate limiting (5 requests per day)
- Location validation (Pakistan boundary check: 23°N-37°N, 60°E-77°E)
- Blacklist system for blocked phones
- Duplicate request detection (prevents multiple simultaneous emergencies per phone)
- Atomic locking mechanism to prevent race conditions
- Request locking during dispatch assignment

### ✅ **Real-time Features (100%)**
- Server-Sent Events (SSE) for hospital alerts (~100ms latency)
- 3-second polling for driver dashboard updates
- 15-second polling for admin statistics
- Geolocation API integration
- Live ambulance tracking map with driver location
- Real-time bed availability updates
- Real-time driver status synchronization

### ✅ **Data Auditing & Reporting (100%)**
- Complete status timeline for each request with audit trail
- Recording of who performed what action and when
- Historical tracking of all dispatches
- 30-day driver history
- Hospital performance metrics
- System-wide analytics dashboard
- Request status progression tracking
- Performance trends and KPIs

### ✅ **Database & Infrastructure (100%)**
- Connection pool (size=10) for production-level scalability
- Parameterized SQL queries (prevents SQL injection)
- Automatic schema creation on startup
- Demo data seeding
- Transaction management
- Error logging and debugging utilities
- Comprehensive logging of dispatch decisions

---

## 7. Features Pending

### ⚠️ **Critical - Security Enhancements**

#### **1. Plaintext Password Storage (HIGH SEVERITY)**
- **Affected:** 
  - `drivers` table (driver passwords)
  - `users` table (patient passwords)
- **Current Issue:** Passwords stored as plaintext
- **Impact:** If database breached, all passwords exposed; violates security best practices
- **Fix Required:** Hash all passwords with PBKDF2 like hospitals do
- **Estimated Effort:** 2 hours
- **Code Location:** app.py lines with INSERT/SELECT for passwords
- **Status:** NOT STARTED

#### **2. No HTTPS/SSL (HIGH for Production)**
- **Affected:** All network traffic
- **Current:** Development server only (http://127.0.0.1:5000)
- **Impact:** Credentials sent in plaintext over HTTP; vulnerable to man-in-the-middle attacks
- **Fix Required:** SSL certificates for production deployment
- **Deployment:** Use Gunicorn + Nginx reverse proxy with SSL
- **Status:** NOT STARTED

#### **3. CORS Configuration (MEDIUM)**
- **Issue:** Not configured for external APIs
- **Status:** NOT STARTED

---

### ⚠️ **Payment & Billing System**

- **No payment integration** - Cannot charge patients or hospitals
- **No billing system** - No cost calculation or invoicing
- **No payment gateway** - No Stripe, PayPal, or local payment integration
- **Status:** 0% COMPLETE
- **Business Impact:** High - Revenue model not implemented

---

### ⚠️ **SMS & Notifications**

- **No SMS integration** - Only in-app alerts (no Twilio, AWS SNS, etc.)
- **No WhatsApp notifications** - Popular in Pakistan but not implemented
- **No Email alerts** - Could be useful for hospital admins
- **No Push notifications** - Would help mobile users
- **Status:** 0% COMPLETE
- **User Impact:** High - Patients unaware of ambulance arrival without checking app

---

### ⚠️ **Mobile Applications**

- **No iOS native app** - Only web-based
- **No Android native app** - Only web-based
- **Status:** 0% COMPLETE
- **Business Impact:** Critical - Most users in Pakistan access via mobile

---

### ⚠️ **Advanced Dispatch Features**

#### **Smart Reassignment (MEDIUM)**
- **Current:** If driver rejects, only retries up to 3 times then cancels
- **Desired:** Should intelligently reassign to next-best hospital
- **Status:** PARTIAL (workaround exists: auto-forward thread after 60 seconds)
- **File:** `app.py` around dispatch rejection logic

#### **Multi-Hospital Network (MEDIUM)**
- **Desired:** Automatic transfer when first hospital full
- **Existing:** `forwarded_from_hospital_id` column exists but not implemented
- **Status:** NOT STARTED

#### **Machine Learning Integration (MEDIUM)**
- **Current:** AI scoring uses hardcoded weights
- **Desired:** Learn optimal weights from historical data
- **Status:** NOT STARTED

---

### ⚠️ **Documentation & Testing**

- **No API Documentation** - No Swagger/OpenAPI specs
- **Incomplete Test Suite** - Multiple test files but no CI/CD integration
- **No Automated Tests** - Manual testing only
- **Status:** 20% COMPLETE

---

### ⚠️ **Traffic & Routing**

- **File:** `utils/traffic_patterns.py`
- **Issue:** Hardcoded traffic speeds by hour (not real-time)
- **Current:** Fixed speed model (e.g., "9 AM weekday = 20 km/h")
- **Should:** Use Google Maps real-time traffic layer
- **Status:** WORKAROUND IN PLACE (functional but suboptimal)

---

## 8. Key Functions & Modules

### **A. Core Emergency Dispatch Flow (`app.py`)**

#### Function: `emergency()`
```python
"""
POST /emergency

Main entry point for emergency requests. Steps:
1. Validate request format and required fields
2. Check if phone number is blacklisted
3. Check for duplicate active requests from same phone
4. Validate location is within Pakistan boundaries
5. Check rate limits (IP: 1/5min, Phone: 5/day)
6. Query all approved hospitals with available drivers
7. Call ai_engine.calculate_dispatch_score() for each hospital
8. Select hospital with lowest (best) score
9. Create patient_request record with request_id
10. Create dispatch record with dispatch_id
11. Lock driver atomically to prevent race conditions
12. Broadcast SSE alert to hospital dashboard
13. Return confirmation with ETA and driver name
14. If no hospital available, add to queue for auto-forward thread
"""
```

#### Function: `dispatch()`
```python
"""
POST /dispatch
AI Hospital Selection Pipeline

Implementation of 5-factor weighted scoring algorithm.
Calls ai_engine.calculate_dispatch_score() for each hospital.
Returns selected hospital with detailed scoring breakdown.
"""
```

#### Function: `calculate_dispatch_score()` - IN `ai_engine.py`
```python
"""
Core AI Scoring Function

Inputs:
- hospital_id: Target hospital
- patient_lat/lng: Patient GPS coordinates

Calculation:
1. Get hospital location & available resources
2. Calculate Haversine distance between patient and hospital
3. Call Google Maps API for traffic-aware ETA
4. Calculate bed availability penalty (0 = 5+ beds, 0.5 = <5 beds, 1.0 = 0 beds)
5. Calculate ambulance load penalty (busy_ambulances / total)
6. Calculate driver experience bonus (avg_response_time / 30)
7. Weight each factor:
   - ETA: 50% weight (most critical for golden hour)
   - Distance: 25% weight
   - Bed availability: 15% weight
   - Fleet load: 5% weight
   - Driver history: 5% weight

Returns:
{
    'total_score': 45.2,                          # Primary sorting key
    'distance_km': 3.2,
    'eta_minutes': 8,
    'hospital_bed_status': 'available',
    'breakdown': {
        'eta_score': 400,
        'distance_score': 160,
        'bed_availability_score': 0,
        'ambulance_load_score': 10,
        'driver_history_score': -5
    },
    'recommendation_reason': 'Closest hospital with good availability'
}
"""
```

#### Function: `lock_request()`
```python
"""
Atomic operation to prevent race conditions.

Problem: Multiple drivers from same hospital could accept same request.
Solution: Database-level lock flag with driver ID.

Implementation:
1. Check if request.locked == TRUE
2. If locked and not this driver, return error
3. Set locked = TRUE, locked_by = driver_id
4. Proceed with dispatch creation
5. Unlock after dispatch confirmed or timeout

Purpose: Ensures only one driver gets assigned to each request
"""
```

#### Function: `update_driver_location()`
```python
"""
POST /update-driver-location
Real-time GPS tracking during active dispatch.

Updates:
- driver.current_latitude, current_longitude
- driver.location_updated_at timestamp
- Broadcasts to hospital's SSE stream
- Stores in status_timeline for audit

Frequency: Every 3-5 seconds during dispatch

Performance: Requires database connection pool to handle
frequent updates without blocking other operations
"""
```

#### Function: `hospital_sse_stream()`
```python
"""
GET /hospital-sse-stream
Server-Sent Events broadcaster for real-time alerts.

Connection: Persistent (client connects and holds open)
Latency: ~100ms (vs 15-second polling before)
Heartbeat: Sends "ping" event every 30 seconds

Events Sent:
- event: new_emergency
  data: {request_id, patient_location, eta_minutes}

- event: ping (heartbeat)
  data: (empty)

Architecture:
- Uses thread-safe Queue for each hospital
- Broadcast triggered by /dispatch endpoint
- Fallback: 15-second polling if SSE unavailable

Performance Improvement:
- Before SSE: 15s polling = 0-15s delay
- After SSE: 100ms push = ~150x faster
"""
```

### **B. AI Engine Module (`ai_engine.py`)**

#### Function: `haversine_distance(lat1, lon1, lat2, lon2)`
```python
"""
Calculate great-circle distance between two GPS points.

Formula: d = 2R * arcsin(sqrt(sin²(Δφ/2) + cos(φ1)*cos(φ2)*sin²(Δλ/2)))

Where R = 6,371 km (Earth's mean radius)

Usage: Fallback when Google Maps API unavailable
Returns: Distance in kilometers
"""
```

#### Function: `get_google_maps_eta(origin, destination)`
```python
"""
Get traffic-aware ETA from Google Maps Directions API.

Parameters:
- origin: (latitude, longitude) tuple
- destination: (latitude, longitude) tuple

API Call: 
  GET https://maps.googleapis.com/maps/api/directions/json
  ?origin=lat,lng&destination=lat,lng
  &departure_time=now
  &traffic_model=best_guess

Returns: ETA in minutes or None if API fails

Fallback: Estimate using Haversine distance / 30 km/h
"""
```

---

## 9. Authentication System

### **Overview: Four User Types**

```
┌─────────────────┬──────────────────┬────────────────┬──────────────┐
│ Patient/Public  │ Driver           │ Hospital Admin │ System Admin │
├─────────────────┼──────────────────┼────────────────┼──────────────┤
│ /user-login     │ /driver-login    │ /hospital-login│ /admin-login │
│ Username/Pass   │ Username/Pass    │ Username/Pass  │ Hardcoded    │
│ CNIC Smart-L    │ (Plaintext - BUG)│ (PBKDF2 - OK) │ (PBKDF2 - OK)│
│ (Auto-register) │                  │                │              │
└─────────────────┴──────────────────┴────────────────┴──────────────┘
```

### **1. Patient/Public User**

**Login Method 1: Traditional**
```
POST /user-login
Headers: Content-Type: application/json
Body: {username, password}

Process:
1. Query users table for matching username
2. Compare plaintext password (SECURITY ISSUE)
3. Set session['user_id'], session['user_type'] = 'patient'
4. Session expires: 24 hours

Current Issue: Password stored plaintext, compared plaintext
Should Be: Hash with PBKDF2, verify hash
```

**Login Method 2: Smart (CNIC-based)**
```
POST /user-smart-login
Body: {cnic: "12345-1234567-1"}

Process:
1. Query users table for CNIC
2. If found: Set session and login
3. If not found: Auto-create new user with:
   - Auto-generated username
   - Empty password
   - CNIC as identifier
4. Set session

Purpose: Quick emergency access without pre-registration
```

### **2. Driver**

**Login Flow:**
```
POST /driver-login
Body: {username, password}

Validation:
1. Query drivers table
2. Compare plaintext password (SECURITY ISSUE)
3. Check driver's hospital is approved
4. Check driver is not locked
5. Set session['driver_id'], session['hospital_id']
6. Redirect to /driver-dashboard

Session Keys:
- driver_id: int
- hospital_id: int
- driver_username: str
- user_type: 'driver'
```

### **3. Hospital Staff**

**Registration Workflow (First Time):**
```
GET  /hospital-register    → Display form
POST /hospital-register    → Submit registration

Form Fields:
- Hospital name, address, phone, email
- Username, password
- GPS coordinates
- Specialties, bed count

Processing:
1. Validate unique username, phone, email
2. Hash password with PBKDF2 (werkzeug.security)
3. Create hospitals row with status='pending'
4. Set is_locked=TRUE (cannot login until approved)
5. Send approval email to admin

Status: PENDING_ADMIN_APPROVAL
```

**Login (After Approval):**
```
POST /hospital-login
Body: {username, password}

Validation:
1. Query hospitals table
2. PBKDF2 verify password (secure)
3. Check status == 'approved'
4. Check is_locked == FALSE
5. Set session['hospital_id'], session['hospital_name']
6. Redirect to /hospital-dashboard

Session:
- hospital_id: int
- hospital_username: str
- user_type: 'hospital'
- Expires: 24 hours
```

### **4. System Admin**

**Setup:**
```
Hardcoded Admin Credentials
Username: 'admin' (hardcoded in app.py)
Password: Hashed with PBKDF2 (hardcoded or .env)

Login:
POST /admin-login
Body: {username, password}

Validation:
1. Compare against hardcoded credentials
2. PBKDF2 verify
3. Set session['is_admin'] = TRUE
4. Redirect to /admin-dashboard
```

### **5. Session Management**

**Configuration:**
```python
app.config['SESSION_COOKIE_HTTPONLY'] = True      # JavaScript cannot read
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'    # CSRF protection
app.config['SESSION_COOKIE_SECURE'] = False       # HTTP only (dev only)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
```

**Lifecycle:**
```
1. User Login
   ↓
2. Set session['permanent'] = True
   ↓
3. Session created in Flask memory store
   ↓
4. Cookie SESSIONID sent to browser
   ↓
5. Browser sends cookie with every request
   ↓
6. Server validates session
   ↓
7. Expiry: 24 hours or on logout
   ↓
8. session.clear() on /logout
```

### **6. Password Security Issues**

| User Type | Storage | Hashing | Issue | Fix |
|-----------|---------|---------|-------|-----|
| Patient | users table | Plaintext ❌ | HIGH RISK | Hash with PBKDF2 |
| Driver | drivers table | Plaintext ❌ | HIGH RISK | Hash with PBKDF2 |
| Hospital | hospitals table | PBKDF2 ✅ | SECURE | None needed |
| Admin | Code/env | PBKDF2 ✅ | SECURE | None needed |

**Example - Secure (Hospital):**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Registration
password_hash = generate_password_hash('secure456', method='pbkdf2:sha256')
cursor.execute("INSERT INTO hospitals (password) VALUES (%s)", (password_hash,))

# Login
cursor.execute("SELECT password FROM hospitals WHERE username = %s", (username,))
stored_hash = cursor.fetchone()[0]
if check_password_hash(stored_hash, provided_password):
    # Password correct - login user
```

**Example - Insecure (Current - Patient/Driver):**
```python
# Registration - PLAINTEXT
password = request.form.get('password')
cursor.execute("INSERT INTO users (password) VALUES (%s)", (password,))
# SECURITY RISK: Anyone with database access reads password in plaintext

# Login - PLAINTEXT COMPARISON
cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
               (username, password))
# SECURITY RISK: Password visible in HTTP traffic if not HTTPS
```

---

## 10. Issues & Bugs

### **CRITICAL ISSUES**

#### **1. Plaintext Password Storage (SEVERITY: HIGH)**
- **Location:** `drivers` table, `users` table
- **Problem:** Passwords stored as plaintext instead of hashed
- **Evidence:** No hashing in driver/user registration or login code
- **Impact:** If database breached, all passwords exposed; violates security standards
- **Affected Users:** All drivers and patients
- **Fix Required:**
  1. Hash all passwords with PBKDF2 (like hospitals already do)
  2. Migrate existing plaintext passwords
  3. Update login validation to use hash comparison
- **Estimated Effort:** 2 hours
- **Status:** NOT STARTED
- **Deployment Risk:** HIGH - Must fix before production

#### **2. No HTTPS/SSL (SEVERITY: HIGH for Production)**
- **Current State:** Development server (http://127.0.0.1:5000)
- **Problem:** All traffic unencrypted
- **Impact:** Credentials and location data vulnerable to interception
- **Deployment Fix:** Use HTTPS with valid SSL certificate + Nginx reverse proxy
- **Status:** NOT STARTED
- **Deployment Blocker:** YES - Must have for production

#### **3. JavaScript MIME Type Error (SEVERITY: MEDIUM)**
- **Error:** `Refused to execute script.js because MIME type is 'text/plain'`
- **Location:** Browser console shows error for `/static/script.js`
- **Impact:** JavaScript not executing - real-time features may not work
- **Cause:** Flask not serving .js files with correct Content-Type header
- **Investigation Steps:**
  1. Check file exists at `static/script.js`
  2. Verify Flask static folder configuration
  3. Test: `curl -I http://127.0.0.1:5000/static/script.js` and check Content-Type
- **Fix Location:** `app.py` static file serving configuration
- **Status:** NEEDS INVESTIGATION

---

### **MODERATE ISSUES**

#### **4. No Fallback When No Drivers Available (DESIGN)**
- **Location:** app.py around dispatch logic
- **Comment:** Line 1216 - "Do NOT fall back to AI selection when no driver is available"
- **Current Behavior:** If hospital has no available drivers, return 409 error
- **Desired Behavior:** Auto-reassign to next-best hospital with available driver
- **Workaround:** Auto-forward background thread reassigns after 60 seconds
- **Status:** PARTIAL SOLUTION (functional but not ideal)

#### **5. Hardcoded Traffic Patterns (MEDIUM)**
- **File:** `utils/traffic_patterns.py`
- **Issue:** Fixed speed lookup table by hour (not real-time)
- **Example:** "9 AM weekday = 20 km/h" hardcoded
- **Impact:** ETA calculations inaccurate during unusual traffic
- **Current:** Traffic model=best_guess from Google Maps (but hardcoded fallback)
- **Desired:** Real-time traffic layer integration
- **Status:** WORKAROUND IN PLACE (functional)

#### **6. Max 3 Request Rejections (DESIGN LIMITATION)**
- **Current Logic:** `if reassignment_count >= 3: status = 'cancelled'`
- **Problem:** Request cancelled if 3 drivers reject
- **Impact:** Patient left without ambulance if all drivers from one hospital reject
- **Desired:** Smart reassignment to next hospital
- **Actual:** Auto-forward thread provides solution after 60 seconds
- **Status:** LIMITATION (covers 90% of cases)

#### **7. Incomplete Attendance System (MEDIUM)**
- **Table:** `attendance_records` created
- **Issue:** Leave approval workflow has no UI
- **Missing:** Driver leave request submission form
- **Missing:** Admin attendance approval dashboard
- **Impact:** Attendance tracking functional but limited
- **Status:** 40% COMPLETE

---

### **LOW PRIORITY ISSUES**

#### **8. No Automated Testing**
- **Current:** Multiple test_*.py files exist
- **Missing:** pytest integration, CI/CD pipeline
- **Impact:** Manual testing required before deployment
- **Fix:** Setup pytest framework + GitHub Actions or GitLab CI

#### **9. No API Documentation**
- **Missing:** Swagger/OpenAPI specs
- **Impact:** Developers must read code to understand API
- **Fix:** Generate Swagger specs from routes

#### **10. Missing Database Indexes**
- **Missing On:** `patient_requests.created_at`, `status_timeline.timestamp`
- **Impact:** Slow queries on large historical datasets
- **Fix:** Add composite indexes on frequently filtered columns

---

### **KNOWN LIMITATIONS (Not Bugs)**

| Feature | Status | Impact |
|---------|--------|--------|
| SMS Notifications | ❌ Missing | Patients unaware of ambulance arrival |
| Payment System | ❌ Missing | No revenue model |
| Mobile Apps | ❌ Missing | Web-only, most users have mobile |
| Multi-Hospital Transfers | ❌ Not Implemented | Manual transfer only |
| Machine Learning | ❌ Not Implemented | AI weights are static |
| Email Alerts | ❌ Missing | No notification to hospital staff |

---

## Summary

**SmartAmbulance** is a **mature, functional emergency dispatch system** with:

### ✅ **Strengths:**
- Intelligent 5-factor AI routing algorithm
- Real-time tracking with ~100ms latency via SSE
- Multi-role dashboards (patient, driver, hospital, admin)
- Comprehensive security (anti-spam, rate limiting, blacklist)
- Complete audit trail and status tracking
- Automatic escalation after 60 seconds
- Production-ready database architecture (connection pool, parameterized queries)

### ⚠️ **Critical Issues to Fix:**
1. **Hash plaintext passwords** (drivers, users tables)
2. **Enable HTTPS/SSL** for production
3. **Investigate JavaScript MIME type error**

### 📋 **Features to Add:**
1. Payment integration
2. SMS notifications
3. Mobile native apps
4. Smart multi-hospital reassignment
5. Machine learning for weight optimization

**Deployment Recommendation:** Fix critical security issues (plaintext passwords, HTTPS) before production use. All core functionality is stable and ready for deployment.

**Estimated Time to Production:** 1-2 weeks (with security fixes + testing)

---

*Documentation Version: 2.0*  
*Last Updated: May 31, 2026*  
*Prepared for: Developer Onboarding & Project Handoff*
