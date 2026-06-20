"""
ai_engine.py — AI Scoring Engine for Smart Ambulance Dispatch
=============================================================
FYP: AI-Driven Emergency Ambulance Routing System

This module implements a weighted multi-factor scoring model that ranks
ambulance dispatch candidates. Lower score = better candidate (penalty-based).

The model evaluates 5 real-world factors that influence emergency response:
  1. ETA / travel time          (50%) — MOST CRITICAL: fastest arrival saves lives
  2. Physical distance          (25%) — secondary distance penalty
  3. Hospital bed availability  (15%) — only penalises if beds = 0 (full)
  4. Ambulance fleet load        (5%) — avoids overloading a busy hospital
  5. Driver response history     (5%) — prefers faster, experienced drivers
"""

import math


# ---------------------------------------------------------------------------
# HAVERSINE DISTANCE HELPER
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate straight-line distance between two GPS coordinates using the
    Haversine formula.

    WHY: GPS coordinates are spherical (on a globe), not flat. Euclidean
    distance would be inaccurate for real map distances. Haversine gives the
    great-circle distance — the shortest path over the Earth's surface —
    which correlates strongly with road distance in urban areas.

    Returns: distance in kilometres (float)
    """
    R = 6371.0  # Earth's mean radius in km

    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat   = math.radians(lat2 - lat1)
    dlng   = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2)

    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# MAIN SCORING FUNCTION
# ---------------------------------------------------------------------------

def calculate_dispatch_score(
    ambulance_lat: float,
    ambulance_lng: float,
    patient_lat: float,
    patient_lng: float,
    eta_minutes: float,
    hospital_busy_ambulances: int,
    hospital_total_ambulances: int,
    hospital_total_beds: int,
    hospital_available_beds: int,
    driver_avg_response_minutes: float = 15.0,
) -> dict:
    """
    Compute a weighted penalty score for dispatching a specific ambulance/hospital
    to a patient. A LOWER score means a BETTER candidate for dispatch.

    Parameters
    ----------
    ambulance_lat, ambulance_lng   : GPS position of the ambulance (or hospital)
    patient_lat, patient_lng       : GPS position of the patient
    eta_minutes                    : Traffic-aware ETA from Google Maps (minutes)
    hospital_busy_ambulances       : Number of ambulances currently on duty
    hospital_total_ambulances      : Total ambulances registered at the hospital
    hospital_total_beds            : Total bed capacity of the hospital
    hospital_available_beds        : Beds currently free/unoccupied
    driver_avg_response_minutes    : Historical average response time of this driver
                                     (default 15 min if no history exists)

    Returns
    -------
    dict with keys:
        total_score           -- weighted penalty (lower is better)
        distance_km           -- raw Haversine distance
        eta_minutes           -- traffic-aware ETA used for scoring
        breakdown             -- per-factor scores before weighting
        hospital_bed_status   -- "available" / "low" / "full"
        recommendation_reason -- human-readable explanation for the viva / logs
    """

    # -----------------------------------------------------------------------
    # FACTOR 1 -- ETA / TRAVEL TIME  (weight: 50%)
    # -----------------------------------------------------------------------
    # ETA is THE most critical factor in emergency dispatch.
    # The Golden Hour principle states trauma patients have best survival
    # outcomes when definitive care begins within 60 minutes.
    # Traffic-aware ETA from Google Maps is used so real-world congestion
    # is already baked in.
    #
    # Normalisation: divide by 30 min so a 30-minute ETA scores 1.0
    # (maximum penalty).
    # -----------------------------------------------------------------------

    eta_score = eta_minutes / 30.0

    # -----------------------------------------------------------------------
    # FACTOR 2 -- DISTANCE  (weight: 25%)
    # -----------------------------------------------------------------------
    # Physical distance is a secondary penalty. ETA already captures
    # traffic-adjusted travel time, but distance still correlates with
    # fuel cost, risk of breakdown, and general proximity.
    #
    # Normalisation: divide by 20 km so a 20 km trip scores 1.0.
    # -----------------------------------------------------------------------

    distance_km    = _haversine_km(ambulance_lat, ambulance_lng, patient_lat, patient_lng)
    distance_score = distance_km / 20.0

    # -----------------------------------------------------------------------
    # FACTOR 3 -- BED AVAILABILITY  (weight: 15%)
    # -----------------------------------------------------------------------
    # Only penalise a hospital that has ZERO free beds — the patient would
    # need an immediate secondary transfer, losing critical time.
    # Any hospital with at least 1 bed available gets NO penalty; we do not
    # discriminate between "9 beds" and "150 beds" since both can admit the
    # patient. ETA (factor 1) already determines the best candidate.
    # -----------------------------------------------------------------------

    if hospital_available_beds == 0:
        bed_score           = 1.0   # completely full -- near-disqualification
        hospital_bed_status = "full"
    else:
        bed_score           = 0.0   # at least 1 bed -- no penalty
        hospital_bed_status = "available"

    # -----------------------------------------------------------------------
    # FACTOR 4 -- AMBULANCE FLEET LOAD  (weight: 5%)
    # -----------------------------------------------------------------------
    # busy_ratio (0-1): proportion of fleet currently on active calls.
    # Higher utilisation = less spare capacity for follow-up emergencies.
    # -----------------------------------------------------------------------

    busy_ratio = hospital_busy_ambulances / max(hospital_total_ambulances, 1)
    load_score = busy_ratio

    # -----------------------------------------------------------------------
    # FACTOR 5 -- DRIVER RESPONSE HISTORY  (weight: 5%)
    # -----------------------------------------------------------------------
    # Drivers with a faster historical average are preferred.
    # Default of 15 minutes is used for new drivers with no recorded history.
    # -----------------------------------------------------------------------

    history_score = driver_avg_response_minutes / 30.0

    # -----------------------------------------------------------------------
    # WEIGHTED TOTAL SCORE
    # -----------------------------------------------------------------------
    # Weights: 0.50 + 0.25 + 0.15 + 0.05 + 0.05 = 1.00
    # -----------------------------------------------------------------------

    total_score = (
        0.50 * eta_score      +   # ETA              -- 50%
        0.25 * distance_score +   # Distance         -- 25%
        0.15 * bed_score      +   # Bed availability -- 15%
        0.05 * load_score     +   # Fleet load       --  5%
        0.05 * history_score      # Driver history   --  5%
    )

    # Round for readability
    total_score    = round(total_score, 4)
    distance_km    = round(distance_km, 3)
    eta_score      = round(eta_score, 4)
    distance_score = round(distance_score, 4)
    load_score     = round(load_score, 4)
    bed_score      = round(bed_score, 4)
    history_score  = round(history_score, 4)

    # -----------------------------------------------------------------------
    # RECOMMENDATION REASON
    # -----------------------------------------------------------------------

    if eta_minutes <= 5:
        recommendation_reason = f"Fastest arrival: {eta_minutes} min"
    elif distance_km <= 3:
        recommendation_reason = f"Nearest hospital: {distance_km} km"
    else:
        recommendation_reason = f"Best overall: {eta_minutes} min, {distance_km} km"

    return {
        'total_score':  total_score,
        'distance_km':  distance_km,
        'eta_minutes':  eta_minutes,
        'breakdown': {
            'eta_score':              eta_score,
            'distance_score':         distance_score,
            'bed_availability_score': bed_score,
            'ambulance_load_score':   load_score,
            'driver_history_score':   history_score,
        },
        'hospital_bed_status':    hospital_bed_status,
        'recommendation_reason':  recommendation_reason,
    }



# ---------------------------------------------------------------------------
# DEMAND PREDICTION FUNCTION
# ---------------------------------------------------------------------------

def predict_demand(hour: int, day_of_week: int) -> str:
    """
    Predict emergency call demand level based on time patterns.

    Parameters
    ----------
    hour         : Hour of day (0–23)
    day_of_week  : 0 = Monday … 6 = Sunday  (Python datetime.weekday() convention)

    Returns
    -------
    'high' | 'medium' | 'low'

    WHY DEMAND PREDICTION MATTERS:
    Knowing peak demand periods allows the dispatch system to:
      • Pre-position ambulances closer to high-call-volume areas before peaks
      • Alert hospital staff to prepare for incoming patients
      • Adjust scoring weights during high-demand periods (future enhancement)

    Pattern rationale (based on Pakistani urban ambulance call data patterns):
      HIGH   — Morning rush (8–9 am: road accidents, cardiac events triggered
                by exertion), evening rush (17–19: traffic accidents, workplace
                injuries), and Mondays (post-weekend return to activity).
      MEDIUM — Daytime hours (10 am–4 pm): steady baseline demand.
      LOW    — Late night / early morning: population is mostly stationary.
    """

    # High demand: rush hours or Monday (busiest weekday)
    high_hours = {8, 9, 17, 18, 19}

    if hour in high_hours or day_of_week == 0:
        return 'high'

    # Medium demand: regular daytime activity
    medium_hours = {10, 11, 12, 13, 14, 15, 16}

    if hour in medium_hours:
        return 'medium'

    # Low demand: night-time and early morning
    return 'low'
