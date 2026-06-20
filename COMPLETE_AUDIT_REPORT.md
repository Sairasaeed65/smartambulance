# COMPLETE CODEBASE AUDIT REPORT
## Smart Ambulance System — Full Technical Inventory
**Audited by:** GitHub Copilot (March 27, 2026)  
**Scope:** Every file in the workspace read and analyzed

---

## 1. PROJECT STRUCTURE — Every File and Its Purpose

### Root Python Files
| File | Purpose |
|------|---------|
| `app.py` | **Main application.** 5,430+ lines. All Flask routes, database setup, business logic — everything in one file. Runs on port 5000. |
| `db_setup.py` | Standalone script to create MySQL database and tables. Has seed data (2 hospitals, 4 ambulances, 4 drivers, 2 users). Run independently before app if needed. |
| `app_backup_dict.py` | Old backup of app.py that used Python dicts instead of MySQL. Deprecated/not used. |
| `fix_fk.py` | Utility script to fix foreign key constraint issues in MySQL (runs ALTER TABLE commands). |
| `insert_demo_driver.py` | One-off script to manually insert a demo driver row. |
| `debug_loading.py` | Debug script to test page load speed issues. Not part of running app. |
| `DRIVER_ROUTES_FIXED.py` | Scratch file with corrected driver route code. NOT imported by app.py — standalone reference. |

### Templates (HTML Pages)
| File | Purpose |
|------|---------|
| `templates/index.html` | Landing page. Navbar, hero section, map preview, CNIC+phone login modal, emergency button. |
| `templates/emergency.html` | Emergency page. Patient fills in details and triggers dispatch request with GPS. |
| `templates/hospital_login.html` | Hospital staff login page. Username + password form. Shows demo usernames. |
| `templates/hospital_dashboard.html` | Full hospital management dashboard. 8 sections via sidebar (7,500+ lines). |
| `templates/driver_login.html` | Driver login. Username + password + hospital dropdown. |
| `templates/driver_dashboard.html` | Full driver dashboard. 6 sections: dashboard, assignment, route, attendance, history, profile. |
| `templates/driver_change_password.html` | Simple form for driver to change their password. |
| `templates/user_login.html` | Regular user login page (username/password style — legacy system). |
| `templates/user_dashboard.html` | Logged-in patient dashboard showing their profile data. |
| `templates/track.html` | Public ambulance tracking page. Shows live dispatch status and driver location on Leaflet map. |

### Static JavaScript Files
| File | Purpose |
|------|---------|
| `static/script.js` | Landing page JS. Smooth scroll, emergency button animation (1.5s delay then redirect). |
| `static/home-map.js` | Leaflet map module for the home page map preview. Shows nearby hospitals. |
| `static/emergency-map.js` | Leaflet map for emergency page. `EmergencyMapModule` — shows patient location + hospitals. |
| `static/emergency-page.js` | Main JS logic for emergency page. Handles GPS capture, dispatch API call, countdown. |
| `static/emergency-page-leaflet.js` | Alternative/updated emergency page module using Leaflet. `EmergencyPageModule` IIFE. |
| `static/emergency-simple.js` | Simplified emergency page script — likely experimental or fallback. |
| `static/styles.css` | Main CSS for static pages (landing page styles). |

### Static CSS
| File | Purpose |
|------|---------|
| `static/styles.css` | Global styles for landing page (redundant with inline CSS in templates). |

### Photo Directories
| Directory | Purpose |
|-----------|---------|
| `static/driver_photos/` | Stores uploaded driver profile photos. Named `DRV-XXX_timestamp.png`. |
| `static/hospital_photos/` | Stores uploaded hospital logos and cover photos. Named `hospital_id_type_timestamp.png`. |

### Test Files (Not Part of Running App)
| File | Purpose |
|------|---------|
| `test_attendance.py` | Tests attendance marking and approval API endpoints. |
| `test_attendance_integration.py` | Integration test for full attendance workflow. |
| `test_attendance_new_ui.py` | Tests updated attendance UI interactions. |
| `test_complete_workflow.py` | End-to-end test: login → emergency → dispatch → complete. |
| `test_complete_workflow_new.py` | Updated version of above. |
| `test_comprehensive_login.py` | Tests all three login types (hospital, driver, user). |
| `test_dashboard.html` | Standalone HTML test file for dashboard behavior. |
| `test_debug_requests.py` | Debugs request routing and session issues. |
| `test_driver_ambulance_management.py` | Tests add/remove driver and ambulance from hospital. |
| `test_driver_dashboard.py` | Tests driver dashboard load and data. |
| `test_fixes.py` | Miscellaneous fix verification tests. |
| `test_full_rejection.py` | Tests full reject-and-reroute workflow. |
| `test_hospital_login_flow.py` | Tests hospital login session handling. |
| `test_hospital_workflow.py` | Tests hospital accept/reject/reassign flow. |
| `test_login_simple.py` | Simple login test. |
| `test_management.py` | Tests hospital management features. |
| `test_mysql.py` | Tests MySQL connection and basic queries. |
| `test_new_attendance_ui.py` | Tests new attendance UI. |
| `test_quick_debug.py` | Quick debug test. |
| `test_reassignment.py` | Tests driver rejection and reassignment. |
| `test_route_verification.py` | Verifies all routes return correct HTTP codes. |
| `test_session_fix.py` | Tests session persistence fix. |
| `test_workflow.py` | General workflow test. |

