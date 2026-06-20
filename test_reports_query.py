import sys
sys.path.insert(0, '.')
from app import app, get_db, DB_NAME

with app.app_context():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        cursor.execute('SELECT COUNT(*) AS cnt FROM patient_requests')
        total = cursor.fetchone()['cnt']
        print('total_emergencies:', total)

        cursor.execute("""
            SELECT h.id,
                   COALESCE(h.name, h.username) AS name,
                   COUNT(pr.id) AS total,
                   SUM(CASE WHEN LOWER(pr.status) = 'completed' THEN 1 ELSE 0 END) AS completed,
                   AVG(CASE WHEN LOWER(d.status) = 'completed'
                            THEN TIMESTAMPDIFF(MINUTE, d.timestamp, d.updated_at)
                            ELSE NULL END) AS avg_response_min
            FROM hospitals h
            LEFT JOIN patient_requests pr ON pr.hospital_id = h.id
            LEFT JOIN dispatches d ON d.hospital_id = h.id AND d.request_id = pr.request_id
            GROUP BY h.id, h.name, h.username
            ORDER BY total DESC
        """)
        hp = cursor.fetchall()
        print('hospital_perf rows:', len(hp))

        cursor.execute("""
            SELECT dr.id,
                   COALESCE(dr.name, dr.username) AS name,
                   COALESCE(h.name, h.username, 'Unassigned') AS hospital_name,
                   COUNT(pr.id) AS total,
                   SUM(CASE WHEN LOWER(pr.status) = 'completed' THEN 1 ELSE 0 END) AS completed,
                   AVG(CASE WHEN LOWER(d.status) = 'completed'
                            THEN TIMESTAMPDIFF(MINUTE, d.timestamp, d.updated_at)
                            ELSE NULL END) AS avg_response_min
            FROM drivers dr
            LEFT JOIN hospitals h ON dr.hospital_id = h.id
            LEFT JOIN patient_requests pr ON pr.assigned_driver_id = dr.id
            LEFT JOIN dispatches d ON d.driver_id = dr.id AND d.request_id = pr.request_id
            GROUP BY dr.id, dr.name, dr.username, h.name, h.username
            ORDER BY total DESC
        """)
        da = cursor.fetchall()
        print('driver_activity rows:', len(da))

        cursor.execute("""
            SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
            FROM patient_requests
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY day
        """)
        t7 = cursor.fetchall()
        print('trend_7days rows:', len(t7))

        cursor.execute("""
            SELECT COALESCE(LOWER(status), 'unknown') AS status, COUNT(*) AS cnt
            FROM patient_requests
            GROUP BY LOWER(status)
            ORDER BY cnt DESC
        """)
        sb = cursor.fetchall()
        print('status_breakdown rows:', len(sb))

        cursor.close()
        conn.close()
        print('ALL QUERIES OK')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('ERROR:', e)
