# Admin Panel — Complete Technical Documentation

**Project:** Smart Ambulance Dispatch System  
**Component:** Admin Panel (Beyond Original Proposal)  
**Backend:** Flask (Python), MySQL  
**File:** `app.py`  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Access & Authentication](#2-access--authentication)
3. [Admin Panel Features](#3-admin-panel-features)
4. [Database Tables Added](#4-database-tables-added)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Hospital Approval Workflow](#6-hospital-approval-workflow)
7. [Security & Anti-Spam Measures](#7-security--anti-spam-measures)

---

## 1. Overview

The Admin Panel is a complete backend administration system that was added to the Smart Ambulance Dispatch System **beyond the scope of the original project proposal**. The original proposal covered three roles: patient, hospital, and driver. The Admin Panel introduces a fourth privileged role — the **system administrator** — who can oversee all system activity from a dedicated, session-isolated interface.

### Purpose

The original dispatch system had no mechanism for:
- Verifying or approving hospitals before they could receive emergency calls
- Monitoring whether emergency requests were genuine or fraudulent
- Managing drivers and users from a central interface
- Generating analytics or performance reports

The Admin Panel addresses all of these gaps and provides a robust operational layer on top of the core dispatch system.

### What the Admin Panel Adds

| Capability | Without Admin Panel | With Admin Panel |
|---|---|---|
| Hospital verification | Any hospital could log in immediately | Hospitals are reviewed and approved before going live |
| Fraud prevention | No spam protection | IP rate limiting, blacklist, phone validation, duplicate detection |
| System visibility | No monitoring | Live dashboard, emergency tracking, driver status, user list |
| Analytics | No reporting | System reports with charts, tables, trends |
| Access control | Self-managed | Central admin revokes and manages any account |

---

## 2. Access & Authentication

### Login

| Field | Value |
|---|---|
| URL | `http://localhost:5000/admin-login` |
| Username | `admin` |
| Password | `admin123` |

Credentials are stored in the `admins` database table (separate from hospitals, drivers, and users).

### Session Design

Admin authentication is completely isolated from other user types. The following session variables are set on successful admin login:

```python
session['user_type'] = 'admin'
session['admin_id']  = <id from admins table>
```

Every admin route is protected by the `is_admin_logged_in()` guard function (defined at line 1393 in `app.py`):

```python
def is_admin_logged_in():
    return (
        session.get('user_type') == 'admin' and
        session.get('admin_id') is not None
    )
```

This ensures no cross-role access is possible:
- A logged-in hospital (`user_type='hospital'`) cannot access any `/admin-*` route
- A logged-in patient or driver session likewise has no access
- Accessing any admin route without a valid admin session redirects to `/admin-login`

---

## 3. Admin Panel Features

### Feature 1 — Dashboard (`/admin-dashboard`)

The main overview page, automatically refreshed with live data. Displays:

- **Total Emergency Requests** — count of all requests in the system
- **Active Emergencies** — requests in non-terminal states (pending, accepted, assigned, en_route, picked_up)
- **Registered Hospitals** — count of all hospitals in the database
- **Available Drivers** — count of drivers with `status = 'available'`

The dashboard also shows a summary table of recent emergency requests with their current status, and highlights any flagged or suspicious entries.

---

### Feature 2 — Hospital Management (`/admin-hospitals`)

Provides full oversight of all hospitals registered in the system. Hospitals are organized into three tabs:

| Tab | Description |
|---|---|
| **All** | Displays every hospital with their verification and approval status |
| **Pending** | Shows hospitals with `status = 'pending'` awaiting admin review |
| **Approved** | Shows hospitals with `status = 'approved'` that are active in dispatch |

**Actions available per hospital:**
- **Approve** — Sets the hospital's status to `approved`. The hospital can now log in and receive emergency assignments.
- **Reject** — Opens a modal asking for a rejection reason. Sets status to `rejected` and stores the reason in the database.
- **Remove** — Permanently deletes the hospital record.
- **Verify** — Legacy verification toggle (separate from the approval flow).

A **live sidebar badge** displays the current count of pending hospitals, fetched via `/admin-api/pending-count`. This badge updates automatically and draws admin attention to hospitals waiting for review.

---

### Feature 3 — Driver Monitoring (`/admin-drivers`)

Provides a list of all registered drivers with real-time status. For each driver, the following is shown:

- Driver name, phone, and license number
- Assigned ambulance
- Assigned hospital
- Current status (`available`, `busy`, `off_duty`)
- Last location update timestamp

A **live refresh** endpoint (`/admin-drivers-live`) allows the page to poll for updated driver data without a full page reload. Admin can click any driver to open a **detailed view** (`/admin-driver-details/<id>`) showing their full profile, assignment history, and photo. Drivers can be permanently removed via `/admin-remove-driver/<id>`.

---

### Feature 4 — Emergency Oversight (`/admin-emergencies`)

Provides a full audit trail of every emergency request ever submitted to the system. For each entry, the following is displayed:

- Patient name and phone number
- Submission timestamp and GPS coordinates
- Current status in the dispatch lifecycle
- Assigned hospital and driver (if dispatched)
- **Suspicious flag** — marks requests that triggered anti-spam heuristics
- **Blacklisted indicator** — marks requests from blacklisted phone numbers

The **live refresh** endpoint (`/admin-emergencies-live`) keeps the list current. Clicking any emergency opens a **detailed view** (`/admin-emergency-details/<request_id>`) that shows the full status timeline — every state transition with its timestamp.

---

### Feature 5 — User Management (`/admin-users`)

Shows all registered users (patients who created accounts in the system). For each user:

- Full name, email, phone
- Account registration date
- Link to detailed user profile (`/admin-user-details/<id>`)

Admin can permanently remove any user account via `/admin-remove-user/<id>`.

---

### Feature 6 — System Reports (`/admin-reports`)

A dedicated analytics page providing a historical overview of system performance. All data is drawn live from the database — no mock or hardcoded values. The page contains:

| Section | Type | Description |
|---|---|---|
| Summary Cards | 4 stat cards | Total emergencies, approved hospitals, active drivers, system uptime |
| 7-Day Trend | Bar chart (Chart.js) | Daily emergency request count over the last 7 days |
| Status Breakdown | Doughnut chart (Chart.js) | Distribution of requests across all status values |
| Hospital Performance | Table | Per-hospital: total requests, completed, success rate, response quality badge |
| Driver Activity | Table | Per-driver: total dispatches, completed runs, average response metric |
| 30-Day Trend | Line chart (Chart.js) | Monthly activity trend with gradient fill |

Charts are rendered using **Chart.js** (loaded from CDN: `https://cdn.jsdelivr.net/npm/chart.js`).

---

### Feature 7 — Anti-Spam Protection

A multi-layered system to prevent abuse of the emergency request endpoint. This is enforced at the point of every `POST /emergency` request before a dispatch is attempted. See [Section 7](#7-security--anti-spam-measures) for full technical details.

---

### Feature 8 — Blacklist System

Admin can maintain a list of phone numbers that are permanently blocked from submitting emergency requests.

| Action | Endpoint | Method |
|---|---|---|
| View all blacklisted numbers | `/admin-api/blacklist` | GET |
| Add a phone to the blacklist | `/admin-api/blacklist` | POST |
| Remove a phone from the blacklist | `/admin-api/unblacklist/<phone>` | POST |

Each blacklist entry stores:
- The phone number
- The reason for blacklisting
- The admin username who added the entry
- The timestamp it was added

The blacklist is checked in real time on every emergency request submission before any dispatch logic runs.

---

## 4. Database Tables Added

The following database additions were made specifically to support the Admin Panel. All changes are applied automatically at application startup via `init_database()` using `IF NOT EXISTS` and `IF NOT EXISTS` column checks to ensure safe re-runs.

### `admins` Table

Stores admin login credentials. Created during initial database setup.

```sql
CREATE TABLE IF NOT EXISTS admins (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

A default admin account (`admin` / `admin123`) is inserted on first run if no admin exists.

---

### `blacklist` Table

Stores phone numbers blocked from the emergency service.

```sql
CREATE TABLE IF NOT EXISTS blacklist (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    phone       VARCHAR(20) UNIQUE NOT NULL,
    reason      TEXT,
    blocked_by  VARCHAR(50),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

### Additions to `hospitals` Table

Two columns were added to support the approval workflow:

```sql
ALTER TABLE hospitals
    ADD COLUMN status           ENUM('pending','approved','rejected') DEFAULT 'approved',
    ADD COLUMN rejection_reason VARCHAR(255) NULL;
```

- `status` defaults to `'approved'` so that all **existing** hospitals remain fully operational after the migration.
- New hospitals registered after this change default to `'pending'` and must be explicitly approved.

---

### Addition to `patient_requests` Table

One column was added to support IP-based rate limiting:

```sql
ALTER TABLE patient_requests
    ADD COLUMN ip_address VARCHAR(45) NULL;
```

The client IP address is captured from `request.remote_addr` on every emergency submission and stored here. The `check_rate_limit_db()` helper queries this column to enforce the 5-minute cooldown.

---

## 5. API Endpoints Reference

All admin routes require an active admin session. Any request without `session['user_type'] == 'admin'` and a valid `session['admin_id']` is redirected to `/admin-login`.

### Authentication

| Method | URL | Description |
|---|---|---|
| GET / POST | `/admin-login` | Render login form (GET) or authenticate admin (POST). Sets `session['user_type'] = 'admin'` and `session['admin_id']` on success. |
| GET | `/admin-logout` | Clears the admin session and redirects to `/admin-login`. |

---

### Dashboard & Reports

| Method | URL | Description |
|---|---|---|
| GET | `/admin-dashboard` | Main dashboard. Queries live counts for emergencies, hospitals, drivers. Renders `admin_dashboard.html`. |
| GET | `/admin-reports` | Analytics page. Queries 7-day trend, 30-day trend, status breakdown, hospital performance, driver activity. Renders `admin_reports.html`. |

---

### Hospital Management

| Method | URL | Description |
|---|---|---|
| GET | `/admin-hospitals` | Lists all hospitals split into three groups: all, pending, approved. Renders `admin_hospitals.html`. |
| POST | `/admin-verify-hospital/<id>` | Legacy endpoint. Toggles `is_verified` flag on a hospital. |
| POST | `/admin-remove-hospital/<id>` | Permanently deletes a hospital record by ID. |
| POST | `/admin-approve-hospital/<id>` | Sets `status = 'approved'` for the specified hospital. The hospital can now log in and receive dispatches. |
| POST | `/admin-reject-hospital/<id>` | Sets `status = 'rejected'` and stores the provided rejection reason. The hospital will see this reason when they attempt to log in. |
| GET | `/admin-api/pending-count` | Returns a JSON object `{"count": N}` with the number of hospitals in `status = 'pending'` state. Used by the sidebar badge. |

---

### Driver Management

| Method | URL | Description |
|---|---|---|
| GET | `/admin-drivers` | Lists all drivers with status, assignment, and last update. Renders `admin_drivers.html`. |
| GET | `/admin-drivers-live` | Returns updated driver list as JSON for background polling (no full page reload). |
| GET | `/admin-driver-details/<id>` | Returns the full profile for a single driver including assigned ambulance, hospital, photo. Renders `admin_driver_details.html`. |
| POST | `/admin-remove-driver/<id>` | Permanently deletes a driver record by ID. |

---

### Emergency Oversight

| Method | URL | Description |
|---|---|---|
| GET | `/admin-emergencies` | Lists all emergency requests with status, flags, and blacklist indicators. Renders `admin_emergencies.html`. |
| GET | `/admin-emergencies-live` | Returns updated emergency list as JSON for background polling. |
| GET | `/admin-emergency-details/<request_id>` | Returns full detail for a single emergency including complete status timeline. Renders `admin_emergency_details.html`. |
| GET | `/admin-api/emergency-stats` | Returns live statistics as JSON: total requests, active requests, completed today. Used by dashboard polling. |

---

### User Management

| Method | URL | Description |
|---|---|---|
| GET | `/admin-users` | Lists all registered user accounts. Renders `admin_users.html`. |
| GET | `/admin-user-details/<id>` | Returns full profile for a single user. Renders `admin_user_details.html`. |
| POST | `/admin-remove-user/<id>` | Permanently deletes a user account by ID. |

---

### Blacklist Management

| Method | URL | Description |
|---|---|---|
| GET | `/admin-api/blacklist` | Returns the full blacklist as a JSON array. Each entry includes phone, reason, blocked_by, and created_at. |
| POST | `/admin-api/blacklist` | Adds a phone number to the blacklist. Request body: `{ "phone": "...", "reason": "..." }`. Returns `{ "success": true }` or an error. |
| POST | `/admin-api/unblacklist/<phone>` | Removes the specified phone number from the blacklist. Returns `{ "success": true }`. |

---

## 6. Hospital Approval Workflow

The following workflow governs the lifecycle of a hospital account from creation to operational status in the dispatch system.

### Step-by-Step Flow

```
Hospital Account Created
        │
        ▼
  status = 'pending'
  (Default for new hospitals)
        │
        ▼
Admin visits /admin-hospitals → Pending Tab
        │
        ├── Admin clicks "Approve"
        │         │
        │         ▼
        │   POST /admin-approve-hospital/<id>
        │   status = 'approved'
        │         │
        │         ▼
        │   Hospital can log in ✓
        │   Hospital appears in dispatch ✓
        │
        └── Admin clicks "Reject" → enters reason
                  │
                  ▼
          POST /admin-reject-hospital/<id>
          status = 'rejected'
          rejection_reason = <admin's message>
                  │
                  ▼
          Hospital attempts login
                  │
                  ▼
          Login blocked — rejection reason shown ✗
```

### Dispatch Protection

All five locations in `app.py` where hospitals are queried for dispatch purposes use the following filter:

```sql
AND COALESCE(status, 'approved') = 'approved'
```

This ensures that:
1. Pending hospitals are **never** assigned an emergency
2. Rejected hospitals are **never** assigned an emergency
3. Legacy hospitals without a status value (NULL) are treated as approved (backward compatible)

The affected queries are in: `/emergency` (forced dispatch), `/emergency` (distance-based dispatch), `/nearest-hospitals`, and the auto-reroute logic.

### Hospital Login Response by Status

When a hospital submits their credentials at `/hospital-login`, the system checks their status before allowing access:

| `status` value | Login result |
|---|---|
| `'approved'` | Login succeeds, hospital is redirected to their dashboard |
| `'pending'` | Login blocked — message: *"Your account is under review by the administrator"* |
| `'rejected'` | Login blocked — rejection reason is displayed from `rejection_reason` column |

---

## 7. Security & Anti-Spam Measures

The following security measures are enforced at the `/emergency` endpoint (`POST /emergency`) before any dispatch logic is executed. They are implemented as standalone helper functions in `app.py`.

### Measure 1 — IP Rate Limiting

**Function:** `check_rate_limit_db(ip_address)`  
**Location:** `app.py` line ~670  

Enforces a **5-minute cooldown per IP address**. The client's IP is read from `request.remote_addr` on each submission. The function queries the `patient_requests` table for the most recent submission from that IP within the last 5 minutes:

```python
SELECT MAX(timestamp) AS last_ts
FROM patient_requests
WHERE ip_address = %s AND timestamp >= %s   -- %s = now - 5 minutes
```

If a recent request exists, the function calculates the remaining wait time (in minutes, rounded up) and returns it to the caller. The endpoint responds with HTTP 429 and a human-readable message: *"Please wait N minute(s) before sending another request."*

**Exemption:** Localhost addresses (`127.0.0.1`, `::1`) are exempt from rate limiting to allow local testing.

---

### Measure 2 — Pakistani Phone Number Validation

**Function:** `validate_phone_pk(phone)`  
**Location:** `app.py` line ~628  

Every emergency request must include a valid Pakistani mobile phone number. The validation rules are:

1. Phone must be provided and non-empty
2. Exactly **11 digits** after stripping non-numeric characters
3. Must **start with `03`** (Pakistani mobile prefix)
4. Must **not be all the same digit** (e.g., `03333333333` is rejected as likely fake)

Invalid phones return HTTP 400 with a specific error message indicating which rule failed.

---

### Measure 3 — Blacklist Check

**Function:** `check_blacklist_db(phone)`  
**Location:** `app.py` line ~651  

After phone validation passes, the number is looked up in the `blacklist` table:

```python
SELECT reason FROM blacklist WHERE phone = %s
```

If a match is found, the request is rejected with HTTP 403. The reason is logged internally but the public-facing error message is generic: *"This phone number is restricted from using the service."* This avoids revealing specific blacklist logic to abusers.

---

### Measure 4 — Duplicate Active Request Detection

**Function:** `check_duplicate_active_request(phone)`  
**Location:** `app.py` line ~700  

Prevents the same phone number from submitting multiple simultaneous emergency requests. The function checks for any existing request in a non-terminal state:

```python
SELECT request_id FROM patient_requests
WHERE patient_phone = %s
  AND status IN ('pending','accepted','assigned','en_route','picked_up')
  AND (cancelled IS NULL OR cancelled = 0)
LIMIT 1
```

If an active request exists, HTTP 409 is returned: *"You already have an active emergency request. Please wait for it to complete."*

---

### Measure 5 — GPS Coordinate Validation

Before any anti-spam checks, the submitted GPS coordinates are validated:

1. Both `latitude` and `longitude` must be present (HTTP 400 if missing)
2. Both must be valid floating-point numbers (HTTP 400 if malformed)
3. The location must not be `(0, 0)` — a common placeholder that indicates no real location (HTTP 400)
4. Coordinates must be within valid Earth bounds: latitude `[-90, 90]`, longitude `[-180, 180]`

---

### Measure 6 — IP Address Storage

The client IP address is captured and stored in `patient_requests.ip_address` for every successfully submitted emergency request. This serves two purposes:

1. **Rate limiting** — enables the 5-minute cooldown check described above
2. **Audit trail** — admin can review request history and correlate suspicious activity to specific IP addresses in the Emergency Oversight panel

---

### Security Layer Order

Requests to `POST /emergency` pass through the following checks **in order**. The first failure short-circuits the remaining checks:

```
1. GPS coordinate present and valid
2. IP rate limit check (HTTP 429 if triggered)
3. Patient phone format validation (HTTP 400 if invalid)
4. Blacklist check (HTTP 403 if blacklisted)
5. Duplicate active request check (HTTP 409 if duplicate)
6. → Dispatch logic begins
```

---

### Admin Session Security

- All admin routes call `is_admin_logged_in()` before executing any logic
- The admin session uses two independent checks (`user_type` AND `admin_id`) to prevent partial-session exploitation
- Admin credentials are stored in a separate `admins` table, entirely independent of the `hospitals`, `users`, and `drivers` tables
- There is no password reset or self-registration path for admin — credentials must be set directly in the database

---

*Documentation generated for Final Year Project submission.*
