def calculate_score(hospital, patient_lat, patient_lon):
    from app import calculate_distance

    dist = calculate_distance(
        patient_lat, patient_lon,
        float(hospital['latitude']),
        float(hospital['longitude'])
    )

    dist_score = max(0, (50 - dist) / 50) * 100

    if hospital['total_beds'] > 0:
        bed_score = (hospital['available_beds'] / hospital['total_beds']) * 100
    else:
        bed_score = 0

    perf_score = hospital.get('performance_score', 75)

    total = (dist_score * 0.40 + bed_score * 0.30 + perf_score * 0.30)

    return round(total, 2), round(dist, 2)


def select_best_hospital(hospitals, patient_lat, patient_lon):
    scored = []
    for h in hospitals:
        score, dist = calculate_score(h, patient_lat, patient_lon)
        scored.append({
            **h,
            'score': score,
            'distance_km': dist
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[0]