### Documentation Files (35 .md files — reference only, not executable)
Notable ones: `README.md`, `IMPLEMENTATION_ROADMAP.md`, `PROFESSIONAL_EVALUATION.md`, `PROPOSAL_vs_IMPLEMENTATION_ANALYSIS.md`, and many phase-specific implementation notes.

### Other
| File | Purpose |
|------|---------|
| `script.js` | **ROOT-LEVEL duplicate** of `static/script.js`. Probably leftover — not served by Flask. |
| `styles.css` | **ROOT-LEVEL duplicate** of `static/styles.css`. Not served by Flask. |
| `flask_server.log` | Runtime log from previous Flask runs. |
| `flask_test.log` | Test run log. |
| `.venv/` | Python virtual environment. |
| `.vscode/` | VS Code settings. |
| `__pycache__/` | Python bytecode cache. |

---

## 2. DATABASE — All Tables, Columns, Relationships

### Database Name: `smartambulance` (MySQL on localhost:3306, user: root, empty password)

---

### Table 1: `hospitals`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| username | VARCHAR(50) UNIQUE | Login credential |
| password | VARCHAR(255) | **PLAINTEXT — not hashed** |
| name | VARCHAR(100) | Hospital display name |
| address | VARCHAR(255) | |
| phone | VARCHAR(20) | |
| email | VARCHAR(100) | |
| total_beds | INT DEFAULT 150 | |
| available_beds | INT DEFAULT 150 | Controls registration status (0 = unregistered) |
| latitude | DECIMAL(10,8) | Used for Haversine dispatch |
| longitude | DECIMAL(11,8) | |
| specialties | JSON | Array of specialty strings |
| website | VARCHAR(100) | |
| whatsapp | VARCHAR(20) | Added via ALTER TABLE |
| hospital_type | VARCHAR(50) DEFAULT 'Private' | Added via ALTER TABLE |
| gps_latitude | DECIMAL(10,8) | Duplicate GPS field added later |
| gps_longitude | DECIMAL(11,8) | |
| general_beds | INT DEFAULT 0 | |
| icu_beds | INT DEFAULT 0 | |
| emergency_beds | INT DEFAULT 0 | |
| doctors_count | INT DEFAULT 0 | |
| nurses_count | INT DEFAULT 0 | |
| operating_hours | JSON | |
| cover_photo | VARCHAR(255) | File path |
| logo_photo | VARCHAR(255) | File path |
| registration_certificate | VARCHAR(255) | File path |
| is_verified | BOOLEAN DEFAULT FALSE | |
| created_at | TIMESTAMP | |

---

### Table 2: `ambulances`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| ambulance_number | VARCHAR(20) UNIQUE | e.g., SA-001 |
| type | VARCHAR(50) | 'Basic Life Support' / 'Advanced Life Support' |
| status | VARCHAR(50) DEFAULT 'Available' | Available / On Duty |
| hospital_id | INT FK → hospitals(id) | |
| equipment | JSON | Array of equipment strings |
| last_service | DATE | |
| created_at | TIMESTAMP | |

---

### Table 3: `drivers`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| username | VARCHAR(20) UNIQUE | e.g., DRV-001 |
| password | VARCHAR(255) | **PLAINTEXT — not hashed** |
| name | VARCHAR(100) | |
| phone | VARCHAR(20) | |
| cnic | VARCHAR(20) | |
| experience | INT | Years |
| shift | VARCHAR(50) | Morning / Night / Any |
| assigned_ambulance | VARCHAR(20) FK → ambulances(ambulance_number) | |
| status | VARCHAR(50) DEFAULT 'Available' | Available / On Duty |
| hospital_id | INT FK → hospitals(id) | |
| hospital_username | VARCHAR(50) | Denormalized hospital username |
| certifications | JSON | Array of certification strings |
| license | VARCHAR(50) | |
| profile_pic | VARCHAR(255) | File path |
| last_rejected_at | TIMESTAMP NULL | Tracks rejection cooldown |
| current_latitude | DECIMAL(10,8) NULL | Real-time GPS location |
| current_longitude | DECIMAL(11,8) NULL | |
| location_updated_at | TIMESTAMP NULL | When GPS was last updated |
| created_at | TIMESTAMP | |

---

### Table 4: `patient_requests`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| request_id | VARCHAR(20) UNIQUE | e.g., REQ-20260327120000 |
| patient_name | VARCHAR(100) | |
| patient_phone | VARCHAR(20) | |
| pickup_address | VARCHAR(255) | Stringified GPS coords |
| hospital_id | INT FK → hospitals(id) | Auto-assigned nearest hospital |
| reason | VARCHAR(255) | Default: 'Emergency Call' |
| priority | VARCHAR(20) | Default: 'High' |
| status | VARCHAR(50) DEFAULT 'pending' | pending / accepted / assigned / en_route / picked_up / completed / rejected / cancelled / no_hospital_available |
| assigned_driver_id | INT FK → drivers(id) | |
| assigned_driver | VARCHAR(20) | Denormalized driver username |
| rejected_by | JSON | Array of hospital_ids that rejected |
| locked | BOOLEAN DEFAULT FALSE | Prevents double-accept |
| locked_by | INT | |
| locked_at | TIMESTAMP NULL | |
| cancelled | BOOLEAN DEFAULT FALSE | |
| reassignment_count | INT DEFAULT 0 | |
| auto_processed | BOOLEAN DEFAULT FALSE | Was auto-assigned? |
| auto_processed_at | TIMESTAMP NULL | |
| forwarded_from_hospital_id | INT NULL | Which hospital forwarded it |
| latitude | DECIMAL(10,8) | Patient GPS |
| longitude | DECIMAL(11,8) | |
| age | INT | |
| symptoms | TEXT | |
| timestamp | TIMESTAMP | Creation time |

