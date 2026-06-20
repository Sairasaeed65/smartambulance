# Driver Route Section - User Guide

## 📍 What's New

The **Route Section** now provides real-time navigation assistance with live location tracking, distance calculations, and estimated arrival times to help you efficiently reach patients.

## 🗺️ Map Display

### Map Features
- **Dark Theme**: Eye-friendly display, especially during night operations
- **Your Location**: Green pulsing marker showing your current position
- **Patient Location**: Red marker showing where the patient is waiting (when you have an assignment)
- **Route Line**: Green dashed line connecting you to the patient
- **Zoom Controls**: Bottom right corner for manual map zoom

### Understanding the Markers

#### 🟢 Green Pulsing Marker
- Shows YOUR current location
- Updates every 3-5 seconds from your phone's GPS
- Pulsing animation indicates system is tracking you
- Click to see: "Your Location"

#### 🔴 Red Marker  
- Shows PATIENT location
- Only appears when you have an active assignment
- Click to see: "Patient Location"

## 📊 Information Cards

### Current Location Card
- **Coordinates**: Your exact GPS position (latitude, longitude)
- **Updates**: Every location update
- **Precision**: Accurate to 0.0001 degrees
- **Use Case**: Share with dispatch if needed

### Status Card
- **Shows**: Your current driver status
  - ✅ "Available" = Ready for requests
  - 🚑 "On Duty" = Currently assigned
- **Assignment Status**:
  - "Patient assigned" = You have active call
  - "Waiting for request" = No current assignment

### Distance Card (When Assignment Active)
- **Shows**: How far you are from the patient
- **Unit**: Kilometers with decimal precision
- **Example**: "2.50 km means 2 kilometers and 500 meters
- **Updates**: Every 5 seconds as you drive

### ETA Card (When Assignment Active)
- **Shows**: Estimated time to reach patient
- **Speed**: Calculated at 40 km/h average speed
- **Format**: Minutes or "< 1 min" if very close
- **Example**: "8 min" means about 8 minutes to arrive

## 📱 How to Use

### 1. **Accessing the Route Section**
   - Click "Route" in the left navigation menu
   - Map loads with your current location
   - If no assignment, map shows only your location

### 2. **When You Get an Assignment**
   - You'll receive a patient request notification
   - Click "Route" to see the assigned patient location
   - Patient location appears as red marker
   - Green route line shows direct path
   - Distance and ETA cards appear below

### 3. **Tracking Your Route**
   - Your green marker updates continuously
   - Distance decreases as you approach patient
   - ETA recalculates every 5 seconds
   - Route line stays connected until you arrive

### 4. **When You Arrive**
   - Distance shows "0.XX km" very close
   - Update status: "Picked Up" in the dashboard
   - Patient added to ambulance
   - System tracks hospital destination

## 🔍 Smart Features

### Real-Time Location Tracking
- Uses your phone's GPS continuously
- Updates every 3-5 seconds
- Works with or without cellular/WiFi data
- Accurate within 5-10 meters in urban areas

### Automatic Distance Calculation
- Uses geographic formula for accuracy
- Direct "as-the-crow-flies" distance
- Actual driving distance may vary

### Dynamic ETA
- Based on direct distance ÷ 40 km/h average
- Helpful for giving patients time estimates
- More accurate in urban areas with regular traffic

### Fallback System
- If GPS signal lost, last known location shown
- Automatically reconnects when GPS available again
- System won't crash even without location

## ⚙️ Settings & Privacy

### Location Permission
- First use will ask: "Allow access to your location?"
- **Tap "Allow"** to enable real-time tracking
- Required for real-time location features
- Can be changed in Settings → Permissions → Location

### Data Usage
- Uses minimal data for location updates
- Works with GPS alone (no internet needed)
- Reduces data usage compared to real-time video

### Privacy
- Your location only shared with dispatch system
- Not stored longer than necessary
- Not sold or shared with third parties

