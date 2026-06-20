/**
 * =====================================================
 * LOCATION UTILITIES - Coordinate to Place Name Conversion
 * =====================================================
 * Provides functions to convert GPS coordinates to human-readable place names
 * using Google Maps Geocoding API or backend API fallback.
 */

/**
 * Convert GPS coordinates to place name using Google Maps Geocoding API
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {Promise<string>} - Place name or fallback coordinate string
 */
async function getLocationNameGoogleMaps(lat, lng) {
    return new Promise((resolve) => {
        if (!window.google || !window.google.maps) {
            // Google Maps not loaded, use backend API
            getLocationNameBackend(lat, lng).then(resolve);
            return;
        }
        
        try {
            const geocoder = new window.google.maps.Geocoder();
            geocoder.geocode(
                {location: {lat: parseFloat(lat), lng: parseFloat(lng)}},
                function(results, status) {
                    if (status === 'OK' && results && results[0]) {
                        resolve(results[0].formatted_address);
                    } else {
                        resolve(`${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}`);
                    }
                }
            );
        } catch (error) {
            console.error('[GEOCODING] Google Maps error:', error);
            resolve(`${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}`);
        }
    });
}

/**
 * Convert GPS coordinates to place name using backend API
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {Promise<string>} - Place name or fallback coordinate string
 */
async function getLocationNameBackend(lat, lng) {
    try {
        const response = await fetch(`/api/get-place-name?lat=${lat}&lng=${lng}`);
        if (!response.ok) {
            return `${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}`;
        }
        
        const data = await response.json();
        if (data.status === 'success' && data.place_name) {
            return data.place_name;
        }
        return `${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}`;
    } catch (error) {
        console.error('[GEOCODING] Backend API error:', error);
        return `${parseFloat(lat).toFixed(4)}, ${parseFloat(lng).toFixed(4)}`;
    }
}

/**
 * Primary function to get location name (tries Google Maps first, then backend API)
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {Promise<string>} - Place name or fallback coordinate string
 */
async function getLocationName(lat, lng) {
    return getLocationNameGoogleMaps(lat, lng);
}

/**
 * Update a DOM element with place name from coordinates
 * @param {string} elementId - ID of DOM element to update
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 */
async function updateLocationDisplay(elementId, lat, lng) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = 'Loading...';
    const placeName = await getLocationName(lat, lng);
    element.textContent = placeName;
}

/**
 * Batch update multiple location displays
 * @param {Array<{elementId: string, lat: number, lng: number}>} locations
 */
async function updateMultipleLocations(locations) {
    const promises = locations.map(loc =>
        getLocationName(loc.lat, loc.lng)
            .then(placeName => ({
                elementId: loc.elementId,
                placeName: placeName
            }))
    );
    
    const results = await Promise.all(promises);
    results.forEach(result => {
        const element = document.getElementById(result.elementId);
        if (element) {
            element.textContent = result.placeName;
        }
    });
}
