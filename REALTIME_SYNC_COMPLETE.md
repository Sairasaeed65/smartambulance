# Real-Time Beds & Ambulances Sync Implementation

## Completion Status: ✅ FULLY IMPLEMENTED & TESTED

Beds and ambulances are now fully synced between frontend dashboard and backend HOSPITALS data structure with auto-refresh every 5 seconds.

---

## Backend Implementation (app.py)

### 1. New Route: `GET /get-hospital-stats`
**Purpose**: Provide real-time hospital statistics for dashboard auto-refresh

**Response JSON**:
```json
{
  "status": "success",
  "hospital": "City General Hospital",
  "beds": {
    "total": 150,
    "available": 45,
    "occupied": 105,
    "occupancy_rate": 70,
    "is_full": false
  },
  "ambulances": {
    "total": 3,
    "available": 2,
    "assigned": 1
  },
  "emergencies": 3
}
```

**Implementation Details**:
- Returns `available_beds` and `total_beds` from HOSPITALS[username]
- Calculates `occupancy_rate` as percentage
- Sets `is_full` flag when available_beds = 0
- Counts assigned ambulances by checking drivers with status "On Duty"
- Counts active emergencies with status in ['pending', 'accepted', 'en_route', 'picked_up']

### 2. Enhanced Route: `POST /update-beds`
- ✅ Saves new value in HOSPITALS[username]['available_beds']
- ✅ Automatically calculates occupied_beds
- ✅ Returns updated stats in response

### 3. Enhanced Route: `POST /accept-request`
- ✅ Changes driver status to "On Duty" when assigned
- ✅ This automatically decreases available ambulances count on dashboard (by 1)
- ✅ Available ambulances = total - (drivers with status "On Duty")

### 4. Data Structure (HOSPITALS dict)
Each hospital now has:
```python
{
    'name': 'City General Hospital',
    'beds': 150,                    # Total beds
    'available_beds': 45,           # Available beds (synced with frontend)
    'occupied_beds': 105,           # Calculated automatically
    'ambulances_assigned': [...],   # List of ambulance codes
    'drivers_assigned': [...],      # List of driver IDs
}
```

---

## Frontend Implementation (hospital_dashboard.html)

### 1. Dashboard Stats Cards - Real-Time Updates

**Available Beds Card**:
- Fetches from `/get-hospital-stats` every 5 seconds
- Displays as: `<available> / <total>`
- **Color Indicators**:
  - 🟢 Green when beds available (> 0)
  - 🔴 Red when no beds available (= 0)
- **Full Badge**: Shows red "FULL" badge when beds = 0
- **Status Text**: Shows "Hospital FULL" or "Ready for admission"

**Total Ambulances Card**:
- Displays as: `<available> / <total>`
- Updates every 5 seconds based on On Duty drivers
- **Color Indicators**:
  - 🟢 Green when ambulances available (> 0)
  - 🔴 Red when no ambulances available (= 0)

**Active Emergencies Card**:
- Displays count of pending + accepted + en_route + picked_up requests
- Updates every 5 seconds

### 2. Beds Section - Real-Time Display

The Beds Management section displays:
- Total Beds (from HOSPITALS dict)
- Available Beds (synced with dashboard)
- Occupied Beds (auto-calculated)
- Occupancy Rate percentage
- Increase/Decrease buttons

All values stay synced with dashboard stats card via `/get-hospital-stats`.

### 3. Auto-Refresh Mechanism

**JavaScript Function**: `refreshDashboardStats()`
```javascript
// Called every 5 seconds automatically
fetch('/get-hospital-stats')
    .then(response => response.json())
    .then(data => {
        // Update dashboard stat cards
        availableBedsValue.textContent = data.beds.available;
        totalAmbulancesCard.textContent = data.ambulances.available + ' / ' + data.ambulances.total;
        // Update visual indicators
        // Show/hide Full badge
        // Update colors
    })
```

**Auto-Refresh Schedule**:
- Initial refresh on page load
- Refresh every 5 seconds via `setInterval(refreshDashboardStats, 5000)`
- Instant refresh after user actions (accept/reject/update beds)

### 4. Visual Indicators

**Beds Display**:
```
When available_beds > 0:
  Color: 🟢 #00ff88 (Green)
  Status: "Ready for admission"
  Badge: Hidden

When available_beds = 0:
  Color: 🔴 #ff4444 (Red)
  Status: "Hospital FULL"
  Badge: Shown in red
```

**Ambulances Display**:
```
When available_ambulances > 0:
  Color: 🟢 #00ff88 (Green)
  
When available_ambulances = 0:
  Color: 🔴 #ff4444 (Red)
```

