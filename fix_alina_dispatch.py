import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cursor = conn.cursor(dictionary=True)

# Fix: restore the dispatch to picked_up so driver can complete the trip
cursor.execute("""
    UPDATE dispatches SET status='picked_up'
    WHERE dispatch_id='DSP-2026-20260414013738'
    AND driver_id=31
""")
print('Dispatch fixed:', cursor.rowcount)

# Ensure driver is On Duty
cursor.execute("UPDATE drivers SET status='On Duty' WHERE id=31")
print('Driver fixed:', cursor.rowcount)

conn.commit()
cursor.close()
conn.close()
print('Done')
