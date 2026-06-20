import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cursor = conn.cursor(dictionary=True)
cursor.execute("""
    SELECT d.dispatch_id, d.status as dispatch_status,
           drv.name as driver_name, drv.status as driver_status, drv.hospital_id
    FROM dispatches d
    JOIN drivers drv ON d.driver_id = drv.id
    WHERE drv.status = 'On Duty'
""")
rows = cursor.fetchall()
print(f'On Duty drivers with dispatches: {len(rows)}')
for row in rows:
    print(row)
cursor.close()
conn.close()
