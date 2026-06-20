/**
 * Emergency Page Module - Using Google Maps JavaScript API
 * Handles emergency response page functionality including:
 * - User geolocation detection
 * - Nearby hospital discovery
 * - Map initialization with Google Maps (google.maps.Map)
 * - Routes and ETA via Directions API (google.maps.DirectionsService)
 * - Hospital card rendering
 *
 * Google Maps API Key: AIzaSyAiGXGwc8i_JAc4tXEwL7raq0nh3Gli9G0
 * API Reference: https://developers.google.com/maps/documentation/javascript
 */

console.log('[EMERGENCY-PAGE] Module loading...');

const EmergencyPageModule = (() => {
    console.log('[EMERGENCY-PAGE] IIFE executing...');
    
    // ==================== PRIVATE STATE ====================
    let map = null;
    let userMarker = null;
    let userInfoWindow = null;       // google.maps.InfoWindow for user marker
    let hospitalMarkers = [];        // Array of { marker, infoWindow, hospitalId }
    let directionsRenderer = null;   // google.maps.DirectionsRenderer instance
    let userLocation = null;
    let selectedHospital = null;

    let hospitals = [
        {
            id: 1,
            name: 'City General Hospital',
            lat: 25.2048,
            lng: 55.2708,
            address: '123 Sheikh Zayed Rd, Dubai',
            phone: '+971-4-6393000'
        },
        {
            id: 2,
            name: 'Dubai Healthcare City Hospital',
            lat: 25.1228,
            lng: 55.1945,
            address: 'Dubai Healthcare City, Dubai',
            phone: '+971-4-3777777'
        },
        {
            id: 3,
            name: 'Al Wasl Hospital',
            lat: 25.1987,
            lng: 55.2703,
            address: 'Al Wasl Rd, Dubai',
            phone: '+971-4-2193000'
        },
        {
            id: 4,
            name: 'Emirates Hospital Clinics',
            lat: 25.1453,
            lng: 55.2121,
            address: 'Oud Metha, Dubai',
            phone: '+971-4-3081111'
        },
        {
            id: 5,
            name: 'Medcare Hospital',
            lat: 25.0975,
            lng: 55.1761,
            address: 'Umm Hurair Area, Dubai',
            phone: '+971-4-3200555'
        },
        {
            id: 6,
            name: 'Welcare Hospital',
            lat: 25.2341,
            lng: 55.2856,
            address: 'Al Manara Area, Dubai',
            phone: '+971-4-2279999'
        }
    ];

    // ==================== PRIVATE FUNCTIONS ====================

    /**
     * Get user's current location using browser geolocation
     */
    const getUserLocation = (timeoutMs = 700) => {
        return new Promise((resolve) => {
            console.log('[EMERGENCY-PAGE] Requesting user geolocation...');
            
            let timeoutId = setTimeout(() => {
                console.warn('[EMERGENCY-PAGE] Geolocation timeout - using fallback');
                resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
            }, timeoutMs);

            // Try browser geolocation first
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        clearTimeout(timeoutId);
                        const coords = {
                            lat: position.coords.latitude,
                            lng: position.coords.longitude,
                            accuracy: Math.round(position.coords.accuracy),
                            isDefault: false
                        };
                        console.log('[EMERGENCY-PAGE] ✓ Geolocation obtained:', coords);
                        resolve(coords);
                    },
                    (error) => {
                        clearTimeout(timeoutId);
                        console.warn('[EMERGENCY-PAGE] Geolocation error:', error.message);
                        resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
                    },
                    { enableHighAccuracy: false, timeout: 5000, maximumAge: 0 }
                );
            } else {
                clearTimeout(timeoutId);
                console.warn('[EMERGENCY-PAGE] Geolocation not supported');
                resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
            }
        });
    };

    /**
     * Calculate distance between two coordinates using Haversine formula
     */
    const calculateDistance = (lat1, lng1, lat2, lng2) => {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = 
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    };

    /**
     * Get nearby hospitals within 10 km radius
     */
    const getNearbyHospitals = (lat, lng) => {
        const nearby = hospitals
            .map(hospital => ({
                ...hospital,
                distance: calculateDistance(lat, lng, hospital.lat, hospital.lng)
            }))
            .filter(hospital => hospital.distance <= 10)
            .sort((a, b) => a.distance - b.distance);

        console.log('[EMERGENCY-PAGE] Nearby hospitals found:', nearby.length);
        return nearby;
    };

    /**
     * Initialize Leaflet map with OpenStreetMap
     */
    const initializeMap = async (lat, lng) => {
        const mapElement = document.getElementById('emergencyMap');
        
        if (!mapElement) {
            console.error('[EMERGENCY-PAGE] ✗ Map element #emergencyMap not found!');
            throw new Error('Map container element not found');
        }

        // Ensure container has dimensions
        const rect = mapElement.getBoundingClientRect();
        console.log('[EMERGENCY-PAGE] Map container dimensions:', rect.width, 'x', rect.height);

        if (rect.width === 0 || rect.height === 0) {
            console.warn('[EMERGENCY-PAGE] Map container has zero dimensions, waiting...');
            // Give the layout time to render
            await new Promise(resolve => setTimeout(resolve, 100));
            return initializeMap(lat, lng);
        }

        console.log('[EMERGENCY-PAGE] Creating Google Map at:', lat, lng);

        try {
            // Create Google Maps instance
            // google.maps.Map: renders a map inside the given DOM element
            map = new google.maps.Map(mapElement, {
                center: { lat, lng },
                zoom: 15,
                mapTypeId: 'roadmap',
                zoomControl: true,
                streetViewControl: false,
                mapTypeControl: false
            });

            console.log('[EMERGENCY-PAGE] ✓ Google Map created successfully');

            // Add user location marker
            addUserMarker(lat, lng);

        } catch (mapError) {
            console.error('[EMERGENCY-PAGE] ✗ Error creating map:', mapError.message);
            throw new Error('Failed to initialize map: ' + mapError.message);
        }
    };

    /**
     * Add user location marker to map
     * google.maps.Marker + SymbolPath.CIRCLE: blue dot for user/patient location
     * google.maps.InfoWindow: popup shown on marker click
     */
    const addUserMarker = (latitude, longitude) => {
        try {
            // Remove existing user marker if present
            if (userMarker) userMarker.setMap(null);
            if (userInfoWindow) userInfoWindow.close();

            // Create Google Maps Marker with CIRCLE symbol for user location
            userMarker = new google.maps.Marker({
                position: { lat: latitude, lng: longitude },
                map: map,
                title: 'Your Location',
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#00d4ff',
                    fillOpacity: 1,
                    strokeColor: '#0099cc',
                    strokeWeight: 2
                }
            });

            // InfoWindow shown when user marker is clicked
            userInfoWindow = new google.maps.InfoWindow({
                content: `<div style="font-size:12px">
                    <strong>Your Location</strong><br/>
                    Lat: ${latitude.toFixed(6)}°<br/>
                    Lng: ${longitude.toFixed(6)}°
                </div>`
            });

            userMarker.addListener('click', () => {
                userInfoWindow.open(map, userMarker);
            });

            userInfoWindow.open(map, userMarker);
            console.log('[EMERGENCY-PAGE] ✓ User marker added');

        } catch (error) {
            console.error('[EMERGENCY-PAGE] Error adding marker:', error);
        }
    };

    /**
     * Add hospital markers to map
     * google.maps.Marker + SymbolPath.BACKWARD_CLOSED_ARROW: red arrow pins for hospitals
     * google.maps.InfoWindow: popup showing hospital name, address, distance
     */
    const addHospitalMarkers = (hospitals) => {
        try {
            // Remove existing hospital markers from the map
            hospitalMarkers.forEach(m => m.marker.setMap(null));
            hospitalMarkers = [];

            hospitals.forEach((hospital) => {
                // Create hospital marker using BACKWARD_CLOSED_ARROW symbol
                const marker = new google.maps.Marker({
                    position: { lat: hospital.lat, lng: hospital.lng },
                    map: map,
                    title: hospital.name,
                    icon: {
                        path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                        scale: 6,
                        fillColor: '#ff6b6b',
                        fillOpacity: 1,
                        strokeColor: '#ff3333',
                        strokeWeight: 2,
                        rotation: 180
                    }
                });

                // InfoWindow shown when hospital marker is clicked
                const infoWindow = new google.maps.InfoWindow({
                    content: `<div style="font-size:12px">
                        <strong>${hospital.name}</strong><br/>
                        ${hospital.address}<br/>
                        Distance: ${hospital.distance.toFixed(1)} km
                    </div>`
                });

                marker.addListener('click', () => {
                    infoWindow.open(map, marker);
                });

                hospitalMarkers.push({ marker, infoWindow, hospitalId: hospital.id });
            });

            console.log('[EMERGENCY-PAGE] ✓ Hospital markers added:', hospitalMarkers.length);

        } catch (error) {
            console.error('[EMERGENCY-PAGE] Error adding hospital markers:', error);
        }
    };

    /**
     * Update map center to new location
     * google.maps.Map.setCenter(): moves the map to given coordinates
     */
    const updateMap = (lat, lng) => {
        if (map) {
            map.setCenter({ lat, lng });
            map.setZoom(15);
            // Re-draw user marker at new position
            addUserMarker(lat, lng);
            console.log('[EMERGENCY-PAGE] Map updated to:', lat, lng);
        }
    };

    /**
     * Get route and ETA from user to a hospital using Google Maps Directions API
     * DirectionsService: sends a routing request to Google Maps servers
     * Returns { result, distance, duration } from the first route leg
     */
    const getRouteAndETA = (originLat, originLng, destLat, destLng) => {
        return new Promise((resolve, reject) => {
            const directionsService = new google.maps.DirectionsService();
            directionsService.route(
                {
                    origin: { lat: originLat, lng: originLng },
                    destination: { lat: destLat, lng: destLng },
                    travelMode: google.maps.TravelMode.DRIVING,
                    drivingOptions: {
                        departureTime: new Date(),
                        trafficModel: google.maps.TrafficModel.BEST_GUESS
                    }
                },
                (result, status) => {
                    if (status === google.maps.DirectionsStatus.OK) {
                        const leg = result.routes[0].legs[0];
                        resolve({
                            result,
                            distance: leg.distance.text,
                            // Use traffic-aware duration when available
                            duration: leg.duration_in_traffic
                                ? leg.duration_in_traffic.text
                                : leg.duration.text
                        });
                    } else {
                        reject(new Error('Directions request failed: ' + status));
                    }
                }
            );
        });
    };

    /**
     * Render route polyline on the map using DirectionsRenderer
     * DirectionsRenderer: draws the route returned by DirectionsService onto the map
     * suppressMarkers: true keeps our custom marker icons visible
     */
    const displayRoute = (directionsResult) => {
        if (directionsRenderer) directionsRenderer.setMap(null);

        directionsRenderer = new google.maps.DirectionsRenderer({
            map: map,
            suppressMarkers: true,
            polylineOptions: {
                strokeColor: '#00d4ff',
                strokeOpacity: 0.8,
                strokeWeight: 4
            }
        });
        directionsRenderer.setDirections(directionsResult);
    };

    /**
     * Calculate real ETA for a hospital via Directions API and update the hospital card
     * Calls getRouteAndETA, displays the route on map, and patches the ETA in the DOM
     */
    const calculateAndDisplayETA = async (hospital) => {
        if (!userLocation) return;
        try {
            const { result, distance, duration } = await getRouteAndETA(
                userLocation.lat, userLocation.lng,
                hospital.lat, hospital.lng
            );
            // Show the driving route on the map
            displayRoute(result);
            // Patch ETA and distance values in the rendered hospital card
            const card = document.querySelector(`.hospital-card[data-hospital-id="${hospital.id}"]`);
            if (card) {
                const etaEl = card.querySelector('.stat-item:nth-child(2) .stat-value');
                if (etaEl) etaEl.textContent = duration;
                const distEl = card.querySelector('.stat-item:nth-child(1) .stat-value');
                if (distEl) distEl.textContent = distance;
            }
            console.log('[EMERGENCY-PAGE] ✓ ETA for', hospital.name, ':', duration, '(', distance, ')');
        } catch (err) {
            console.warn('[EMERGENCY-PAGE] ETA calculation failed for', hospital.name, ':', err.message);
        }
    };

    /**
     * Fit the map viewport to show the user and all hospital markers
     * google.maps.LatLngBounds: extends bounds to include each coordinate, then fits the map
     */
    const fitMapBounds = (lat, lng, hospitalsArr) => {
        if (!map) return;
        const bounds = new google.maps.LatLngBounds();
        bounds.extend({ lat, lng });
        hospitalsArr.forEach(h => bounds.extend({ lat: h.lat, lng: h.lng }));
        map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
    };

    /**
     * Render hospital cards dynamically
     */
    const renderHospitalCards = (hospitals, distanceMatrixData) => {
        const hospitalList = document.getElementById('hospitalList');
        if (!hospitalList) {
            console.warn('[EMERGENCY-PAGE] Hospital list element not found');
            return;
        }

        let html = '';
        hospitals.forEach((hospital, index) => {
            const distance = hospital.distance.toFixed(1);
            const etaMinutes = Math.round((hospital.distance / 40) * 60);
            const eta = '~' + etaMinutes + ' min';

            html += `
                <div class="hospital-card" data-hospital-id="${hospital.id}">
                    <div class="hospital-rank">${index + 1}</div>
                    
                    <div class="hospital-info-section">
                        <div class="hospital-name">${hospital.name}</div>
                        <div class="hospital-address">
                            <i class="fas fa-map-marker-alt"></i>
                            ${hospital.address}
                        </div>
                    </div>

                    <div class="hospital-stats">
                        <div class="stat-item">
                            <div class="stat-label">Distance</div>
                            <div class="stat-value">${distance} km</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">ETA</div>
                            <div class="stat-value">${eta}</div>
                        </div>
                    </div>

                    <div class="hospital-actions">
                        <button class="btn-directions" onclick="EmergencyPageModule.getDirections(${hospital.lat}, ${hospital.lng}, '${hospital.name.replace(/'/g, "\\'")}')">
                            <i class="fas fa-directions"></i> Get Directions
                        </button>
                        <button class="btn-select" onclick="EmergencyPageModule.selectHospital(${hospital.id}, '${hospital.name.replace(/'/g, "\\'")}')">
                            <i class="fas fa-check"></i> Select
                        </button>
                    </div>
                </div>
            `;
        });

        hospitalList.innerHTML = html;
        // Update ETA via Google Maps Directions API for the nearest hospital
        if (hospitals.length > 0) {
            calculateAndDisplayETA(hospitals[0]);
        }
        console.log('[EMERGENCY-PAGE] Hospital cards rendered:', hospitals.length);
    };

    /**
     * Update location info display
     */
    const updateLocationInfo = (lat, lng, count) => {
        const userLocationEl = document.getElementById('userLocation');
        const nearbyCountEl = document.getElementById('nearbyCount');

        const formattedLat = lat.toFixed(4);
        const formattedLng = lng.toFixed(4);

        if (userLocationEl) {
            userLocationEl.innerHTML = `<strong>${formattedLat}°N, ${formattedLng}°E</strong>`;
        }

        if (nearbyCountEl) {
            nearbyCountEl.textContent = `${count} hospitals nearby`;
        }
    };

    /**
     * Handle "Get Directions" button
     */
    const handleGetDirections = (lat, lng, hospitalName) => {
        const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        window.open(mapsUrl, '_blank');
        console.log('[EMERGENCY-PAGE] Directions opened for:', hospitalName);
    };

    /**
     * Handle hospital selection
     */
    const handleSelectHospital = (hospitalId, hospitalName) => {
        document.querySelectorAll('.hospital-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`.hospital-card[data-hospital-id="${hospitalId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        selectedHospital = { id: hospitalId, name: hospitalName };
        console.log('[EMERGENCY-PAGE] Hospital selected:', hospitalName);

        sendDispatchRequest(hospitalId, hospitalName);
    };

    /**
     * Send dispatch request to backend
     */
    const sendDispatchRequest = async (hospitalId, hospitalName) => {
        try {
            const response = await fetch('/dispatch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    hospital_id: hospitalId,
                    hospital_name: hospitalName,
                    lat: userLocation.lat,
                    lng: userLocation.lng
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log('[EMERGENCY-PAGE] Dispatch request sent:', data);
                
                setTimeout(() => {
                    window.location.href = '/track?id=' + data.emergency_id;
                }, 1500);
            } else {
                console.error('[EMERGENCY-PAGE] Dispatch request failed');
                alert('Failed to dispatch ambulance. Please try again.');
            }
        } catch (error) {
            console.error('[EMERGENCY-PAGE] Dispatch error:', error);
            alert('Error dispatching ambulance: ' + error.message);
        }
    };

    // ==================== PUBLIC API ====================

    return {
        /**
         * Initialize the emergency page
         */
        init: async function() {
            console.log('[EMERGENCY-PAGE] ════════════════════════════════════');
            console.log('[EMERGENCY-PAGE] Starting initialization...');
            console.log('[EMERGENCY-PAGE] ════════════════════════════════════');

            try {
                // Check if Google Maps API is available
                if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
                    throw new Error('Google Maps API not loaded. Please refresh the page.');
                }
                console.log('[EMERGENCY-PAGE] ✓ Google Maps API available');

                // FAST: Initialize map immediately with fallback location
                const fallbackLoc = { lat: 25.2048, lng: 55.2708 };
                console.log('[EMERGENCY-PAGE] Step 1: Initializing map with fallback location...');
                await initializeMap(fallbackLoc.lat, fallbackLoc.lng);
                updateLocationInfo(fallbackLoc.lat, fallbackLoc.lng, 6);
                console.log('[EMERGENCY-PAGE] ✓ Map initialized');

                // Hide loading spinner
                const loadingSpinner = document.getElementById('mapLoadingSpinner');
                if (loadingSpinner) {
                    loadingSpinner.style.display = 'none';
                    console.log('[EMERGENCY-PAGE] ✓ Loading spinner hidden');
                }

                // Get nearby hospitals
                console.log('[EMERGENCY-PAGE] Step 2: Finding nearby hospitals...');
                const nearbyHospitals = getNearbyHospitals(fallbackLoc.lat, fallbackLoc.lng);
                console.log('[EMERGENCY-PAGE] ✓ Found', nearbyHospitals.length, 'hospitals');

                // Add hospital markers and fit map viewport to show all locations
                console.log('[EMERGENCY-PAGE] Step 3: Adding hospital markers...');
                addHospitalMarkers(nearbyHospitals);
                fitMapBounds(fallbackLoc.lat, fallbackLoc.lng, nearbyHospitals);

                // Render hospital cards
                console.log('[EMERGENCY-PAGE] Step 4: Rendering hospital cards...');
                renderHospitalCards(nearbyHospitals, null);

                console.log('[EMERGENCY-PAGE] ════════════════════════════════════');
                console.log('[EMERGENCY-PAGE] ✓ INITIALIZATION COMPLETE (< 2 seconds)');
                console.log('[EMERGENCY-PAGE] ════════════════════════════════════');

                // Request real location in background
                userLocation = fallbackLoc;
                const locationPromise = getUserLocation(700);

                locationPromise.then(async (realLocation) => {
                    if (realLocation && !realLocation.isDefault) {
                        console.log('[EMERGENCY-PAGE] ✓ Real location obtained:', realLocation);
                        userLocation = realLocation;
                        updateMap(realLocation.lat, realLocation.lng);
                        updateLocationInfo(realLocation.lat, realLocation.lng, nearbyHospitals.length);

                        const updatedHospitals = getNearbyHospitals(realLocation.lat, realLocation.lng);
                        addHospitalMarkers(updatedHospitals);
                        fitMapBounds(realLocation.lat, realLocation.lng, updatedHospitals);
                        renderHospitalCards(updatedHospitals, null);
                        console.log('[EMERGENCY-PAGE] ✓ Map updated with real location');
                    }
                }).catch(error => {
                    console.warn('[EMERGENCY-PAGE] Background location error:', error.message);
                });

            } catch (error) {
                console.error('[EMERGENCY-PAGE] ✗ INITIALIZATION ERROR:', error);
                console.error('[EMERGENCY-PAGE] Error details:', error.message);
                
                const hospitalList = document.getElementById('hospitalList');
                if (hospitalList) {
                    hospitalList.innerHTML = `
                        <div style="padding: 20px; text-align: center; color: #ff6b6b;">
                            <i class="fas fa-exclamation-circle" style="font-size: 2rem; margin-bottom: 10px;"></i>
                            <p><strong>Error Loading Emergency Page</strong></p>
                            <p style="font-size: 0.9rem; margin-top: 10px;">${error.message}</p>
                            <button onclick="location.reload()" style="margin-top: 15px; padding: 8px 16px; background: #00d4ff; color: #000; border: none; border-radius: 5px; cursor: pointer;">
                                Retry
                            </button>
                        </div>
                    `;
                }
            }
        },

        /**
         * Get directions to a hospital
         */
        getDirections: function(lat, lng, hospitalName) {
            handleGetDirections(lat, lng, hospitalName);
        },

        /**
         * Select a hospital
         */
        selectHospital: function(hospitalId, hospitalName) {
            handleSelectHospital(hospitalId, hospitalName);
        }
    };
})();

console.log('[EMERGENCY-PAGE] Module loaded. EmergencyPageModule available:', typeof EmergencyPageModule !== 'undefined');
