import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cursor = conn.cursor(dictionary=True)

print('=== RECENT DISPATCHES ===')
cursor.execute("""
    SELECT dispatch_id, driver_id, driver_name, status, request_id, timestamp
    FROM dispatches
    ORDER BY timestamp DESC LIMIT 10
""")
for r in cursor.fetchall():
    print(r)

print()
print('=== PATIENT REQUESTS WITH DRIVER ASSIGNED ===')
cursor.execute("""
    SELECT request_id, patient_name, status, assigned_driver, assigned_driver_id
    FROM patient_requests
    WHERE assigned_driver IS NOT NULL
    ORDER BY timestamp DESC LIMIT 10
""")
for r in cursor.fetchall():
    print(r)

cursor.close()
conn.close()