---

### Table 5: `dispatches`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| dispatch_id | VARCHAR(30) UNIQUE | e.g., DSP-2026-20260327120000 |
| request_id | VARCHAR(20) FK → patient_requests(request_id) | |
| patient_name | VARCHAR(100) | Denormalized |
| patient_phone | VARCHAR(20) | Denormalized |
| location | VARCHAR(255) | Denormalized address |
| driver_id | INT FK → drivers(id) | |
| driver_name | VARCHAR(100) | Denormalized |
| ambulance_id | VARCHAR(20) FK → ambulances(ambulance_number) | |
| hospital_id | INT FK → hospitals(id) | |
| status | VARCHAR(50) | dispatched / en_route / picked_up / completed / cancelled / driver_rejected |
| priority | VARCHAR(20) | |
| timestamp | TIMESTAMP | |
| updated_at | TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | |

---

### Table 6: `status_timeline`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| request_id | VARCHAR(20) FK → patient_requests(request_id) | |
| dispatch_id | VARCHAR(30) | |
| old_status | VARCHAR(50) | |
| new_status | VARCHAR(50) | |
| action_by | VARCHAR(50) | Username or 'system' |
| action_type | VARCHAR(50) | driver_update / driver_accepted / driver_rejected / driver_timeout / trip_completed |
| driver_id | INT FK → drivers(id) | |
| driver_name | VARCHAR(100) | Denormalized |
| notes | TEXT | Human-readable description |
| timestamp | TIMESTAMP | |

---

### Table 7: `users`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| username | VARCHAR(50) UNIQUE | For old-style login |
| password | VARCHAR(255) | **PLAINTEXT — not hashed** |
| name | VARCHAR(100) | |
| email | VARCHAR(100) | |
| phone | VARCHAR(20) UNIQUE | Used for CNIC-based login |
| address | VARCHAR(255) | |
| blood_type | VARCHAR(10) | |
| medical_history | TEXT | |
| emergency_contacts | JSON | |
| cnic | VARCHAR(20) UNIQUE | For smart login |
| full_name | VARCHAR(100) | For smart login (parallel to name) |
| user_type | VARCHAR(50) | 'patient' |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | |

---

### Table 8: `attendance_records`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| driver_id | INT FK → drivers(id) | |
| date | DATE | |
| status | VARCHAR(50) DEFAULT 'Present' | Present / On Leave |
| admin_status | VARCHAR(50) DEFAULT 'pending' | pending / approved / rejected |
| leave_reason | TEXT | Required if On Leave |
| admin_id | INT FK → users(id) | Who approved (nullable) |
| approved_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |
| UNIQUE KEY | (driver_id, date) | One record per driver per day |

---

### Relationships Summary
```
hospitals (1) ──< ambulances (many)       FK: ambulances.hospital_id
hospitals (1) ──< drivers (many)          FK: drivers.hospital_id
hospitals (1) ──< patient_requests (many) FK: patient_requests.hospital_id
hospitals (1) ──< dispatches (many)       FK: dispatches.hospital_id
ambulances (1) ──< drivers (many)        FK: drivers.assigned_ambulance
drivers (1) ──< patient_requests (many)  FK: patient_requests.assigned_driver_id
drivers (1) ──< dispatches (many)        FK: dispatches.driver_id
drivers (1) ──< attendance_records (many)FK: attendance_records.driver_id
patient_requests (1) ──< dispatches (many) FK: dispatches.request_id
patient_requests (1) ──< status_timeline (many) FK: via request_id
dispatches (1) ──< status_timeline (many) FK: via dispatch_id
```

### What Data Is Currently Stored
- **`app.py` seed:** `hospitals_data = []` — EMPTY. No seed data in the running app's init.
- **`db_setup.py` seed:** Has 2 hospitals (Dubai coordinates), 4 ambulances, 4 drivers (DRV-001 to DRV-004), 2 users — but this file must be run separately.
- **Real data:** Whatever was entered manually through the dashboard when running locally.

---

## 3. ROUTES & ENDPOINTS — Every URL Route

### Public Routes (No Login Required)
| Route | Method | What It Does | Who Uses It |
|-------|--------|-------------|-------------|
| `/` | GET | Serves landing page (index.html) | Everyone |
| `/emergency` | GET | Serves emergency request page | Patient |
| `/emergency` | POST | Receives GPS, finds nearest hospital, creates patient_request, returns JSON | Patient (JS call) |
| `/dispatch` | POST | Alternative dispatch endpoint. Auto-selects hospital by distance. Supports `forced_hospital_id`. | Patient (JS call) |
| `/track` | GET | Serves ambulance tracking page | Patient |
| `/nearest-hospitals` | POST | Receives lat/lng, returns sorted list of all hospitals with distances | Patient (JS call) |
| `/get-request-status` | GET | Returns full status + timeline for a request_id. No auth. | Patient (polling) |
| `/get-live-tracking` | GET | Returns patient coords, hospital coords, driver live GPS, freshness flag | Patient (polling) |
| `/cancel-request` | POST | Marks request cancelled, frees driver + ambulance | Patient |
| `/check-session` | GET | Debug: returns current session data as JSON | Debug |

