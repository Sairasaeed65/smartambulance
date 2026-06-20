/**
 * Emergency Page Module
 * Handles emergency response page functionality including:
 * - User geolocation detection
 * - Nearby hospital discovery
 * - Distance Matrix calculations
 * - Map initialization and markers
 * - Hospital card rendering
 */

console.log('[EMERGENCY-PAGE] Module loading...');

const EmergencyPageModule = (() => {
    console.log('[EMERGENCY-PAGE] IIFE executing...');
    
    // ==================== PRIVATE STATE ====================
    let map = null;
    let userMarker = null;
    let hospitalMarkers = [];
    let userLocation = null;
    let selectedHospital = null;
    let mapsAPIReady = false;

    // Check if Google Maps API is available
    const checkGoogleMapsAPI = () => {
        if (typeof window.google === 'undefined' || typeof window.google.maps === 'undefined') {
            console.error('[EMERGENCY-PAGE] ✗ Google Maps API not loaded');
            return false;
        }
        console.log('[EMERGENCY-PAGE] ✓ Google Maps API detected');
        mapsAPIReady = true;
        return true;
    };

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
     * Get user's current location using Google Geolocation API (FAST - no GPS needed)
     */
    const getUserLocation = (timeoutMs = 700) => {
        return new Promise((resolve) => {
            const hasGoogleAPI = typeof google !== 'undefined' && typeof google.maps !== 'undefined';
            
            console.log('[EMERGENCY-PAGE] Requesting location from Google Geolocation API...');
            
            let timeoutId = setTimeout(() => {
                console.warn('[EMERGENCY-PAGE] Google Geolocation timeout - using fallback');
                resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
            }, timeoutMs);

            // Use Google's Geolocation API (works with WiFi, not just GPS)
            fetch('https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyBNjusvvZkr-RWwCBKVoEOMsAL0Sd_5gdk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.location) {
                    const coords = {
                        lat: data.location.lat,
                        lng: data.location.lng,
                        accuracy: data.accuracy || 5000,
                        isDefault: false
                    };
                    console.log('[EMERGENCY-PAGE] ✓ Google Geolocation obtained:', coords);
                    resolve(coords);
                } else {
                    throw new Error('No location in response');
                }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                console.warn('[EMERGENCY-PAGE] Google Geolocation error:', error.message);
                console.log('[EMERGENCY-PAGE] Using fallback location - will try native geolocation next');
                
                // Fallback to browser's native geolocation
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const coords = {
                                lat: position.coords.latitude,
                                lng: position.coords.longitude,
                                accuracy: Math.round(position.coords.accuracy),
                                isDefault: false
                            };
                            console.log('[EMERGENCY-PAGE] ✓ Browser geolocation obtained:', coords);
                            resolve(coords);
                        },
                        (error) => {
                            console.warn('[EMERGENCY-PAGE] Browser geolocation also failed:', error.message);
                            resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
                        },
                        { enableHighAccuracy: false, timeout: 5000, maximumAge: 0 }
                    );
                } else {
                    resolve({ lat: 25.2048, lng: 55.2708, accuracy: 5000, isDefault: true });
                }
            });
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
     * Get Distance Matrix data from Google Distance Matrix API
     */
    const getDistanceMatrixData = async (originLat, originLng, hospitals) => {
        try {
            if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
                console.warn('[EMERGENCY-PAGE] Google Maps API not available for Distance Matrix');
                return null;
            }

            const service = new google.maps.DistanceMatrixService();
            const origins = [new google.maps.LatLng(originLat, originLng)];
            const destinations = hospitals.map(h => new google.maps.LatLng(h.lat, h.lng));

            return new Promise((resolve, reject) => {
                service.getDistanceMatrix({
                    origins: origins,
                    destinations: destinations,
                    travelMode: 'DRIVING'
                }, (response, status) => {
                    if (status !== google.maps.DistanceMatrixStatus.OK) {
                        console.warn('[EMERGENCY-PAGE] Distance Matrix API error:', status);
                        console.warn('[EMERGENCY-PAGE] Response:', response);
                        resolve(null);
                        return;
                    }

                    const results = response.rows[0].elements;
                    const distances = results.map((element, index) => ({
                        hospitalId: hospitals[index].id,
                        distance: element.distance ? element.distance.text : 'N/A',
                        duration: element.duration ? element.duration.text : 'N/A',
                        durationValue: element.duration ? element.duration.value : 0
                    }));

                    console.log('[EMERGENCY-PAGE] Distance Matrix data received:', distances.length);
                    resolve(distances);
                });
            });
        } catch (error) {
            console.error('[EMERGENCY-PAGE] Distance Matrix error:', error.message);
            return null;
        }
    };

    /**
     * Update map center to a new location
     */
    const updateMap = (lat, lng) => {
        if (map) {
            map.setCenter({ lat, lng });
            if (userMarker) {
                userMarker.setPosition({ lat, lng });
            }
            console.log('[EMERGENCY-PAGE] Map center updated to:', lat, lng);
        }
    };

    /**
     * Initialize Google Map
     */
    const initializeMap = (lat, lng) => {
        const mapElement = document.getElementById('emergencyMap');
        console.log('[EMERGENCY-PAGE] Map element check:', {
            exists: !!mapElement,
            tagName: mapElement?.tagName,
            width: mapElement?.offsetWidth,
            height: mapElement?.offsetHeight,
            display: mapElement ? window.getComputedStyle(mapElement).display : 'N/A',
            visibility: mapElement ? window.getComputedStyle(mapElement).visibility : 'N/A'
        });

        if (!mapElement) {
            console.error('[EMERGENCY-PAGE] ✗ Map element #emergencyMap not found!');
            throw new Error('Map container element #emergencyMap not found in HTML');
        }

        if (mapElement.offsetWidth === 0 || mapElement.offsetHeight === 0) {
            console.error('[EMERGENCY-PAGE] ✗ Map element has zero dimensions:', mapElement.offsetWidth, 'x', mapElement.offsetHeight);
            throw new Error('Map container has invalid dimensions. Please check CSS.');
        }

        if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
            console.error('[EMERGENCY-PAGE] Google Maps API not available');
            throw new Error('Google Maps API is not available. Please check your internet connection.');
        }

        console.log('[EMERGENCY-PAGE] Creating map at:', lat, lng);

        try {
            map = new google.maps.Map(mapElement, {
                zoom: 14,
                center: { lat, lng },
                mapTypeId: google.maps.MapTypeId.ROADMAP,
                styles: [
                    {
                        elementType: 'geometry',
                        stylers: [{ color: '#1a2332' }]
                    },
                    {
                        elementType: 'geometry.stroke',
                        stylers: [{ color: '#2a3a52' }]
                    },
                    {
                        elementType: 'labels.text',
                        stylers: [{ color: '#e8eef7' }]
                    },
                    {
                        elementType: 'labels.icon',
                        stylers: [{ visibility: 'off' }]
                    }
                ]
            });

            console.log('[EMERGENCY-PAGE] ✓ Google Map created successfully');
            
            // ✓ HIDE LOADING SPINNER IMMEDIATELY
            const loadingSpinner = document.getElementById('mapLoadingSpinner');
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
                console.log('[EMERGENCY-PAGE] ✓ Loading spinner hidden');
            }

            // Wait for map to fully load before adding markers
            map.addListener('idle', () => {
                console.log('[EMERGENCY-PAGE] Map is idle, map element size:', mapElement.offsetWidth, 'x', mapElement.offsetHeight);
            });

            // Add user location marker - use custom SVG for better visibility
            const userLocationSVG = `
                <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                    <!-- Outer circle (glow effect) -->
                    <circle cx="20" cy="20" r="18" fill="none" stroke="#00d4ff" stroke-width="2" opacity="0.3"/>
                    <!-- Main circle -->
                    <circle cx="20" cy="20" r="12" fill="#00d4ff" stroke="#0099cc" stroke-width="2"/>
                    <!-- Center dot -->
                    <circle cx="20" cy="20" r="4" fill="#fff"/>
                </svg>
            `;

            const markerImage = {
                url: 'data:image/svg+xml;base64,' + btoa(userLocationSVG),
                size: new google.maps.Size(40, 40),
                origin: new google.maps.Point(0, 0),
                anchor: new google.maps.Point(20, 20),
                scaledSize: new google.maps.Size(40, 40)
            };

            userMarker = new google.maps.Marker({
                position: { lat, lng },
                map: map,
                title: 'Your Location',
                icon: markerImage,
                zIndex: 1000
            });

            console.log('[EMERGENCY-PAGE] ✓ User marker added at:', lat, lng);
            
            // Force map recalculation immediately (no delay)
            google.maps.event.trigger(map, 'resize');
            map.setCenter({ lat, lng });
            console.log('[EMERGENCY-PAGE] ✓ Map resize triggered and centered');
        } catch (mapError) {
            console.error('[EMERGENCY-PAGE] ✗ Error creating map:', mapError.message);
            throw new Error('Failed to initialize Google Map: ' + mapError.message);
        }
    };

    /**
     * Add hospital markers to map
     */
    const addHospitalMarkers = (hospitals) => {
        hospitals.forEach((hospital, index) => {
            const marker = new google.maps.Marker({
                position: { lat: hospital.lat, lng: hospital.lng },
                map: map,
                title: hospital.name,
                label: {
                    text: (index + 1).toString(),
                    color: '#000',
                    fontSize: '12px',
                    fontWeight: 'bold'
                },
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#ff6b6b',
                    fillOpacity: 0.7,
                    strokeColor: '#ff3333',
                    strokeWeight: 2
                }
            });

            const infoWindow = new google.maps.InfoWindow({
                content: `<div style="color: #000; padding: 8px;">
                    <strong>${hospital.name}</strong><br/>
                    ${hospital.address}<br/>
                    Distance: ${hospital.distance.toFixed(1)} km
                </div>`
            });

            marker.addListener('click', () => {
                infoWindow.open(map, marker);
            });

            hospitalMarkers.push({ marker, hospitalId: hospital.id });
        });

        console.log('[EMERGENCY-PAGE] Hospital markers added:', hospitalMarkers.length);
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

        // Create a map of hospital IDs to distance matrix data
        const distanceMap = {};
        if (distanceMatrixData) {
            distanceMatrixData.forEach(d => {
                distanceMap[d.hospitalId] = d;
            });
        }

        let html = '';
        hospitals.forEach((hospital, index) => {
            const distanceData = distanceMap[hospital.id];
            const distance = hospital.distance.toFixed(1);
            const eta = distanceData ? distanceData.duration : 'Calculating...';

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
        console.log('[EMERGENCY-PAGE] Hospital cards rendered:', hospitals.length);
    };

    /**
     * Update map location info display
     */
    const updateLocationInfo = (lat, lng, count) => {
        const userLocationEl = document.getElementById('userLocation');
        const nearbyCountEl = document.getElementById('nearbyCount');

        const formattedLat = lat.toFixed(4);
        const formattedLng = lng.toFixed(4);

        if (userLocationEl) {
            userLocationEl.innerHTML = `<strong>${formattedLat}°N, ${formattedLng}°E</strong>`;
            console.log('[EMERGENCY-PAGE] Location info updated:', formattedLat, formattedLng);
        }

        if (nearbyCountEl) {
            nearbyCountEl.textContent = `${count} hospitals nearby`;
        }
    };

    /**
     * Handle "Get Directions" button click
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
        // Update selected state in UI
        document.querySelectorAll('.hospital-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`.hospital-card[data-hospital-id="${hospitalId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        selectedHospital = { id: hospitalId, name: hospitalName };
        console.log('[EMERGENCY-PAGE] Hospital selected:', hospitalName);

        // Send to backend for dispatch
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
                
                // Redirect to tracking page
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
                if (!checkGoogleMapsAPI()) {
                    throw new Error('Google Maps API failed to load. Please refresh the page.');
                }

                // FAST: Initialize map immediately with fallback location (no waiting)
                const fallbackLoc = { lat: 25.2048, lng: 55.2708 };
                console.log('[EMERGENCY-PAGE] Step 1: Initializing map with fallback location...');
                initializeMap(fallbackLoc.lat, fallbackLoc.lng);
                updateLocationInfo(fallbackLoc.lat, fallbackLoc.lng, 6);
                console.log('[EMERGENCY-PAGE] ✓ Map initialized instantly with fallback');

                // PARALLEL: Request geolocation in background (don't wait)
                console.log('[EMERGENCY-PAGE] Step 2: Requesting real location in background...');
                const locationPromise = getUserLocation(700); // 700ms timeout (fail fast)

                // PARALLEL: Get nearby hospitals (don't wait for real location)
                console.log('[EMERGENCY-PAGE] Step 3: Finding nearby hospitals...');
                const nearbyHospitals = getNearbyHospitals(fallbackLoc.lat, fallbackLoc.lng);
                console.log('[EMERGENCY-PAGE] ✓ Found', nearbyHospitals.length, 'hospitals (using fallback location)');

                // Step 4: Add hospital markers
                console.log('[EMERGENCY-PAGE] Step 4: Adding hospital markers...');
                addHospitalMarkers(nearbyHospitals);
                console.log('[EMERGENCY-PAGE] ✓ Hospital markers added');

                // Step 5: Render hospital cards immediately (skip distance matrix initially)
                console.log('[EMERGENCY-PAGE] Step 5: Rendering hospital cards immediately...');
                renderHospitalCards(nearbyHospitals, null); // Show hospitals instantly
                console.log('[EMERGENCY-PAGE] ✓ Hospital cards rendered');

                console.log('[EMERGENCY-PAGE] ════════════════════════════════════');
                console.log('[EMERGENCY-PAGE] ✓ FAST INITIALIZATION COMPLETE (2-3 seconds)');
                console.log('[EMERGENCY-PAGE] Loading real location and distance data in background...');
                console.log('[EMERGENCY-PAGE] ════════════════════════════════════');

                // =================================================================
                // BACKGROUND ONLY: Request distance matrix data after UI is ready
                // =================================================================
                locationPromise.then(async (realLocation) => {
                    console.log('[EMERGENCY-PAGE] ✓ Real location obtained:', realLocation);
                    
                    // Update if we got a real location (not fallback)
                    if (realLocation && !realLocation.isDefault) {
                        console.log('[EMERGENCY-PAGE] Updating map with real location:', realLocation);
                        userLocation = realLocation;
                        updateMap(realLocation.lat, realLocation.lng);
                        updateLocationInfo(realLocation.lat, realLocation.lng, nearbyHospitals.length);
                        
                        // Update hospitals based on real location
                        const updatedHospitals = getNearbyHospitals(realLocation.lat, realLocation.lng);
                        
                        // Now get distance matrix data with real location
                        console.log('[EMERGENCY-PAGE] Requesting distance matrix with real location...');
                        const distanceData = await getDistanceMatrixData(
                            realLocation.lat,
                            realLocation.lng,
                            updatedHospitals
                        );
                        
                        // Update hospital cards with ETA data
                        renderHospitalCards(updatedHospitals, distanceData);
                        console.log('[EMERGENCY-PAGE] ✓ Hospital list updated with real location and ETA');
                    } else {
                        console.log('[EMERGENCY-PAGE] Using fallback location, skipping distance matrix');
                    }
                }).catch(error => {
                    console.warn('[EMERGENCY-PAGE] Background update error (non-critical):', error.message);
                });

                // Set fallback as current location for now
                userLocation = fallbackLoc;

            } catch (error) {
                console.error('[EMERGENCY-PAGE] ✗ INITIALIZATION ERROR:', error);
                console.error('[EMERGENCY-PAGE] Error details:', error.message);
                
                // Display user-friendly error message
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