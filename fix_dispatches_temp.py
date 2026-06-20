"""Temporary script: reset driver_rejected dispatches back to dispatched for testing."""
from app import get_db

conn = get_db()
cur = conn.cursor(dictionary=True)

# Show current state
cur.execute("SELECT dispatch_id, driver_id, status, timestamp FROM dispatches ORDER BY timestamp DESC LIMIT 10")
rows = cur.fetchall()
print("=== CURRENT DISPATCHES ===")
for r in rows:
    print(r)

# Reset driver_rejected -> dispatched and refresh timestamp so the 10-min timer resets
cur.execute("UPDATE dispatches SET status='dispatched', timestamp=NOW() WHERE status='driver_rejected'")
print(f"\nReset {cur.rowcount} dispatches back to 'dispatched'")

# Refresh timestamps on existing 'dispatched' records so they don't auto-reject immediately
cur.execute("UPDATE dispatches SET timestamp=NOW() WHERE status='dispatched'")
print(f"Refreshed timestamps on {cur.rowcount} dispatched records")

# Free drivers that are stuck On Duty with no active en_route dispatch
cur.execute("""
    UPDATE drivers SET status='Available', last_rejected_at=NULL
    WHERE status='On Duty'
    AND id NOT IN (
        SELECT driver_id FROM dispatches WHERE status IN ('en_route', 'picked_up')
    )
""")
print(f"Freed {cur.rowcount} drivers back to Available")

conn.commit()
cur.close()
conn.close()
print("Done.")