### User/Patient Routes
| Route | Method | What It Does | Who Uses It |
|-------|--------|-------------|-------------|
| `/user-login` | GET | Serves user login page with demo usernames | User |
| `/user-login` | POST | Validates username/password (plaintext), creates session, redirects to dashboard | User |
| `/user-smart-login` | POST | CNIC + phone login. Finds or auto-registers new patient. | Patient (index.html modal) |
| `/user-update-profile` | POST | Updates full_name and phone by CNIC | Patient |
| `/user-dashboard` | GET | Serves user dashboard (requires `user` session) | User |
| `/patient-history` | GET | Returns last 20 requests for session patient_phone. Requires `patient` session. | Patient |
| `/logout` | GET | Clears session, redirects home | User |

### Hospital Routes
| Route | Method | What It Does | Who Uses It |
|-------|--------|-------------|-------------|
| `/hospital-login` | GET | Serves hospital login page | Hospital staff |
| `/hospital-login` | POST | Validates username/password (plaintext), creates session | Hospital staff |
| `/hospital-logout` | GET | Clears session | Hospital staff |
| `/hospital-dashboard` | GET | Serves hospital dashboard page. Requires `hospital` session. | Hospital staff |
| `/hospital-profile` | GET | Redirects to hospital-dashboard | Hospital staff |
| `/get-hospital-dashboard-stats` | GET | Returns incoming ambulances, emergency cases, ambulance list | Hospital (async load) |
| `/get-hospital-profile-data` | GET | Returns full hospital profile fields | Hospital |
| `/update-hospital-profile` | POST | Updates hospital info (name, beds, GPS, specialties, hours, etc.) | Hospital |
| `/upload-hospital-logo` | POST | Uploads logo image (max 2MB, PNG/JPG/GIF), saves to static/hospital_photos/ | Hospital |
| `/upload-hospital-cover` | POST | Uploads cover photo (max 2MB) | Hospital |
| `/upload-hospital-certificate` | POST | Uploads registration certificate PDF (max 5MB) | Hospital |
| `/get-hospital-requests` | GET | Returns pending requests for hospital. Respects lock timeout (60s). | Hospital (polling) |
| `/accept-request` | POST | Finds first available driver, assigns, creates dispatch record, marks ambulance On Duty | Hospital |
| `/reject-request` | POST | Marks request as rejected | Hospital |
| `/auto-accept-request` | POST | Auto-processes pending requests: assigns nearest driver OR reroutes to next hospital if no drivers available | Hospital (automated) |
| `/get-hospital-active-requests` | GET | Returns accepted/assigned/en_route/picked_up requests + forwarded requests | Hospital |
| `/get-hospital-history` | GET | Returns requests filtered by month/year with summary stats | Hospital |
| `/get-today-activity` | GET | Returns all today's requests with summary stats | Hospital |
| `/get-hospital-stats` | GET | Returns beds, ambulances, drivers, emergencies counts | Hospital |
| `/get-dispatch-history` | GET | Returns last 50 dispatches for hospital | Hospital |
| `/add-driver` | POST | Creates new driver (auto-generates DRV-XXX username, random 6-digit password, auto-assigns ambulance) | Hospital |
| `/remove-driver` | POST | Deletes driver, frees ambulance | Hospital |
| `/get-drivers` | GET | Returns all drivers for hospital including passwords in JSON | Hospital |
| `/add-ambulance` | POST | Creates new ambulance, auto-assigns to driver with no ambulance | Hospital |
| `/remove-ambulance` | POST | Deletes ambulance, unassigns from driver | Hospital |
| `/get-ambulances` | GET | Returns all ambulances for hospital | Hospital |
| `/get-dispatches` | GET | Returns all dispatches (hospital = by hospital, driver = by driver) | Hospital/Driver |
| `/update-beds` | POST | Updates available_beds count | Hospital |
| `/update-total-beds` | POST | Updates total_beds count | Hospital |
| `/change-driver-password` | POST | Hospital admin changes a driver's password | Hospital |
| `/reset-all-status` | POST | **DESTRUCTIVE** — Resets all drivers/ambulances to Available, deletes ALL requests and dispatches for hospital | Hospital |
| `/get-pending-attendance` | GET | Returns pending leave requests for hospital's drivers | Hospital |
| `/approve-attendance` | POST | Approves or rejects one or batch of attendance records | Hospital |
| `/all-attendance` | GET | Returns last 500 attendance records for hospital | Hospital |
| `/edit-attendance` | POST | Edits a single attendance record | Hospital |
| `/hospital-history` | GET | Returns last 100 dispatches with full timelines and avg response time | Hospital |

### Driver Routes
| Route | Method | What It Does | Who Uses It |
|-------|--------|-------------|-------------|
| `/driver-login` | GET | Serves driver login page with hospital dropdown | Driver |
| `/driver-login` | POST | Validates username/password/hospital_id (plaintext), creates session | Driver |
| `/driver-logout` | GET | Clears session | Driver |
| `/driver-dashboard` | GET | Serves driver dashboard. Requires `driver` session. | Driver |
| `/driver-change-password` | GET | Serves change password form | Driver |
| `/driver-change-password` | POST | Validates old password (plaintext), updates new password (plaintext) | Driver |
| `/driver-upload-photo` | POST | Uploads profile photo, saves to static/driver_photos/ | Driver |
| `/mark-attendance` | POST | Marks Present or submits leave request (single day or date range) | Driver |
| `/check-assignment` | GET | Returns active dispatch assignment. Auto-rejects and reassigns if no response in 60 seconds. | Driver (polling every 5s) |
| `/driver-respond` | POST | Accept (→ en_route) or Reject (→ reassign to next driver) | Driver |
| `/update-driver-location` | POST | Updates current_latitude, current_longitude, location_updated_at in drivers table | Driver (GPS watchPosition) |
| `/update-dispatch-status` | POST | Updates status: en_route, picked_up, completed. On complete: frees driver + ambulance, logs timeline. | Driver |
| `/get-driver-live-data` | GET | Returns current assignment + today's completed trips | Driver |
| `/driver-history` | GET | Returns last 50 completed trips with timelines and durations | Driver |

