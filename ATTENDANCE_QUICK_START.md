# Attendance System - Quick Start Guide

## What's New

Your SmartAmbulance driver dashboard now includes a **comprehensive Attendance System** that allows drivers to:
- ✓ Mark themselves present for their shift
- ✓ Request leave with reason
- ✓ View attendance calendar with color-coded status
- ✓ See recent attendance history (last 7 days)

---

## Getting Started

### 1. Initialize Database (if needed)

The attendance tables are automatically created when you run:

```bash
python db_setup.py
```

If upgrading an existing installation, the system automatically adds the `profile_pic` column to the drivers table.

### 2. Start the Flask App

```bash
python app.py
```

The app will start on http://localhost:5000

### 3. Login as Driver

Use test credentials:
- **Username:** `DRV-001`
- **Password:** `pass123`

Other test drivers: `DRV-002`, `DRV-003`, `DRV-004` (all use password `pass123`)

---

## Using the Attendance System

### 1. Navigate to Attendance Tab

In the driver dashboard, click the **"Attendance"** tab in the left sidebar (calendar icon).

### 2. View Calendar

**Left Panel - Calendar:**
- Shows current month with color-coded dates
- Navigate months using Previous/Next buttons
- Colors indicate status:
  - **Green** = Present (confirmed)
  - **Orange** = On Leave
  - **Red** = Leave Rejected  
  - **Dashed** = Pending approval
  - **Green glow** = Today (if unmarked)
  - **Grey** = Future dates

### 3. Mark Present

**Right Panel - Today's Card:**

If you haven't marked attendance yet:
1. Click **"Mark Present"** button
2. You'll be marked present for today
3. Calendar updates immediately

### 4. Request Leave

If you haven't marked attendance yet:
1. Click **"Request Leave"** button
2. A modal form opens
3. Enter reason (minimum 10 characters)
4. Click **"Submit Request"**
5. Status shows as "Pending" until admin approves

Example reasons:
- "Personal medical appointment required for health checkup"
- "Family emergency requiring immediate attention"
- "Vehicle maintenance and repair appointment"

### 5. View History

**Right Panel - Recent Records:**
- Shows last 7 days of attendance
- Each record displays: Date, Status, Admin Status, Reason (if applicable)
- Scrollable if more than 5 records

---

## Features

### Calendar Color System

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green Solid | Present (Approved) | You marked present and it's confirmed |
| 🟢 Green Dashed | Present (Pending) | Awaiting admin confirmation |
| 🟠 Orange Solid | Leave (Approved) | Your leave request was approved |
| 🟠 Orange Dashed | Leave (Pending) | Waiting for admin to approve your leave request |
| 🔴 Red Solid | Leave (Rejected) | Your leave request was denied |
| 🟢 Green Glow | Today (Unmarked) | Today's date - click to mark attendance |
| ⚪ Grey | Future | Can't mark dates in the future |

### Today's Status Card

Shows current status and quick actions:
- **If already marked:** Displays your status, admin approval status, and leave reason (if applicable)
- **If not marked:** Shows two buttons:
  - **Mark Present** (Green) - Quick attendance marking
  - **Request Leave** (Orange) - Open leave request form

### Recent Attendance History

Displays your last 7 days of attendance records with:
- Date in short format (Mar 10)
- Status badge (Present/On Leave)
- Admin status (Pending/Approved/Rejected)
- Leave reason preview (if applicable)

---

## Photo Upload (Profile Feature)

When you first view your profile in the dashboard:
1. Click the camera icon on your avatar (bottom-right corner)
2. Select a photo from your device
3. Photo preview shows immediately
4. Uploaded to server and saved to your profile

Supported formats: JPG, PNG, GIF (max size handled by server)

---

## Testing Scenarios

### Scenario 1: Mark Present
```
1. Login as DRV-001
2. Go to Attendance tab
3. Click "Mark Present"
4. Observe calendar shows green for today
5. Recent records show new entry
```

### Scenario 2: Request Leave
```
1. Login as DRV-002
2. Go to Attendance tab
3. Click "Request Leave"
4. Enter: "Doctor appointment for monthly checkup"
5. Click "Submit Request"
6. Observe calendar shows orange dashed (pending)
7. Admin status shows "pending"
```

