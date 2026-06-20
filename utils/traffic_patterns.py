TRAFFIC_SPEEDS = {
    0: 60, 1: 65, 2: 65, 3: 65, 4: 60,
    5: 50, 6: 30, 7: 20, 8: 20, 9: 35,
    10: 45, 11: 50, 12: 40, 13: 45, 14: 50,
    15: 50, 16: 45, 17: 25, 18: 15, 19: 20,
    20: 40, 21: 50, 22: 55, 23: 60
}


def get_speed_for_hour(hour):
    return TRAFFIC_SPEEDS.get(hour, 40)


def get_traffic_level(hour):
    speed = get_speed_for_hour(hour)
    if speed >= 55:
        return 'FREE'
    elif speed >= 40:
        return 'LIGHT'
    elif speed >= 25:
        return 'MODERATE'
    else:
        return 'HEAVY'
