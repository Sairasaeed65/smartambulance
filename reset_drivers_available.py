"""
Fix stuck drivers: reset On Duty drivers whose dispatches are already completed or old
"""
import mysql.connector
from datetime import datetime

conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cursor = conn.cursor(dictionary=True)

# 1. Find drivers marked On Duty but their latest dispatch is already completed/rejected
cursor.execute("""
    SELECT d.id, d.name, d.hospital_id, d.status
    FROM drivers d
    WHERE d.status = 'On Duty'
""")
on_duty_drivers = cursor.fetchall()

print(f'Drivers On Duty: {len(on_duty_drivers)}')
reset_ids = []

for drv in on_duty_drivers:
    # Get latest dispatch for this driver
    cursor.execute("""
        SELECT dispatch_id, status FROM dispatches 
        WHERE driver_id = %s 
        ORDER BY id DESC LIMIT 1
    """, (drv['id'],))
    latest = cursor.fetchone()
    
    if not latest:
        print(f"  Driver {drv['name']} (ID:{drv['id']}) has no dispatches - resetting to Available")
        reset_ids.append(drv['id'])
    elif latest['status'] in ('completed', 'driver_rejected', 'cancelled'):
        print(f"  Driver {drv['name']} (ID:{drv['id']}) latest dispatch={latest['dispatch_id']} status={latest['status']} - resetting to Available")
        reset_ids.append(drv['id'])
    else:
        # Active dispatch (dispatched/en_route) - mark it completed and reset driver
        print(f"  Driver {drv['name']} (ID:{drv['id']}) has active dispatch={latest['dispatch_id']} status={latest['status']} - completing and resetting")
        cursor.execute("UPDATE dispatches SET status='completed' WHERE dispatch_id=%s", (latest['dispatch_id'],))
        reset_ids.append(drv['id'])

if reset_ids:
    placeholders = ','.join(['%s'] * len(reset_ids))
    cursor.execute(f"UPDATE drivers SET status='Available' WHERE id IN ({placeholders})", reset_ids)
    conn.commit()
    print(f'\nReset {len(reset_ids)} drivers to Available: {reset_ids}')
else:
    print('No drivers to reset')

# 2. Also reset ambulance statuses for those drivers
cursor.execute("""
    UPDATE ambulances a
    JOIN drivers d ON d.assigned_ambulance = a.ambulance_number
    SET a.status = 'Available'
    WHERE d.id IN ({})
""".format(','.join(['%s'] * len(reset_ids)) if reset_ids else '0'), reset_ids if reset_ids else [])
conn.commit()
print(f'Reset ambulance statuses for affected drivers')

cursor.close()
conn.close()
print('\nDone! Drivers are back to Available status.')
