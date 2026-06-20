/**
 * SmartAmbulance Emergency Map Module
 * Handles Google Maps integration and location display on emergency page
 * 
 * Features:
 * - Displays user location on interactive Google Map
 * - Handles geolocation from URL parameters
 * - Falls back to default coordinates if unavailable
 * - Provides clean, modular code structure
 * - Uses async/await for proper asynchronous handling
 */

// Module Configuration
const EmergencyMapModule = (() => {
    /**
     * Private state variables
     */
    let map = null;
    let userMarker = null;
    let infoWindow = null;

    /**
     * Dark-themed map styling that matches SmartAmbulance design
     * Provides better visual hierarchy and eyecare
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
            featureType: 'poi',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }]
        },
        {
            featureType: 'poi.park',
            elementType: 'geometry',
            stylers: [{ color: '#263c3f' }]
        },
        {
            featureType: 'poi.park',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#6b9080' }]
        },
        {
            featureType: 'road',
            elementType: 'geometry',
            stylers: [{ color: '#38414e' }]
        },
        {
            featureType: 'road',
            elementType: 'geometry.stroke',
            stylers: [{ color: '#212a37' }]
        },
        {
            featureType: 'road',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#9ca5b3' }]
        },
        {
            featureType: 'road.highway',
            elementType: 'geometry',
            stylers: [{ color: '#746855' }]
        },
        {
            featureType: 'road.highway',
            elementType: 'geometry.stroke',
            stylers: [{ color: '#1f2835' }]
        },
        {
            featureType: 'road.highway',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#f3751ff' }]
        },
        {
            featureType: 'transit',
            elementType: 'geometry',
            stylers: [{ color: '#2f3948' }]
        },
        {
            featureType: 'transit.station',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#d59563' }]
        },
        {
            featureType: 'water',
            elementType: 'geometry',
            stylers: [{ color: '#17263c' }]
        },
        {
            featureType: 'water',
            elementType: 'labels.text.fill',
            stylers: [{ color: '#515c6d' }]
        },
        {
            featureType: 'water',
            elementType: 'labels.text.stroke',
            stylers: [{ color: '#17263c' }]
        }
    ];

    /**
     * Default fallback coordinates (Dubai, UAE)
     * Used when location data is unavailable
     */
    const DEFAULT_LOCATION = {
        latitude: 25.2048,
        longitude: 55.2708,
        label: 'Default Location'
    };

    /**
     * Initialize Google Map with specified location
     * Creates map instance, adds marker, and sets up info window
     * 
     * @async
     * @param {number} latitude - Latitude coordinate
     * @param {number} longitude - Longitude coordinate
     * @returns {Promise<void>}
     */
    const initializeMap = async (latitude, longitude) => {
        try {
            const userLocation = {
                lat: parseFloat(latitude),
                lng: parseFloat(longitude)
            };

            // Validate coordinates
            if (isNaN(userLocation.lat) || isNaN(userLocation.lng)) {
                console.error('[EMERGENCY-MAP] Invalid coordinates provided');
                return;
            }

            // Wait for map container to be available
            const mapContainer = document.getElementById('emergencyMap');
            if (!mapContainer) {
                console.error('[EMERGENCY-MAP] Map container not found');
                return;
            }

            // Create map instance with dark theme
            map = new google.maps.Map(mapContainer, {
                zoom: 16,
                center: userLocation,
                styles: DARK_MAP_STYLES,
                gestureHandling: 'greedy', // Allow user to scroll page
                disableDoubleClickZoom: false
            });

            console.log('[EMERGENCY-MAP] Map initialized successfully');

            // Add marker and info window
            await addUserMarker(latitude, longitude);

            // Log successful initialization
            console.log(`[EMERGENCY-MAP] Map centered on (${latitude}, ${longitude})`);

        } catch (error) {
            console.error('[EMERGENCY-MAP] Error initializing map:', error);
        }
    };

    /**
     * Add user location marker to map with info window
     * 
     * @async
     * @param {number} latitude - Latitude coordinate
     * @param {number} longitude - Longitude coordinate
     * @returns {Promise<void>}
     */
    const addUserMarker = async (latitude, longitude) => {
        try {
            const userLocation = {
                lat: parseFloat(latitude),
                lng: parseFloat(longitude)
            };

            // Create marker with red icon (standard Google Maps)
            userMarker = new google.maps.Marker({
                position: userLocation,
                map: map,
                title: 'Your Emergency Location',
                icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                animation: google.maps.Animation.DROP
            });

            console.log('[EMERGENCY-MAP] User marker added');

            // Create info window with location details
            infoWindow = new google.maps.InfoWindow({
                content: createInfoWindowContent(latitude, longitude),
                maxWidth: 300
            });

            // Add click listener to marker to toggle info window
            userMarker.addListener('click', () => {
                if (infoWindow) {
                    infoWindow.open(map, userMarker);
                    console.log('[EMERGENCY-MAP] Info window opened');
                }
            });

            // Auto-open info window on page load
            infoWindow.open(map, userMarker);

        } catch (error) {
            console.error('[EMERGENCY-MAP] Error adding marker:', error);
        }
    };

    /**
     * Create HTML content for info window
     * Displays formatted coordinates and location info
     * 
     * @param {number} latitude - Latitude coordinate
     * @param {number} longitude - Longitude coordinate
     * @returns {string} HTML content string
     */
    const createInfoWindowContent = (latitude, longitude) => {
        return `
            <div style="
                color: #333;
                padding: 12px;
                font-family: 'Inter', sans-serif;
                min-width: 180px;
            ">
                <strong style="display: block; margin-bottom: 8px;">Your Emergency Location</strong>
                <div style="font-size: 0.85rem; line-height: 1.6;">
                    <div><strong>Latitude:</strong> ${parseFloat(latitude).toFixed(6)}°</div>
                    <div><strong>Longitude:</strong> ${parseFloat(longitude).toFixed(6)}°</div>
                    <div style="margin-top: 8px; color: #666; font-size: 0.8rem;">
                        Dispatching ambulance to this location...
                    </div>
                </div>
            </div>
        `;
    };

    /**
     * Extract location data from URL parameters
     * Parses query string for lat, lng, accuracy parameters
     * 
     * @returns {Promise<Object>} Location object with latitude, longitude, accuracy
     */
    const extractLocationFromURL = async () => {
        return new Promise((resolve) => {
            try {
                const params = new URLSearchParams(window.location.search);
                const latitude = params.get('lat');
                const longitude = params.get('lng');
                const accuracy = params.get('accuracy');

                if (latitude && longitude) {
                    console.log('[EMERGENCY-MAP] Location found in URL parameters');
                    resolve({
                        latitude: latitude,
                        longitude: longitude,
                        accuracy: accuracy,
                        source: 'URL'
                    });
                } else {
                    console.log('[EMERGENCY-MAP] No location in URL, using default');
                    resolve({
                        latitude: DEFAULT_LOCATION.latitude,
                        longitude: DEFAULT_LOCATION.longitude,
                        accuracy: null,
                        source: 'DEFAULT'
                    });
                }
            } catch (error) {
                console.error('[EMERGENCY-MAP] Error extracting location from URL:', error);
                resolve({
                    latitude: DEFAULT_LOCATION.latitude,
                    longitude: DEFAULT_LOCATION.longitude,
                    accuracy: null,
                    source: 'DEFAULT'
                });
            }
        });
    };

    /**
     * Update location display elements with coordinate information
     * Updates latitude, longitude, and accuracy fields on page
     * 
     * @async
     * @param {number} latitude - Latitude coordinate
     * @param {number} longitude - Longitude coordinate
     * @param {number} accuracy - Location accuracy in meters (optional)
     * @returns {Promise<void>}
     */
    const updateLocationDisplay = async (latitude, longitude, accuracy) => {
        try {
            const latElement = document.getElementById('latitude');
            const lngElement = document.getElementById('longitude');
            const accuracyElement = document.getElementById('accuracy');

            if (latElement) {
                latElement.textContent = `${parseFloat(latitude).toFixed(4)}°N`;
                console.log('[EMERGENCY-MAP] Latitude display updated');
            }

            if (lngElement) {
                lngElement.textContent = `${parseFloat(longitude).toFixed(4)}°E`;
                console.log('[EMERGENCY-MAP] Longitude display updated');
            }

            if (accuracyElement) {
                if (accuracy) {
                    accuracyElement.textContent = `±${Math.round(accuracy)} meters`;
                } else {
                    accuracyElement.textContent = 'Location accuracy unavailable';
                }
                console.log('[EMERGENCY-MAP] Accuracy display updated');
            }

        } catch (error) {
            console.error('[EMERGENCY-MAP] Error updating location display:', error);
        }
    };

    /**
     * Initialize the emergency map module
     * Main entry point - extracts location and sets up map
     * 
     * @async
     * @returns {Promise<void>}
     */
    const init = async () => {
        try {
            console.log('[EMERGENCY-MAP] Initializing emergency map module...');

            // Extract location from URL or use default
            const locationData = await extractLocationFromURL();

            // Update display elements with location info
            await updateLocationDisplay(
                locationData.latitude,
                locationData.longitude,
                locationData.accuracy
            );

            // Initialize map with location coordinates
            await initializeMap(
                locationData.latitude,
                locationData.longitude
            );

            console.log(`[EMERGENCY-MAP] Module initialized successfully (Source: ${locationData.source})`);

        } catch (error) {
            console.error('[EMERGENCY-MAP] Error during initialization:', error);
        }
    };

    /**
     * Public API - expose init function
     */
    return {
        init: init
    };

})();

/**
 * Initialize map when DOM is ready
 * Waits for Google Maps API to load before initializing module
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[EMERGENCY-MAP] DOM loaded, waiting for Google Maps API...');
    
    // Small delay to ensure Google Maps API is available
    setTimeout(async () => {
        await EmergencyMapModule.init();
    }, 100);
});