**Total Routes: 62 endpoints**

---

## 4. FEATURES IMPLEMENTED

### Fully Working ✅
1. **Hospital Login + Session** — username/password works, session persists 24 hours
2. **Driver Login + Session** — username/password/hospital dropdown works
3. **Emergency Page** — GPS capture (browser `navigator.geolocation`), form submission, Leaflet map
4. **Auto Nearest Hospital Selection** — Haversine formula calculates real distances, picks nearest hospital with available_beds > 0
5. **Patient Request Creation** — Creates REQ-YYYYMMDDHHMMSS in database
6. **Hospital Dashboard** — All 8 sections (dashboard, emergencies, today activity, ambulances, beds, drivers, history, profile)
7. **Accept Request** — Assigns first available driver, creates dispatch record, marks ambulance On Duty
8. **Reject Request** — Marks request rejected
9. **Auto-Accept (Hospital Auto-Processing)** — Finds nearest available driver, auto-assigns. If no driver: reroutes to next hospital by distance. If all fail: marks `no_hospital_available`.
10. **Driver Dashboard** — All 6 sections (dashboard, assignment, route, attendance, history, profile)
11. **Check Assignment (Driver Polling)** — 5-second polling, shows dispatch with 60-second countdown
12. **Driver Accept/Reject Assignment** — Accept → en_route. Reject → reassigns to next available driver.
13. **Driver Status Update** — en_route → picked_up → completed with full timeline logging
14. **Status Timeline Logging** — Every status change written to status_timeline table
15. **Driver GPS Location Tracking** — `update-driver-location` stores real-time coords in DB
16. **Live Tracking Page** — Leaflet map shows patient, driver (if GPS available), hospital
17. **Request Status Polling** — Patient can poll `/get-request-status` for real-time updates
18. **Cancel Request** — Patient can cancel, driver + ambulance freed
19. **Add/Remove Drivers** — Hospital can add drivers (auto-generates credentials), remove drivers
20. **Add/Remove Ambulances** — Hospital can manage fleet
21. **Bed Management** — Hospital can update available_beds and total_beds
22. **Driver Attendance — Mark Present/On Leave** — Single day or date range
23. **Hospital Approve/Reject Attendance** — Single or batch approval
24. **History Views** — Hospital history by month/year, driver trip history, today's activity
25. **Hospital Profile Update** — Edit all fields including beds, specialties, GPS coords, operating hours
26. **Photo Uploads** — Hospital logo, cover photo, registration certificate; Driver profile photo
27. **Password Change (Driver)** — Driver can change their own password
28. **Password Change by Hospital** — Hospital admin can reset any driver's password
29. **Smart Patient Login (CNIC+Phone)** — Auto-registers new patients, validates existing
30. **Patient History** — Patient can view last 20 requests with timelines
31. **Hospital History API** — Detailed history with avg response time calculation
32. **60-Second Driver Timeout** — Auto-rejects inactive drivers and reassigns
33. **Forwarded Request Tracking** — `forwarded_from_hospital_id` tracks rerouting chain
34. **Reset All Status** — Hospital debug tool to clear all data

### Partially Working ⚠️
1. **User Dashboard** (`user_dashboard` route) — Requires `user` session type but smart login sets `patient` session. The old legacy login and new CNIC login create DIFFERENT session types. A user who logs in via CNIC is `patient` type, but `/user-dashboard` checks for `user` type — **they are locked out of user dashboard**.
2. **Route Map (Driver)** — Section exists in driver dashboard (`section-route`) with Leaflet map, but has no backend calculation of optimal path — shows static points only.
3. **Ambulance Tracking** — Live GPS updates work when driver reports location, but if driver has no active GPS, the tracking page shows no driver marker. There's no fallback position using hospital coordinates.
4. **Patient History** — `/patient-history` endpoint exists and works, but the frontend page to display it is not clearly accessible from the index or user interface.

