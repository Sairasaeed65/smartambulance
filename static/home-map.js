/**
 * SmartAmbulance Home Page Map Module
 * Displays Google Maps with user location and nearby hospitals
 * Activated when emergency button is clicked
 * 
 * Features:
 * - Async geolocation detection
 * - Nearby hospital discovery (5-10 km radius)
 * - Auto-zoom to fit all relevant locations
 * - Interactive markers with info windows
 * - Modular, clean code structure
 */

// ============================================================
// HOSPITAL DATABASE
// ============================================================
// Sample hospital data with coordinates (Dubai area)
const HOSPITALS_DATABASE = [
    {
        id: 1,
        name: 'City General Hospital',
        latitude: 25.2048,
        longitude: 55.2708,
        beds: 150,
        distance: 0,
        department: 'Emergency Ward'
    },
    {
        id: 2,
        name: 'Dubai Medical Center',
        latitude: 25.1972,
        longitude: 55.2770,
        beds: 200,
        distance: 0,
        department: 'Trauma Center'
    },
    {
        id: 3,
        name: 'Al Wasl Hospital',
        latitude: 25.2116,
        longitude: 55.2820,
        beds: 175,
        distance: 0,
        department: 'Critical Care'
    },
    {
        id: 4,
        name: 'Medicana Hospital',
        latitude: 25.1850,
        longitude: 55.2650,
        beds: 120,
        distance: 0,
        department: 'Emergency Services'
    },
    {
        id: 5,
        name: 'Deira Hospital',
        latitude: 25.2656,
        longitude: 55.3215,
        beds: 140,
        distance: 0,
        department: 'Emergency Department'
    },
    {
        id: 6,
        name: 'NMC Specialty Hospital',
        latitude: 25.1622,
        longitude: 55.2490,
        beds: 180,
        distance: 0,
        department: 'Emergency Care'
    }
];