### Scenario 3: View History
```
1. Login as DRV-001
2. Go to Attendance tab
3. Look at right panel Recent Records section
4. Navigate calendar months to see historical patterns
5. Note color coding matches records
```

### Scenario 4: Multiple Days
```
1. Mark attendance on multiple days
2. Navigate calendar backwards with Previous button
3. See multiple colored dates showing your attendance history
4. Observe patterns in Recent Records
```

---

## Technical Details

### Request Format

**Mark Present:**
```javascript
POST /mark-attendance
{
    "status": "Present"
}
```

**Request Leave:**
```javascript
POST /mark-attendance
{
    "status": "On Leave",
    "leave_reason": "Reason for leave (min 10 characters)"
}
```

### Response Format

```javascript
{
    "status": "success" | "error",
    "message": "Description of action or error"
}
```

### Database Tables

**attendance_records:**
- Tracks all driver attendance
- One record per driver per day
- Fields: date, status (Present/On Leave), admin_status (pending/approved/rejected), leave_reason

**drivers (updated):**
- New `profile_pic` column for uploaded photos
- Stores photo URL (/static/driver_photos/filename)

---

## Troubleshooting

### Calendar Not Showing

**Issue:** Attendance tab appears but calendar is empty

**Solution:**
1. Check browser console (F12 → Console) for errors
2. Verify database has attendance_records table
3. Refresh page (Ctrl+R)
4. Check Flask console for SQL errors

### Can't Mark Attendance

**Issue:** Buttons not working or getting error

**Solution:**
1. Ensure you're logged in as a driver
2. Check that today's date is not already marked
3. Verify /mark-attendance route is working:
   ```bash
   curl -X POST http://localhost:5000/mark-attendance \
     -H "Content-Type: application/json" \
     -d '{"status": "Present"}'
   ```

### Leave Reason Too Short

**Issue:** Getting error "Leave reason required (min 10 characters)"

**Solution:**
- Enter at least 10 characters in the leave reason field
- Include spaces and punctuation in your count
- Example: "Doctor appointment" (18 characters) ✓

### Photos Not Uploading

**Issue:** Camera icon doesn't work or photo not saving

**Solution:**
1. Check that /static/driver_photos directory exists
2. Verify Flask app has permission to write to disk
3. Check browser console for Upload error
4. File must be under 50MB
5. Format must be: JPG, PNG, or GIF

---

## Unit Tests

Run the included test suite to verify installation:

```bash
python test_attendance.py
```

Expected output:
```
Results: 6/6 tests passed
✓ All tests passed! Attendance system is ready.
```

---

## Integration Tests

To test the complete flow (requires Flask running):

```bash
# Terminal 1:
python app.py

# Terminal 2 (in new window):
python test_attendance_integration.py
```

Tests:
- Driver login flow
- Dashboard data loading
- Attendance marking
- Leave requests
- Input validation

---

## Files Reference

### Backend
- `app.py` - Contains /driver-dashboard and /mark-attendance routes
- `db_setup.py` - Database schema with attendance_records table

### Frontend
- `templates/driver_dashboard.html` - Attendance UI and JavaScript
- `static/driver_photos/` - Photo upload directory

### Documentation
- `ATTENDANCE_SYSTEM_COMPLETE.md` - Full technical documentation
- This file - Quick start guide

### Tests
- `test_attendance.py` - Unit tests (database and schema)
- `test_attendance_integration.py` - Integration tests (API flow)

---

## Support

For issues or questions:

1. **Check the logs:**
   - Python console: Flask error messages
   - Browser console: Frontend errors (F12)
   - MySQL logs: Database errors

2. **Read the documentation:**
   - `ATTENDANCE_SYSTEM_COMPLETE.md` for technical details
   - Code comments in app.py and driver_dashboard.html

3. **Run tests:**
   - `python test_attendance.py` - Verify database setup
   - `python test_attendance_integration.py` - Test complete flow

---

## Version Info

- **System:** SmartAmbulance Driver Dashboard
- **Component:** Attendance Tracking System
- **Status:** Complete ✓
- **Date:** 2026-03-11
- **Tested:** All 6 unit tests passing, integration ready

---

Happy tracking! 📋✓
