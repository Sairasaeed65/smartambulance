"""
Google Maps Directions API Service
Provides real-time ETA and traffic data using Google Maps API
Falls back to Haversine calculation if API fails
"""

import requests
import os
from math import radians, sin, cos, sqrt, atan2


MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')


def get_traffic_eta(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Get real-time ETA using Google Maps Directions API with traffic data.
    
    Parameters:
        origin_lat, origin_lng: Ambulance/Hospital GPS coordinates
        dest_lat, dest_lng: Patient/Destination GPS coordinates
    
    Returns:
        {
            'eta_minutes': int,           # Time in minutes
            'distance_km': float,         # Distance in kilometers
            'traffic': str,               # 'light', 'moderate', 'heavy', 'unknown'
            'success': bool,              # True if API call succeeded
            'duration_in_traffic': int,   # Raw duration in seconds
            'duration_normal': int,       # Normal duration without traffic
        }
    
    On API failure, falls back to Haversine distance + 30 km/h estimate.
    """
    
    if not MAPS_API_KEY:
        print('[MAPS_SERVICE] WARNING: GOOGLE_MAPS_API_KEY not set, using fallback')
        return _fallback_calculation(origin_lat, origin_lng, dest_lat, dest_lng)
    
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data['status'] == 'OK' and data['routes']:
            leg = data['routes'][0]['legs'][0]
            
            # Extract duration and distance
            eta = leg.get('duration_in_traffic', leg.get('duration'))
            eta_seconds = eta.get('value', 0) if isinstance(eta, dict) else eta
            eta_minutes = max(1, round(eta_seconds / 60))
            
            distance_meters = leg['distance'].get('value', 0)
            distance_km = round(distance_meters / 1000, 1)
            
            # Calculate traffic level based on duration ratio
            duration_normal = leg['duration']['value']
            duration_traffic = leg.get('duration_in_traffic', {}).get('value', duration_normal)
            
            if duration_normal > 0:
                ratio = duration_traffic / duration_normal
                if ratio > 1.5:
                    traffic = 'heavy'
                elif ratio > 1.2:
                    traffic = 'moderate'
                else:
                    traffic = 'light'
            else:
                traffic = 'unknown'
            
            print(f'[MAPS_SERVICE] API Success: {distance_km}km | {eta_minutes}min | {traffic} traffic')
            
            return {
                'eta_minutes': eta_minutes,
                'distance_km': distance_km,
                'traffic': traffic,
                'success': True,
                'duration_in_traffic': duration_traffic,
                'duration_normal': duration_normal,
            }
        else:
            print(f'[MAPS_SERVICE] API Error: {data.get("status")} - {data.get("error_message", "")}')
            return _fallback_calculation(origin_lat, origin_lng, dest_lat, dest_lng)
            
    except requests.exceptions.Timeout:
        print('[MAPS_SERVICE] API Timeout, using fallback')
        return _fallback_calculation(origin_lat, origin_lng, dest_lat, dest_lng)
    except Exception as e:
        print(f'[MAPS_SERVICE] API Exception: {str(e)}, using fallback')
        return _fallback_calculation(origin_lat, origin_lng, dest_lat, dest_lng)


def _fallback_calculation(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Fallback: Calculate ETA using Haversine distance + average speed estimate.
    Used when Google Maps API is unavailable or fails.
    """
    try:
        R = 6371  # Earth radius in km
        
        lat1 = radians(float(origin_lat))
        lon1 = radians(float(origin_lng))
        lat2 = radians(float(dest_lat))
        lon2 = radians(float(dest_lng))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = round(R * c, 1)
        
        # Estimate: 30 km/h average speed in urban areas
        eta_minutes = max(1, round((distance_km / 30) * 60))
        
        print(f'[MAPS_SERVICE] Fallback: {distance_km}km | {eta_minutes}min (no traffic data)')
        
        return {
            'eta_minutes': eta_minutes,
            'distance_km': distance_km,
            'traffic': 'unknown',
            'success': False,
            'duration_in_traffic': None,
            'duration_normal': None,
        }
    except Exception as e:
        print(f'[MAPS_SERVICE] Fallback calculation failed: {str(e)}')
        # Last resort: return minimal response
        return {
            'eta_minutes': 15,
            'distance_km': 0.0,
            'traffic': 'unknown',
            'success': False,
            'duration_in_traffic': None,
            'duration_normal': None,
        }
