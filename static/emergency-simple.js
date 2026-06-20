/**
 * Emergency Page Module - Using Google Maps JavaScript API
 * Displays patient location, nearby hospitals, and ambulance routes.
 *
 * Google Maps API usage:
 * - google.maps.Map              : map container initialization
 * - google.maps.Marker           : ambulance / hospital / user location pins
 * - google.maps.SymbolPath       : built-in vector icon shapes (CIRCLE, BACKWARD_CLOSED_ARROW)
 * - google.maps.InfoWindow       : popup info on marker click
 * - google.maps.DirectionsService: route + ETA calculation from Google Maps backend
 * - google.maps.DirectionsRenderer: route polyline rendered on the map
 * - google.maps.LatLngBounds     : auto-fit map viewport to show all markers
 *
 * API Key: AIzaSyAiGXGwc8i_JAc4tXEwL7raq0nh3Gli9G0
 */

const EmergencyPageModule = (() => {
    let map = null;
    let userMarker = null;
    let hospitalMarkers = [];
    let userLocation = { lat: 25.2048, lng: 55.2708 };
    let directionsRenderer = null;  // google.maps.DirectionsRenderer instance

    const hospitals = [
        { id: 1, name: 'City General Hospital', lat: 25.2048, lng: 55.2708, address: '123 Sheikh Zayed Rd, Dubai', phone: '+971-4-6393000' },
        { id: 2, name: 'Dubai Healthcare City Hospital', lat: 25.1228, lng: 55.1945, address: 'Dubai Healthcare City, Dubai', phone: '+971-4-3777777' },
        { id: 3, name: 'Al Wasl Hospital', lat: 25.1987, lng: 55.2703, address: 'Al Wasl Rd, Dubai', phone: '+971-4-2193000' },
        { id: 4, name: 'Emirates Hospital Clinics', lat: 25.1453, lng: 55.2121, address: 'Oud Metha, Dubai', phone: '+971-4-3081111' },
        { id: 5, name: 'Medcare Hospital', lat: 25.0975, lng: 55.1761, address: 'Umm Hurair Area, Dubai', phone: '+971-4-3200555' },
        { id: 6, name: 'Welcare Hospital', lat: 25.2341, lng: 55.2856, address: 'Al Manara Area, Dubai', phone: '+971-4-2279999' }
    ];

    /**
     * Calculate distance using Haversine formula
     */
    const calculateDistance = (lat1, lng1, lat2, lng2) => {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    };

    /**
     * Get nearby hospitals
     */
    const getNearbyHospitals = (lat, lng) => {
        return hospitals
            .map(h => ({ ...h, distance: calculateDistance(lat, lng, h.lat, h.lng) }))
            .filter(h => h.distance <= 10)
            .sort((a, b) => a.distance - b.distance);
    };

    /**
     * Initialize Google Map
     * google.maps.Map: creates and renders a map inside the specified DOM element
     * google.maps.Marker + SymbolPath.CIRCLE: blue pin for user/patient location
     * google.maps.LatLngBounds: auto-fits the viewport to show all markers
     */
    const initMap = () => {
        try {
            // Verify Google Maps API is loaded
            if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
                console.error('[EMERGENCY] Google Maps API not loaded');
                return false;
            }

            const mapEl = document.getElementById('emergencyMap');
            if (!mapEl) {
                console.error('[EMERGENCY] Map element not found');
                return false;
            }

            // Create Google Maps instance centered on user location
            map = new google.maps.Map(mapEl, {
                center: { lat: userLocation.lat, lng: userLocation.lng },
                zoom: 14,
                mapTypeId: 'roadmap',
                streetViewControl: false
            });

            // User location marker — google.maps.SymbolPath.CIRCLE (blue pulse)
            userMarker = new google.maps.Marker({
                position: { lat: userLocation.lat, lng: userLocation.lng },
                map: map,
                title: 'Patient Location',
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#00d4ff',
                    fillOpacity: 0.8,
                    strokeColor: '#00d4ff',
                    strokeWeight: 3
                }
            });
            var userInfoWin = new google.maps.InfoWindow({
                content: `<b>Patient Location</b><br>Lat: ${userLocation.lat.toFixed(6)}°<br>Lng: ${userLocation.lng.toFixed(6)}°`
            });
            userMarker.addListener('click', () => userInfoWin.open(map, userMarker));
            userInfoWin.open(map, userMarker);

            // Add hospital markers (arrow symbols)
            const nearby = getNearbyHospitals(userLocation.lat, userLocation.lng);
            addHospitalMarkers(nearby);

            // Fit viewport: google.maps.LatLngBounds extends to include all coordinates
            const bounds = new google.maps.LatLngBounds();
            bounds.extend({ lat: userLocation.lat, lng: userLocation.lng });
            nearby.forEach(h => bounds.extend({ lat: h.lat, lng: h.lng }));
            map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });

            // Hide loading spinner
            const spinner = document.getElementById('mapLoadingSpinner');
            if (spinner) spinner.style.display = 'none';

            const locEl = document.getElementById('userLocation');
            if (locEl) locEl.textContent = `${userLocation.lat.toFixed(4)}°N, ${userLocation.lng.toFixed(4)}°E`;
            const countEl = document.getElementById('nearbyCount');
            if (countEl) countEl.textContent = `${nearby.length} hospitals nearby`;

            renderHospitals(nearby);

            return true;
        } catch (error) {
            console.error('[EMERGENCY] Map init error:', error);
            return false;
        }
    };

    /**
     * Add hospital markers to the map
     * google.maps.Marker with SymbolPath.BACKWARD_CLOSED_ARROW: red hospital pins
     * google.maps.InfoWindow: popup showing hospital name and distance on click
     */
    const addHospitalMarkers = (hospitalsArr) => {
        // Remove previous hospital markers from the map
        hospitalMarkers.forEach(m => m.marker.setMap(null));
        hospitalMarkers = [];

        hospitalsArr.forEach((hospital) => {
            const marker = new google.maps.Marker({
                position: { lat: hospital.lat, lng: hospital.lng },
                map: map,
                title: hospital.name,
                icon: {
                    path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                    scale: 6,
                    fillColor: '#ff6b6b',
                    fillOpacity: 0.8,
                    strokeColor: '#ff0000',
                    strokeWeight: 2,
                    rotation: 180
                }
            });
            var infoWin = new google.maps.InfoWindow({
                content: `<strong>${hospital.name}</strong><br>${hospital.address}<br>Distance: ${hospital.distance.toFixed(1)} km`
            });
            marker.addListener('click', () => infoWin.open(map, marker));
            hospitalMarkers.push({ marker, id: hospital.id });
        });
    };

    /**
     * Show driving route from user to a hospital using Google Maps Directions API
     * DirectionsService: sends route request to Google Maps backend
     * DirectionsRenderer: draws the returned route polyline on the map
     * Logs real ETA from the Directions API response (includes live traffic)
     */
    const showRouteToHospital = (destLat, destLng) => {
        const directionsService = new google.maps.DirectionsService();

        // Remove previous route renderer before drawing a new one
        if (directionsRenderer) directionsRenderer.setMap(null);

        // DirectionsRenderer draws the route polyline returned by DirectionsService
        directionsRenderer = new google.maps.DirectionsRenderer({
            map: map,
            suppressMarkers: true,  // Keep our custom markers visible
            polylineOptions: {
                strokeColor: '#00d4ff',
                strokeOpacity: 0.7,
                strokeWeight: 4
            }
        });

        // DirectionsService.route(): request driving directions origin → destination
        directionsService.route(
            {
                origin: { lat: userLocation.lat, lng: userLocation.lng },
                destination: { lat: destLat, lng: destLng },
                travelMode: google.maps.TravelMode.DRIVING
            },
            (result, status) => {
                if (status === google.maps.DirectionsStatus.OK) {
                    directionsRenderer.setDirections(result);
                    // Extract ETA and distance from the first route leg
                    const leg = result.routes[0].legs[0];
                    console.log('[EMERGENCY] Route to hospital:', leg.distance.text, '— ETA:', leg.duration.text);
                } else {
                    console.warn('[EMERGENCY] Directions request failed:', status);
                }
            }
        );
    };

    /**
     * Update map when user location changes
     * google.maps.Marker.setPosition(): moves the marker to new coordinates
     * google.maps.LatLngBounds: re-fits the viewport to the updated location set
     */
    const updateMapLocation = (lat, lng) => {
        if (!map) return;

        // Move user marker to new position
        if (userMarker) userMarker.setPosition({ lat, lng });

        const locEl = document.getElementById('userLocation');
        if (locEl) locEl.textContent = `${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E`;

        // Refresh hospital markers for updated location
        const nearby = getNearbyHospitals(lat, lng);
        addHospitalMarkers(nearby);

        // Fit bounds to updated location set
        const bounds = new google.maps.LatLngBounds();
        bounds.extend({ lat, lng });
        nearby.forEach(h => bounds.extend({ lat: h.lat, lng: h.lng }));
        map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });

        const countEl = document.getElementById('nearbyCount');
        if (countEl) countEl.textContent = `${nearby.length} hospitals nearby`;
        renderHospitals(nearby);
    };

    /**
     * Render hospital cards
     */
    const renderHospitals = (hospitals) => {
        const list = document.getElementById('hospitalList');
        if (!list) return;

        let html = '';
        hospitals.forEach((h, idx) => {
            html += `
                <div class="hospital-card" data-hospital-id="${h.id}">
                    <div class="hospital-rank">${idx + 1}</div>
                    <div class="hospital-info-section">
                        <div class="hospital-name">${h.name}</div>
                        <div class="hospital-address"><i class="fas fa-map-marker-alt"></i> ${h.address}</div>
                    </div>
                    <div class="hospital-stats">
                        <div class="stat-item">
                            <div class="stat-label">Distance</div>
                            <div class="stat-value">${h.distance.toFixed(1)} km</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">ETA</div>
                            <div class="stat-value">~${Math.round(h.distance * 2)} min</div>
                        </div>
                    </div>
                    <div class="hospital-actions">
                        <button class="btn-directions" onclick="EmergencyPageModule.getDirections(${h.lat}, ${h.lng}, '${h.name.replace(/'/g, "\\'")}')">
                            <i class="fas fa-directions"></i> Directions
                        </button>
                        <button class="btn-select" onclick="EmergencyPageModule.selectHospital(${h.id}, '${h.name.replace(/'/g, "\\'")}')">
                            <i class="fas fa-check"></i> Select
                        </button>
                    </div>
                </div>
            `;
        });

        list.innerHTML = html;
    };

    /**
     * Get current location with timeout fallback
     */
    const getLocation = () => {
        if (!navigator.geolocation) {
            console.warn('[EMERGENCY] Geolocation not supported');
            return;
        }

        let gotPosition = false;
        const timeout = setTimeout(() => {
            if (!gotPosition) {
                console.warn('[EMERGENCY] Location request timeout - using fallback');
            }
        }, 5000);

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                gotPosition = true;
                clearTimeout(timeout);
                userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                console.log('[EMERGENCY] Got location:', userLocation);
                updateMapLocation(userLocation.lat, userLocation.lng);
            },
            (error) => {
                gotPosition = true;
                clearTimeout(timeout);
                console.warn('[EMERGENCY] Geolocation error:', error);
            },
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
        );

        // Watch location for updates
        navigator.geolocation.watchPosition(
            (pos) => {
                userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                updateMapLocation(userLocation.lat, userLocation.lng);
            },
            (error) => console.warn('[EMERGENCY] Watch error:', error),
            { enableHighAccuracy: false, timeout: 5000, maximumAge: 0 }
        );
    };

    // Public API
    return {
        init: () => {
            console.log('[EMERGENCY] Initializing emergency page...');
            if (initMap()) {
                console.log('[EMERGENCY] Map initialized successfully');
                // Try to get real location in background
                setTimeout(getLocation, 500);
            } else {
                console.error('[EMERGENCY] Failed to initialize map');
            }
        },
        getDirections: (lat, lng, name) => {
            // Show route on map via Directions API, then open Google Maps for turn-by-turn
            showRouteToHospital(lat, lng);
            window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, '_blank');
        },
        selectHospital: (id, name) => {
            document.querySelectorAll('.hospital-card').forEach(c => c.classList.remove('selected'));
            document.querySelector(`[data-hospital-id="${id}"]`)?.classList.add('selected');
            console.log('[EMERGENCY] Selected:', name);
            // Send to backend
            fetch('/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hospital_id: id, hospital_name: name, lat: userLocation.lat, lng: userLocation.lng })
            }).then(r => r.json()).then(data => {
                setTimeout(() => window.location.href = '/track?id=' + data.emergency_id, 1000);
            });
        }
    };
})();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    EmergencyPageModule.init();
    document.querySelector('.back-btn')?.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = '/';
    });
});