### Broken or Missing ❌
1. **No Admin Panel** — Confirmed: zero admin routes, zero admin login, zero admin HTML page. There is no superuser who can manage hospitals, view all data, or approve hospital registrations. All management is per-hospital only.
2. **No Google Maps** — Confirmed: every map is Leaflet.js (open-source). Zero Google Maps API calls anywhere. No traffic data.
3. **No AI/Machine Learning** — Confirmed: the dispatch algorithm is `sort by distance, pick index 0`. No NumPy, no Pandas, no ML model, no prediction.
4. **No Traffic Awareness** — ETA = `(distance / 40) * 60` hardcoded everywhere. 40 km/h is hardcoded for ALL scenarios: midnight, rush hour, any road condition.
5. **No Hospital Registration** — Hospitals cannot register themselves. They must be inserted directly into the database (no signup page exists).
6. **No User Registration (Legacy)** — The old `/user-login` system has no signup route. Users can only be seeded via `db_setup.py` or direct DB insert.
7. **No Input Sanitization on profile fields** — The `update-hospital-profile` route accepts any string for name, phone, email without server-side format validation.
8. **Plaintext Passwords** — All three user types (hospital, driver, user) store and compare passwords in plaintext. Zero hashing.
9. **DB Credentials Hardcoded** — `DB_PASSWORD = ''` in plain Python at the top of app.py. No `.env` file.
10. **Secret Key Hardcoded** — `app.secret_key = 'smartambulance2024secretkey'` in plain code.
11. **No Rate Limiting** — Login endpoints can be brute-forced with unlimited attempts.
12. **`seed_database()` is empty in app.py** — `hospitals_data = []`. The app creates empty tables on startup. Data must come from `db_setup.py` or manual entry.
13. **Driver Password Exposed in `/get-drivers`** — The hospital's `/get-drivers` endpoint returns the password field in its JSON response.
14. **No HTTPS enforcement** — `SESSION_COOKIE_SECURE = False`.
15. **`/reset-all-status`** — Destructive endpoint with no confirmation or soft-delete. Permanently deletes all requests/dispatches for a hospital.

---

## 5. LOGIN SYSTEM

### How Many Login Types Exist
**4 login types:**

| Type | Route | Session `user_type` | Who |
|------|-------|---------------------|-----|
| Hospital | `/hospital-login` | `'hospital'` | Hospital admin/staff |
| Driver | `/driver-login` | `'driver'` | Ambulance drivers |
| User (Legacy) | `/user-login` | `'user'` | Old-style registered users |
| Patient (Smart) | `/user-smart-login` | `'patient'` | Anyone with CNIC + phone |

### How Sessions Work
- Flask server-side sessions using `app.secret_key`
- `session.permanent = True` → lasts 86400 seconds (24 hours) configured via `PERMANENT_SESSION_LIFETIME`
- Session stores: `user_type`, `username`, `hospital_id`, `hospital_name`, `driver_id`, `driver_username`, `name`, `ambulance`, `patient_cnic`, `patient_name`, `patient_phone`
- **No JWT**, no token-based auth — all cookie sessions
- `SESSION_COOKIE_SAMESITE = 'Lax'`, `SESSION_COOKIE_SECURE = False`

### Which Pages Are Protected
| Page/Route | Protection |
|------------|------------|
| `/driver-dashboard` | Requires `user_type == 'driver'` → redirects to `/driver-login` |
| `/driver-change-password` | Requires `user_type == 'driver'` |
| `/driver-upload-photo` | Requires `user_type == 'driver'` → returns 401 JSON |
| `/mark-attendance` | Requires `user_type == 'driver'` |
| `/check-assignment` | Requires `user_type == 'driver'` |
| `/driver-respond` | Requires `user_type == 'driver'` |
| `/update-driver-location` | Requires `user_type == 'driver'` |
| `/update-dispatch-status` | Requires `user_type == 'driver'` |
| `/get-driver-live-data` | Requires `user_type == 'driver'` |
| `/driver-history` | Requires `user_type == 'driver'` |
| `/hospital-dashboard` | Requires `user_type == 'hospital'` → redirects to `/hospital-login` |
| All `/get-hospital-*` routes | Requires `user_type == 'hospital'` → returns 401 JSON |
| All hospital management routes | Requires `user_type == 'hospital'` |
| `/user-dashboard` | Requires `user_type == 'user'` (NOT 'patient') |
| `/patient-history` | Requires `user_type == 'patient'` |
| `/emergency` GET | **Unprotected** — anyone can access |
| `/track` GET | **Unprotected** — public page |
| `/get-request-status` | **Unprotected** — public API |
| `/get-live-tracking` | **Unprotected** — public API |
| `/cancel-request` | **Unprotected** — no auth check |
| `/nearest-hospitals` | **Unprotected** — public API |

---

## 6. FRONTEND PAGES — Every Template

### `templates/index.html` — Landing Page
- **Role:** Everyone (public)
- **What it shows:** Navbar, hero section with "Request Emergency Ambulance" button, Leaflet map showing nearby hospitals, feature highlights, login/profile modal in top-right
- **Login modal:** CNIC (13 digits) + full name + phone (11 digits starting 03). On success: shows profile panel with name, CNIC, phone, edit profile option, history link.
- **Emergency flow:** Click button → captures GPS → redirects to `/emergency` page (1.5s delay)
- **Tech:** Bootstrap 5, Leaflet.js, home-map.js, inline CSS (~500 lines), script.js

### `templates/emergency.html` — Emergency Request Page
- **Role:** Patient (public, no login required)
- **What it shows:** Dark-themed page with pulsing red emergency indicator, Leaflet map (auto-centers on patient GPS), hospital list (registered vs unregistered), ETA display, patient form (name, phone, symptoms)
- **Flow:** GPS captured → POST to `/emergency` → displays auto-selected hospital + all nearby hospitals on map + in sidebar → countdown timer
- **Tech:** Leaflet.js, emergency-page.js, emergency-map.js, Bootstrap 5
- **CSS variables:** `--accent-green: #00ff88`, `--alert-red: #ff3333`, animated `emergencyPulseRed` keyframe

### `templates/hospital_login.html` — Hospital Login
- **Role:** Hospital staff
- **What it shows:** Clean login form, shows demo usernames from DB
- **Tech:** Bootstrap 5, minimal inline CSS