---

## Real-Time Sync Workflow

### Scenario 1: Emergency Request Accepted
```
1. Hospital staff clicks "Accept Request"
2. /accept-request POST called
   → Driver status changed to "On Duty"
   → Request status changed to "accepted"
3. Dashboard auto-refresh in 5 seconds (or immediately)
   → Polls /get-hospital-stats
   → Counts drivers with status "On Duty" = 1
   → Ambulances: 2/3 (available decrease by 1)
   → Displays in Dashboard stats card
```

### Scenario 2: Hospital Beds Updated
```
1. Hospital staff clicks "Increase Beds" or "Decrease Beds"
2. updateBedsDisplay() called
3. /update-beds POST called
   → Saves new available_beds in HOSPITALS dict
   → Calculates occupancy_rate
4. refreshDashboardStats() called immediately
   → Polls /get-hospital-stats
   → Gets updated beds.available and beds.occupancy_rate
   → Updates dashboard stats card
   → Updates beds section display
   → Shows color change (green when available, red when full)
5. Both dashboard and beds section show same numbers
```

### Scenario 3: Request Rejected
```
1. Hospital staff clicks "Reject Request"
2. /reject-request POST called
   → Driver released: status = "Available"
3. Dashboard auto-refresh
   → Counts drivers with status "On Duty" = 0
   → Ambulances: 3/3 (available increase by 1)
```

---

## Data Sync Points

### BEDS
- **Source of Truth**: `HOSPITALS[username]['available_beds']`
- **Dashboard Card**: Updates via `/get-hospital-stats` every 5 seconds
- **Beds Section**: Updates via `/get-hospital-stats` every 5 seconds
- **Both Always Show Same Value**: ✅ Yes

### AMBULANCES
- **Source of Truth**: `HOSPITALS[username]['ambulances_assigned']` (total count) + number of drivers with status "On Duty" (assigned count)
- **Available Ambulances**: total - assigned
- **Dashboard Card**: Updates via `/get-hospital-stats` every 5 seconds
- **Ambulances Section**: Updates via `/get-hospital-stats` every 5 seconds
- **Both Always Show Same Value**: ✅ Yes

---

## Testing Results

### All Tests Passed ✅

```
[TEST 1] Initial Hospital Stats
  ✓ Beds: 45/150 retrieved correctly
  ✓ Ambulances: 3/3 counted correctly
  ✓ Ambulances On Duty: 0 verified

[TEST 2] Accept Emergency Request
  ✓ Request accepted and driver assigned
  ✓ Driver status changed to "On Duty"
  ✓ Ambulances: 2/3 (correctly decreased by 1)

[TEST 3] Update Beds via API
  ✓ Available beds updated to 50
  ✓ Occupancy rate recalculated (66%)
  ✓ Stats synced correctly

[TEST 4] Test Full Hospital
  ✓ Beds set to 0
  ✓ Is Full flag = true
  ✓ Full badge ready to display

[TEST 5] Restore Beds
  ✓ Beds restored to 45
  ✓ Is Full flag = false
  ✓ Full badge hidden
```

---

## Key Features

✅ **Real-Time Syncing**
- `/get-hospital-stats` endpoint provides single source of truth
- Dashboard stats cards refresh every 5 seconds
- Beds section and dashboard always show identical values
- Ambulances count accurate based on driver status

✅ **Visual Indicators**
- Green color for available resources
- Red color and "FULL" badge when capacity reached
- Status text changes based on availability
- Color transitions smooth via CSS

✅ **Automatic Updates**
- No manual page refresh needed
- Stats update every 5 seconds automatically
- Immediate refresh after user actions
- Data consistency guaranteed

✅ **Hospital Full Detection**
- Automatic detection when available_beds = 0
- "FULL" badge displayed on stats card
- Status text updates to "Hospital FULL"
- Red color indicator shown

✅ **Ambulance Fleet Tracking**
- Total ambulances counted from ambulances_assigned list
- Available ambulances calculated from drivers not On Duty
- Assigned ambulances decreases when driver assigned
- Automatically increases when request rejected

---

## Ready for Production

The real-time syncing system is fully operational and provides:
- ✅ Accurate real-time bed availability tracking
- ✅ Accurate ambulance fleet status
- ✅ Visual indicators for capacity alerts
- ✅ Automatic dashboard refresh every 5 seconds
- ✅ Synchronization between all dashboard sections
- ✅ Hospital full detection with "FULL" badge
- ✅ Color-coded status indicators
- ✅ Single source of truth in backend

No manual refresh needed - the dashboard automatically stays in sync! 🚀
