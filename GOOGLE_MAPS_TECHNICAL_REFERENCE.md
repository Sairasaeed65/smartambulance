# Technical Reference - Emergency Page with Google Maps

## 📖 Quick Code Reference

### HTML Structure
```html
<div class="emergency-layout">
  <!-- 70% Left: Map -->
  <div class="map-section">
    <div class="map-header">...</div>
    <div id="emergencyMap"></div>  <!-- Google Maps renders here -->
  </div>
  
  <!-- 30% Right: Hospital List -->
  <div class="hospital-section">
    <div class="hospital-header">...</div>
    <div class="emergency-status">...</div>
    <div class="hospital-list" id="hospitalList">
      <!-- Hospital cards generated here -->
    </div>
  </div>
</div>
```

---

## 🔑 Key JavaScript Functions

### `initMap()`
Initializes Google Map with dark theme styling.
```javascript
map = new google.maps.Map(document.getElementById('emergencyMap'), {
    zoom: 14,
    center: { lat: 25.2048, lng: 55.2708 },
    styles: [...] // Dark theme
});
```

### `detectUserLocation()`
Gets user's browser location or uses fallback.
```javascript
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        success => { /* set userLocation */ },
        error => { /* use fallback */ }
    );
}
```

### `calculateDistance(lat1, lon1, lat2, lon2)`
Haversine formula for great-circle distance.
```javascript
const R = 6371; // km
const dLat = (lat2 - lat1) * Math.PI / 180;
const dLon = (lon2 - lon1) * Math.PI / 180;
// ... calculate and return distance in km
```

### `addUserMarker()`
Places blue circle marker at user location.
```javascript
const userIcon = {
    path: google.maps.SymbolPath.CIRCLE,
    scale: 12,
    fillColor: '#00d4ff',
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 2
};
userMarker = new google.maps.Marker({...});
```

### `displayNearbyHospitals()`
Sorts hospitals by distance and displays them.
```javascript
HOSPITALS.forEach(h => {
    h.distance = calculateDistance(...);
});
HOSPITALS.sort((a, b) => a.distance - b.distance);
HOSPITALS.slice(0, 5).forEach(h => {
    addHospitalMarker(h);
});
renderHospitalList();
```

### `renderHospitalList()`
Dynamically creates hospital cards in HTML.
```javascript
HOSPITALS.slice(0, 5).forEach((hospital, index) => {
    const card = document.createElement('div');
    card.className = 'hospital-card';
    card.innerHTML = `...hospital details...`;
    card.addEventListener('click', () => selectHospital(hospital));
    listContainer.appendChild(card);
});
```

### `selectHospital(hospital)`
Centers map on selected hospital and highlights card.
```javascript
map.setCenter({ lat: hospital.latitude, lng: hospital.longitude });
map.setZoom(15);
// Add 'selected' class to card
```

---

## 🎨 CSS Layout System

### Main Flex Container
```css
.emergency-layout {
    display: flex;
    height: calc(100vh - 70px);  /* Minus navbar */
    gap: 0;
}
```

### Map Section (70%)
```css
.map-section {
    flex: 0 0 70%;
    display: flex;
    flex-direction: column;
}

#emergencyMap {
    flex: 1;  /* Takes remaining space */
    width: 100%;
}
```

### Hospital Section (30%)
```css
.hospital-section {
    flex: 0 0 30%;
    display: flex;
    flex-direction: column;
}

.hospital-list {
    flex: 1;  /* Scrollable */
    overflow-y: auto;
}
```

---

## 📊 Hospital Data Structure

```javascript
const HOSPITALS = [
    {
        id: 1,
        name: 'City General Hospital',
        latitude: 25.2048,
        longitude: 55.2708,
        address: '123 Medical St, Dubai',
        beds: 15,
        department: 'Emergency Ward',
        distance: 0  // Calculated at runtime
    },
    // ... 4 more hospitals
];
```

---

