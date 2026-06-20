import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='smartambulance')
cur = conn.cursor(dictionary=True)

# Cancel stale requests stuck at hospital 5 (no ambulances there)
cur.execute("UPDATE patient_requests SET status='cancelled' WHERE hospital_id=5 AND status='pending'")
print('Cancelled hospital-5 requests:', cur.rowcount)
conn.commit()

# Show current pending per hospital
cur.execute("SELECT hospital_id, COUNT(*) as cnt FROM patient_requests WHERE status IN ('pending','assigned','en_route') GROUP BY hospital_id")
print('Remaining active per hospital:')
for r in cur.fetchall(): print(r)

cur.close()
conn.close()
print('Done')