// ============================================================
// HOME MAP MODULE
// ============================================================
const HomeMapModule = (() => {
    /**
     * Private state variables
     */
    let map = null;
    let userMarker = null;
    let hospitalMarkers = [];
    let userLocation = null;

    /**
     * Default fallback coordinates (Dubai)
     */
    const DEFAULT_LOCATION = {
        latitude: 25.2048,
        longitude: 55.2708
    };

    /**
     * Dark-themed map styles matching app design
     */
    const DARK_MAP_STYLES = [
        { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
        {
            featureType: 'administrative.locality',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }]
        },
        {
            featureType: 'road',
            elementType: 'geometry',
            stylers: [{ color: '#38414e' }]
        },
        {
            featureType: 'road',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#9ca5b3' }]
        },
        {
            featureType: 'water',
            elementType: 'geometry',
            stylers: [{ color: '#17263c' }]
        }
    ];

    /**
     * Calculate distance between two coordinates in kilometers
     * Uses Haversine formula
     * 
     * @param {number} lat1 - User latitude
     * @param {number} lng1 - User longitude
     * @param {number} lat2 - Hospital latitude
     * @param {number} lng2 - Hospital longitude
     * @returns {number} Distance in kilometers
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
     * Get hospitals within specified radius
     * 
     * @async
     * @param {number} latitude - User latitude
     * @param {number} longitude - User longitude
     * @param {number} radiusKm - Search radius in kilometers (default 10)
     * @returns {Promise<Array>} Filtered hospitals with distances
     */
    const getNearbyHospitals = async (latitude, longitude, radiusKm = 10) => {
        return new Promise((resolve) => {
            try {
                const nearby = HOSPITALS_DATABASE
                    .map(hospital => ({
                        ...hospital,
                        distance: calculateDistance(
                            latitude,
                            longitude,
                            hospital.latitude,
                            hospital.longitude
                        )
                    }))
                    .filter(hospital => hospital.distance <= radiusKm)
                    .sort((a, b) => a.distance - b.distance);

                console.log(`[HOME-MAP] Found ${nearby.length} hospitals within ${radiusKm}km`);
                resolve(nearby);
            } catch (error) {
                console.error('[HOME-MAP] Error getting nearby hospitals:', error);
                resolve([]);
            }
        });
    };

    /**
     * Calculate optimal zoom level to fit all markers
     * 
     * @param {Array} markers - Array of marker locations
     * @returns {number} Optimal zoom level
     */
    const calculateOptimalZoom = (markers) => {
        if (markers.length <= 1) return 16;

        const bounds = new google.maps.LatLngBounds();
        markers.forEach(marker => {
            bounds.extend(new google.maps.LatLng(marker.latitude, marker.longitude));
        });

        // Rough zoom calculation based on bounds
        const zoom = Math.round(Math.log2(360 / bounds.toSpan().lng())) - 2;
        return Math.max(12, Math.min(zoom, 18));
    };

    /**
     * Initialize Google Map
     * 
     * @async
     * @param {number} latitude - Center latitude
     * @param {number} longitude - Center longitude
     * @returns {Promise<void>}
     */
    const initializeMap = async (latitude, longitude) => {
        try {
            const mapContainer = document.getElementById('homeMap');
            if (!mapContainer) {
                console.error('[HOME-MAP] Map container not found');
                return;
            }

            // Create map instance
            map = new google.maps.Map(mapContainer, {
                zoom: 16,
                center: { lat: parseFloat(latitude), lng: parseFloat(longitude) },
                styles: DARK_MAP_STYLES,
                gestureHandling: 'greedy'
            });

            console.log('[HOME-MAP] Map initialized successfully');
        } catch (error) {
            console.error('[HOME-MAP] Error initializing map:', error);
        }
    };

    /**
     * Add user location marker
     * 
     * @async
     * @param {number} latitude - User latitude
     * @param {number} longitude - User longitude
     * @returns {Promise<void>}
     */
    const addUserMarker = async (latitude, longitude) => {
        try {
            userMarker = new google.maps.Marker({
                position: { lat: parseFloat(latitude), lng: parseFloat(longitude) },
                map: map,
                title: 'Your Location',
                icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                animation: google.maps.Animation.DROP
            });

            // Add info window for user location
            const userInfoWindow = new google.maps.InfoWindow({
                content: `
                    <div style="color: #333; padding: 12px; font-family: 'Inter', sans-serif;">
                        <strong>Your Location</strong><br>
                        Lat: ${parseFloat(latitude).toFixed(6)}°<br>
                        Lng: ${parseFloat(longitude).toFixed(6)}°<br>
                        <span style="font-size: 0.8rem; color: #666; margin-top: 8px; display: block;">
                            📍 Emergency location detected
                        </span>
                    </div>
                `,
                maxWidth: 300
            });

            userMarker.addListener('click', () => {
                userInfoWindow.open(map, userMarker);
            });

            userInfoWindow.open(map, userMarker);
            console.log('[HOME-MAP] User marker added');

        } catch (error) {
            console.error('[HOME-MAP] Error adding user marker:', error);
        }
    };

    /**
     * Add hospital markers to map
     * 
     * @async
     * @param {Array} hospitals - Array of hospital objects
     * @returns {Promise<void>}
     */
    const addHospitalMarkers = async (hospitals) => {
        try {
            hospitalMarkers = hospitals.map((hospital, index) => {
                const marker = new google.maps.Marker({
                    position: {
                        lat: hospital.latitude,
                        lng: hospital.longitude
                    },
                    map: map,
                    title: hospital.name,
                    icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
                });

                // Create info window for hospital
                const hospitalInfoWindow = new google.maps.InfoWindow({
                    content: `
                        <div style="color: #333; padding: 12px; font-family: 'Inter', sans-serif; min-width: 220px;">
                            <strong style="display: block; margin-bottom: 8px; color: #d4143c;">
                                <i class="fas fa-hospital"></i> ${hospital.name}
                            </strong>
                            <div style="font-size: 0.85rem; line-height: 1.6;">
                                <div><strong>Distance:</strong> ${hospital.distance.toFixed(1)} km</div>
                                <div><strong>Available Beds:</strong> ${hospital.beds}</div>
                                <div><strong>Department:</strong> ${hospital.department}</div>
                                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; color: #666; font-size: 0.8rem;">
                                    ⏱️ ETA: ${Math.ceil(hospital.distance / 0.85)} mins
                                </div>
                            </div>
                        </div>
                    `,
                    maxWidth: 300
                });

                marker.addListener('click', () => {
                    // Close all other info windows would go here if we tracked them
                    hospitalInfoWindow.open(map, marker);
                });

                return marker;
            });

            console.log(`[HOME-MAP] Added ${hospitalMarkers.length} hospital markers`);

        } catch (error) {
            console.error('[HOME-MAP] Error adding hospital markers:', error);
        }
    };

    /**
     * Adjust map zoom to fit all markers (user + hospitals)
     * 
     * @async
     * @returns {Promise<void>}
     */
    const adjustMapBounds = async () => {
        try {
            const bounds = new google.maps.LatLngBounds();

            // Add user location to bounds
            if (userMarker) {
                bounds.extend(userMarker.getPosition());
            }

            // Add all hospital markers to bounds
            hospitalMarkers.forEach(marker => {
                bounds.extend(marker.getPosition());
            });

            // Fit map to bounds
            if (userMarker || hospitalMarkers.length > 0) {
                map.fitBounds(bounds);
                
                // Add some padding
                const padding = { top: 50, right: 50, bottom: 50, left: 50 };
                map.fitBounds(bounds, padding);
            }

            console.log('[HOME-MAP] Map bounds adjusted to fit all markers');

        } catch (error) {
            console.error('[HOME-MAP] Error adjusting map bounds:', error);
        }
    };

    /**
     * Get user location via geolocation API
     * 
     * @async
     * @returns {Promise<Object>} Location object with latitude and longitude
     */
    const getUserLocation = async () => {
        return new Promise((resolve) => {
            if (!('geolocation' in navigator)) {
                console.warn('[HOME-MAP] Geolocation not supported, using default');
                resolve(DEFAULT_LOCATION);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const location = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    console.log(`[HOME-MAP] Location obtained: ${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`);
                    resolve(location);
                },
                (error) => {
                    console.warn(`[HOME-MAP] Geolocation error: ${error.message}`);
                    resolve(DEFAULT_LOCATION);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 8000,
                    maximumAge: 0
                }
            );
        });
    };

    /**
     * Show the home map modal/container
     * 
     * @returns {void}
     */
    const showMap = () => {
        const mapContainer = document.getElementById('homeMapContainer');
        if (mapContainer) {
            mapContainer.style.display = 'flex';
            console.log('[HOME-MAP] Map container shown');
        }
    };

    /**
     * Hide the home map modal/container
     * 
     * @returns {void}
     */
    const hideMap = () => {
        const mapContainer = document.getElementById('homeMapContainer');
        if (mapContainer) {
            mapContainer.style.display = 'none';
            console.log('[HOME-MAP] Map container hidden');
        }
    };

    /**
     * Initialize the home map system
     * Main entry point
     * 
     * @async
     * @returns {Promise<void>}
     */
    const init = async () => {
        try {
            console.log('[HOME-MAP] Initializing home map module...');

            // Show map container
            showMap();

            // Get user location
            userLocation = await getUserLocation();

            // Initialize map
            await initializeMap(userLocation.latitude, userLocation.longitude);

            // Add user marker
            await addUserMarker(userLocation.latitude, userLocation.longitude);

            // Get nearby hospitals
            const nearbyHospitals = await getNearbyHospitals(
                userLocation.latitude,
                userLocation.longitude,
                10 // 10 km radius
            );

            // Add hospital markers
            if (nearbyHospitals.length > 0) {
                await addHospitalMarkers(nearbyHospitals);
                await adjustMapBounds();
            } else {
                console.log('[HOME-MAP] No hospitals found in radius');
            }

            console.log('[HOME-MAP] Module initialized successfully');

        } catch (error) {
            console.error('[HOME-MAP] Error during initialization:', error);
        }
    };

    /**
     * Public API
     */
    return {
        init: init,
        show: showMap,
        hide: hideMap
    };

})();

/**
 * Export for use in other scripts
 */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HomeMapModule;
}