## 🎯 Best Practices

### Do:
✅ Grant location permission when prompted
✅ Keep screen on while navigating
✅ Monitor distance/ETA cards
✅ Update status when arriving at patient
✅ Verify patient location on red marker

### Don't:
❌ Don't drive while staring at map
❌ Don't dismiss location permission prompts
❌ Don't rely only on distance/ETA (use actual navigation app too)
❌ Don't zoom map too much (affects accuracy)

## 🆘 Troubleshooting

### Problem: "Fetching..." stays on Current Location
**Solution**:
1. Check GPS is enabled on your phone
2. Make sure location permission is granted
3. Stand outside for clearer GPS signal
4. Refresh page (F5)

### Problem: Green marker not moving
**Solution**:
1. Verify GPS signal strength (bars indicator)
2. Move to open area away from buildings
3. Wait 10-15 seconds for GPS to stabilize
4. Try turning GPS off/on

### Problem: Map not loading
**Solution**:
1. Check internet connection
2. Clear browser cache (Ctrl+Shift+Delete)
3. Refresh page (Ctrl+R)
4. Try different browser

### Problem: Patient marker not showing
**Solution**:
1. Verify you have an active assignment
2. Check assignment status in main dashboard
3. Refresh page
4. Contact dispatch if issue persists

### Problem: Distance/ETA not updating
**Solution**:
1. Wait 5 seconds (updates every 5 seconds)
2. Verify geolocation is working
3. Check map is fully loaded
4. Refresh page

## 📞 Reporting Issues

If you experience issues with the Route Section:

1. **Screenshot Error**: Take a screenshot of the problem
2. **Note Time**: When did it happen?
3. **Check Context**: 
   - Do you have an active assignment?
   - Is GPS enabled?
   - Is internet working?
4. **Contact Dispatch**: Report with details
5. **Provide Info**: 
   - Time of incident
   - Screenshot
   - Device type (iPhone/Android)
   - Browser type
   - What were you doing?

## 🚀 Tips for Better Navigation

### For Accuracy
- Keep phone in sunny area when stopped
- Give GPS 10-15 seconds to acquire signal
- Move away from tall buildings for better signal
- Don't cover GPS antenna on your phone

### For Efficiency
- Use the ETA to inform patient
- Start moving toward patient immediately
- Look at distance cards frequently
- Plan your route based on traffic

### For Safety
- Use dedicated navigation app too
- Don't rely on Route section alone
- Keep eyes on road, not map
- Ask colleague to monitor map if needed

## 📋 Quick Reference

| Element | What It Means | Updates |
|---------|---------------|---------|
| Green Pulsing Marker | Your location | Every 3-5 sec |
| Red Marker | Patient location | When assigned |
| Green Dashed Line | Route to patient | Every 5 sec |
| Distance Card | Kilometers to patient | Every 5 sec |
| ETA Card | Minutes to arrive | Every 5 sec |
| Current Location | Your GPS coordinates | Real-time |
| Status Card | Available/On Duty | On change |

## ❓ FAQ

**Q: Why is distance not exact to traffic?**
A: Route shows direct distance. Use Google Maps for actual route with traffic.

**Q: How often does location update?**
A: Every 3-5 seconds when driving. Slower when stationary.

**Q: Does it work without internet?**
A: GPS tracking works without internet. Map needs internet to load tiles.

**Q: Why is ETA sometimes wrong?**
A: ETA assumes 40 km/h average. Actual speed varies with traffic.

**Q: Can I zoom map to see more detail?**
A: Yes! Use scroll wheel or pinch on touchscreen.

**Q: What if GPS signal is weak?**
A: System uses last known location. Move to clear area.

**Q: How accurate is the location?** A: Within 5-10 meters in most conditions. Can be 20-40m in dense areas.

---

**Version**: 1.0 - Initial Release
**Last Updated**: 2024

For additional support, contact your dispatch center.
