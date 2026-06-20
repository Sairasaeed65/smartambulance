import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cursor = conn.cursor(dictionary=True)

# Find all drivers marked On Duty with no active dispatch
cursor.execute("""
    SELECT d.id, d.name, d.status
    FROM drivers d
    WHERE d.status = 'On Duty'
    AND NOT EXISTS (
        SELECT 1 FROM dispatches disp
        WHERE disp.driver_id = d.id
        AND disp.status NOT IN ('completed', 'driver_rejected')
    )
""")
stuck = cursor.fetchall()
print('Stuck drivers found:', stuck)

if stuck:
    ids = [r['id'] for r in stuck]
    placeholders = ','.join(['%s'] * len(ids))
    cursor.execute(f"UPDATE drivers SET status='Available' WHERE id IN ({placeholders})", ids)
    conn.commit()
    print('Reset', cursor.rowcount, 'drivers to Available')
else:
    print('No stuck drivers found')

cursor.close()
conn.close()