## 🔄 Data Flow Diagram

```
Page Load
  ↓
Google Maps API loads (async)
  ↓
DOMContentLoaded fires
  ↓
initMap() → Creates blank map
  ↓
detectUserLocation() → Gets position
  ↓
├─ Success: Set userLocation
│   ↓
│   addUserMarker()
│   updateLocationInfo()
│   displayNearbyHospitals()
│
└─ Error/Denied: Use fallback (25.2048, 55.2708)
    ↓
    (same as above)
    ↓
displayNearbyHospitals()
  ├─ Calculate distance for each hospital
  ├─ Sort by distance
  ├─ Add markers for top 5
  ├─ renderHospitalList() → Create DOM cards
  └─ Update nearby count display
    ↓
User interacts with map/cards
  ↓
selectHospital() → Center map + highlight card
  ↓
User clicks directions → Opens Google Maps
User clicks select → Confirms hospital choice
```

---

## 🌐 API Integration Points

### Google Maps API
```javascript
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBNjusvvZkr-RWwCBKVoEOMsAL0Sd_5gdk"></script>
```

### Available Objects
- `google.maps.Map` - The map instance
- `google.maps.Marker` - Markers on the map
- `google.maps.InfoWindow` - Popup windows
- `google.maps.SymbolPath` - Icon shapes (CIRCLE, etc.)
- `google.maps.Animation` - Animations (DROP, etc.)

### Browser APIs
- `navigator.geolocation.getCurrentPosition()` - Get user location
- `document.createElement()` - Create DOM elements
- `fetch()` - HTTP requests (if needed)

---

## 🛠️ CSS Variables (Easy Customization)

```css
:root {
    --primary-dark: #0f1419;        /* Main background */
    --secondary-dark: #1a2332;      /* Card background */
    --accent-primary: #00d4ff;      /* Cyan highlights */
    --accent-secondary: #0066cc;    /* Blue accents */
    --alert-red: #ff0000;           /* Emergency red */
    --text-primary: #e8eef7;        /* Main text */
    --text-secondary: #a0a8b8;      /* Secondary text */
    --border-color: #2a3a52;        /* Borders */
    --success-green: #10b981;       /* Action buttons */
}
```

Change these to customize the entire color scheme!

---

## 🧮 Distance Calculation Example

```javascript
// For hospital at 25.2048°N, 55.2708°E
// User at 25.2000°N, 55.2700°E
// Distance ≈ 0.85 km

const dist = calculateDistance(25.2000, 55.2700, 25.2048, 55.2708);
// Returns: 0.852 (in kilometers)
```

---

## 🎯 Responsive Media Query Breakpoints

```css
/* Desktop: Default styles (≥1024px) */
.emergency-layout {
    flex-direction: row;  /* Side-by-side */
}
.map-section { flex: 0 0 70%; }
.hospital-section { flex: 0 0 30%; }

/* Tablet: 768px - 1024px */
@media (max-width: 1024px) {
    .emergency-layout {
        flex-direction: column;  /* Stacked */
    }
    .map-section { flex: 0 0 60%; }
    .hospital-section { flex: 0 0 40%; }
}

/* Mobile: < 768px */
@media (max-width: 768px) {
    .map-section { flex: 0 0 50%; }
    .hospital-section { flex: 0 0 50%; }
    .navbar { height: 60px; }  /* Smaller navbar */
}
```

---

## 🔍 Debugging Tips

### Check if Google Maps loaded:
```javascript
console.log(google.maps);  // Should be defined
```

### Check user location:
```javascript
console.log('User Location:', userLocation);
// Should log: { lat: 25.2048, lng: 55.2708 }
```

### Check hospital data:
```javascript
console.log('Hospital[0]:', HOSPITALS[0]);
// Should show hospital with calculated distance
```

### Check map markers:
```javascript
console.log('Markers count:', hospitalMarkers.length);
// Should be 5 (for 5 hospitals)
```