### `templates/hospital_dashboard.html` — Hospital Dashboard
- **Role:** Hospital staff (requires `hospital` session)
- **What it shows:** Full-featured SPA-style dashboard with left sidebar navigation + right sidebar (today's activity)
- **7,500+ lines** — most complex file in the project
- **Sidebar sections:**
  1. **Dashboard** — Stats cards (incoming ambulances, emergency cases, bed occupancy rate, ambulances in area), live map with hospital + patient markers
  2. **Emergencies** — Pending requests table with Accept/Reject buttons, auto-accept button
  3. **Today Activity** (standalone section) — Today's requests with status, driver, durations
  4. **Ambulances** — Fleet table (ambulance number, type, status), Add/Remove buttons
  5. **Beds** — Bed count management: general, ICU, emergency, manual available beds slider
  6. **Drivers** — Driver table with status, ambulance, CNIC, phone; Add driver modal, Remove driver, Change password
  7. **History** — Month/year filter, request table with completion stats
  8. **Profile** — Edit all hospital fields, upload logo/cover/certificate
- **Right sidebar:** Today's activity summary cards (Total, Completed, Forwarded, Active Now)
- **Accepted/Forwarded panels:** Separate expandable panels for accepted requests and forwarded requests
- **Polling:** 15-second auto-refresh on most data via `setInterval`
- **Tech:** Bootstrap 5, Font Awesome, Leaflet.js, Plus Jakarta Sans font, CSS variables `--accent: #2563eb`

### `templates/driver_login.html` — Driver Login
- **Role:** Drivers
- **What it shows:** Login form with hospital dropdown (populated from DB), username, password
- **Tech:** Bootstrap 5

### `templates/driver_dashboard.html` — Driver Dashboard
- **Role:** Drivers (requires `driver` session)
- **What it shows:** Dark military-themed SPA dashboard
- **Sections (6):**
  1. **Dashboard** — Stats cards (active calls, completed today, response time, status), driver info, hospital info
  2. **My Assignment** — Current dispatch card with patient name, phone, location, priority, countdown timer, Accept/Reject buttons
  3. **Route** — Leaflet map showing patient location and hospital. No routing algorithm — just markers.
  4. **Attendance** — Mark present/on leave today, request leave for date range, attendance history table (last 7 days)
  5. **History** — Table of completed trips with duration and timeline
  6. **Profile** — Driver info (read-only view), photo upload button, change password link
- **Polling:** 5-second polling for assignment updates (`/check-assignment`)
- **GPS tracking:** Uses `navigator.geolocation.watchPosition` when active assignment exists; sends updates to `/update-driver-location`
- **Tech:** Bootstrap 5, Font Awesome, Leaflet.js, dark theme (`--bg-dark: #0a0f1e`, `--accent-green: #00ff88`)

### `templates/driver_change_password.html` — Driver Change Password
- **Role:** Driver (requires `driver` session)
- **What it shows:** Simple 3-field form (old password, new password, confirm)
- **Tech:** Bootstrap 5

### `templates/user_login.html` — User Login (Legacy)
- **Role:** Users (legacy)
- **What it shows:** Username/password form, shows demo users from DB
- **Tech:** Bootstrap 5

### `templates/user_dashboard.html` — User Dashboard
- **Role:** User (requires `user` session — NOT `patient` session)
- **What it shows:** User profile info (name, email, phone, address, blood type, medical history)
- **Note:** Smart-login patients (`patient` session) CANNOT access this page — bug/design gap.
- **Tech:** Bootstrap 5

### `templates/track.html` — Ambulance Tracking
- **Role:** Public (no auth required)
- **What it shows:** Input for request ID → Leaflet map showing patient location (blue), hospital (red), driver (green if GPS available) → status timeline list → auto-polls every 5 seconds
- **Tech:** Leaflet.js, polling via `setInterval`

---

## 7. HOSPITAL LOGIC

### How "Registered" Hospitals Work
- **Definition:** A hospital with `available_beds > 0` is considered "registered" (has capacity)
- **In dispatch:** When a patient submits emergency, all hospitals are fetched. Hospitals with `available_beds > 0` are sorted by Haversine distance. The nearest one is auto-selected.
- **In accept flow:** Hospital staff see pending requests, can click Accept (assigns available driver) or Reject
- **In auto-accept:** System finds available drivers for hospital. Assigns nearest by distance proxy (hospital GPS used until driver GPS tracking is available).

### How "Unregistered" Hospitals Work
- **Definition:** Any hospital with `available_beds = 0`
- **In dispatch:** If ALL registered hospitals fail (no beds), nearest unregistered hospital is used as last resort fallback
- **They still appear** on the emergency map as markers, but in a separate "unregistered" list
- **They cannot accept requests** in the current flow (no staff assigned, no driver check)
- **Note:** This "registered/unregistered" distinction is entirely controlled by the `available_beds` column — not by any verified registration status.

### How Ambulance Dispatch Works
The full dispatch flow has **3 levels** of escalation:

**Level 1 — Patient submits emergency:**
1. Patient GPS coordinates sent to `/emergency` (POST) or `/dispatch` (POST)
2. All hospitals with lat/lng fetched from DB
3. Haversine formula calculates distance to each
4. Hospitals with `available_beds > 0` = registered list; `available_beds == 0` = unregistered list
5. Both lists sorted by distance
6. Nearest registered hospital auto-selected (or nearest unregistered if no registered hospitals)
7. `patient_requests` record created with `status = 'pending'`, `hospital_id = selected`

**Level 2 — Hospital processes request:**
- **Manual:** Hospital staff see pending request in dashboard → click Accept → system picks first available driver (has ambulance, status = Available) → dispatch created → driver status = On Duty
- **Auto:** Hospital calls `/auto-accept-request` → finds nearest available driver by distance → assigns → creates dispatch → driver notified. If NO drivers available: adds hospital to `rejected_by` array → finds next nearest registered hospital not in `rejected_by` → reroutes request to that hospital. If ALL hospitals exhausted: status = `no_hospital_available`.

**Level 3 — Driver responds:**
- Driver dashboard polls `/check-assignment` every 5 seconds
- On receipt: 60-second countdown shown; driver must Accept or Reject
- **Accept:** `status = en_route` → driver proceeds to patient
- **Reject / Timeout (60s):** Driver marked with `last_rejected_at`, cooldown 5 minutes; next available driver at same hospital auto-assigned
- Driver then updates status: `en_route` → `picked_up` → `completed`
- On `completed`: driver and ambulance both freed back to `Available`

---

## 8. WHAT IS MISSING

### No Admin Panel — CONFIRMED ❌
There is **zero** admin functionality anywhere in the codebase:
- No `/admin-login` route
- No admin HTML template
- No admin session check anywhere
- No superuser role in the database
- No ability to: view all hospitals, approve hospital registrations, manage all requests system-wide, view global statistics, add/delete hospitals from the UI, audit logs

**Impact:** To add a hospital, someone must run a raw SQL INSERT or modify `db_setup.py`. Hospitals cannot self-register. There is no oversight of the system.

### No Google Maps — CONFIRMED ❌
- Zero Google Maps API calls anywhere in the codebase
- Zero `maps.googleapis.com` references
- Every map uses **Leaflet.js 1.9.4** (open source, offline)
- Tile server: OpenStreetMap (free)
- Zero traffic data integration
- Zero real routing (just straight lines between markers or standard tile display)

### Other Confirmed Gaps

| Gap | Status |
|-----|--------|
| **No AI/ML** | ❌ `sort(by distance)[0]` is the entire "AI". No NumPy, Pandas, or ML anywhere. |
| **No traffic awareness** | ❌ ETA = `(distance / 40) * 60` hardcoded everywhere. Ignores time of day, roads, congestion. |
| **No hospital self-registration** | ❌ No signup page. Hospitals must be added via DB. |
| **No password hashing** | ❌ All passwords stored/compared in plaintext. Critical security vulnerability. |
| **No .env / config file** | ❌ DB credentials, secret key hardcoded in app.py. |
| **Passwords in /get-drivers response** | ❌ Driver passwords returned in JSON API response. Should be excluded. |
| **No SMS/push notifications** | ❌ No alerts sent to patient after dispatch. No Twilio or similar integration. |
| **No email notifications** | ❌ No email on registration, password change, or dispatch. |
| **No role-based access beyond session type** | ❌ No permissions beyond user_type check. Any hospital can access any public route. |
| **cancel-request has no auth** | ❌ Anyone who knows a request_id can cancel it. No ownership check. |
| **Driver section-route has no routing** | ❌ Map shows markers only. No turn-by-turn, no road routing. |
| **User dashboard broken for CNIC patients** | ❌ Smart-login sets `user_type = 'patient'` but `/user-dashboard` requires `user_type = 'user'`. |
| **app.py is monolithic** | ❌ 5,430+ lines, no blueprints, no service layer, no separation of concerns. Very hard to maintain. |
| **No database migrations** | ❌ Schema changes done via ALTER TABLE in init_database() on every startup — fragile. |
| **No pagination on most list endpoints** | ❌ `/get-drivers`, `/get-ambulances` etc. have no pagination. Would break with hundreds of records. |
| **reset-all-status is destructive** | ⚠️ Deletes all patient_requests and dispatches with no confirmation or undo. |
| **No HTTPS** | ❌ SESSION_COOKIE_SECURE = False |

---

## 9. QUICK REFERENCE — Key Facts for Planning

### What works well enough to demo
- Full emergency request flow (patient → hospital notification → driver assignment → completion)
- Hospital dashboard with all management features
- Driver dashboard with all features
- Real GPS tracking on driver and patient side
- Attendance system
- History and reporting

### What needs to be built first (critical)
1. **Password hashing** (werkzeug `generate_password_hash` / `check_password_hash`) — security critical
2. **Admin panel** — needed to manage hospitals, users, system data
3. **Hospital self-registration** — so hospitals can sign up without DB access
4. **Fix user_type mismatch** — `patient` vs `user` session types

### What needs to be added for proposal compliance
1. **Traffic-aware ETA** — replace hardcoded 40 km/h with hourly speed variation
2. **Multi-factor hospital scoring** — add bed availability % and response history to selection
3. **Google Maps integration** — to show actual road routes instead of straight lines

### File to edit for any feature
- **All backend:** `app.py` (one file — 5,430 lines)
- **Hospital UI:** `templates/hospital_dashboard.html` (7,500+ lines)
- **Driver UI:** `templates/driver_dashboard.html` (2,500+ lines)
- **Patient flow:** `templates/emergency.html` + `static/emergency-page.js`
- **Landing page:** `templates/index.html` + `static/script.js`

---

*This audit was generated by reading every file in the workspace on March 27, 2026.*