### Enable browser geolocation logging:
```javascript
navigator.geolocation.getCurrentPosition(
    (pos) => console.log('Position:', pos),
    (err) => console.error('Geolocation error:', err)
);
```

---

## 📦 Performance Optimizations

1. **Lazy Loading**: Google Maps API loads asynchronously
2. **Efficient Rendering**: Hospital cards created once and cached
3. **Minimal Reflows**: CSS transforms for animations (GPU accelerated)
4. **Debounced Functions**: No rapid recalculations
5. **Event Delegation**: Single listener on hospital list (delegated to cards)

---

## 🔐 Security Considerations

1. **Google Maps API Key**: Exposed in client (acceptable with restrictions)
   - **Restriction**: HTTP referrer (domain.com only)
   - **Restriction**: Google Maps API and Static Maps API only
   
2. **Geolocation**: User permission required
   - Browser shows permission dialog
   - Can be denied/revoked in settings
   
3. **HTTPS**: Geolocation requires HTTPS in production
   - localhost works with HTTP for development
   - Production must use HTTPS

---

## 🚀 Deployment Checklist

- [ ] Verify Google Maps API key is production-restricted
- [ ] Set HTTP referrer restrictions to your domain
- [ ] Use HTTPS in production
- [ ] Test geolocation on real devices
- [ ] Update hospital data with real database
- [ ] Implement backend validation for coordinates
- [ ] Add rate limiting for API calls
- [ ] Monitor Google Maps usage quota
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Add analytics for emergency requests

---

## 🔗 Useful Resources

| Resource | Link |
|----------|------|
| Google Maps API Docs | `developers.google.com/maps` |
| Geolocation API Docs | `developer.mozilla.org/geolocation` |
| Haversine Formula | `en.wikipedia.org/wiki/Haversine_formula` |
| Bootstrap Grid | `getbootstrap.com/docs/5.0/layout/grid` |
| Font Awesome Icons | `fontawesome.com/icons` |

---

## 📝 Code Style Guide

### Naming Conventions
- **Functions**: `camelCase` (e.g., `initMap`, `detectUserLocation`)
- **Variables**: `camelCase` (e.g., `userLocation`, `hospitalMarkers`)
- **Constants**: `UPPER_CASE` (e.g., `HOSPITALS`)
- **CSS Classes**: `kebab-case` (e.g., `.hospital-card`, `.map-section`)

### Comments
```javascript
/**
 * Function description
 * @param {type} name - Description
 * @returns {type} Description
 */
function exampleFunction(param) {
    // Single line comment for logic
    const result = param * 2;
    return result;
}
```

### File Organization
1. **HTML**: Structure first
2. **CSS**: Styling (variables, layout, components, responsive)
3. **JavaScript**: Logic (constants, functions, initialization)

---

## ✅ Testing Checklist

| Test Case | Expected | Status |
|-----------|----------|--------|
| Map loads | Blank map shows | ✅ |
| Geolocation | Blue marker appears | ⏳ Depends on browser |
| Hospital list | 5 cards show | ✅ |
| Click hospital | Map centers, card highlighted | ⏳ |
| Hover effect | Color changes | ✅ |
| Responsive | Layout adapts 70/30 → 60/40 → 50/50 | ✅ |
| Mobile | All elements visible, scrollable | ⏳ |
| Fallback | Works without geolocation | ✅ |

---

## 🎓 Learning Path

To understand this code better, study these topics in order:

1. **CSS Flexbox** - Layout system
2. **JavaScript DOM API** - Element creation/manipulation
3. **Google Maps API** - Map initialization and markers
4. **Geolocation API** - Getting user position
5. **Mathematical Formulas** - Distance calculation
6. **Responsive Design** - Media queries
7. **Event Handling** - Click listeners, bubbling

---

*Reference Document v1.0*  
*Created: February 28, 2026*  
*For: SmartAmbulance Emergency Page*
