import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='smartambulance'
)

cursor = conn.cursor()

# Find all foreign keys on drivers table
cursor.execute("""
    SELECT CONSTRAINT_NAME 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
    WHERE TABLE_NAME='drivers' AND CONSTRAINT_TYPE='FOREIGN KEY'
""")

constraints = cursor.fetchall()
print("Foreign Keys on drivers table:")
for constraint in constraints:
    print(f"  - {constraint[0]}")

# Try to drop the ambulance-related foreign key
if constraints:
    for constraint in constraints:
        constraint_name = constraint[0]
        try:
            print(f"Dropping constraint: {constraint_name}")
            cursor.execute(f"ALTER TABLE drivers DROP FOREIGN KEY {constraint_name}")
            conn.commit()
            print(f"✓ Successfully dropped {constraint_name}")
        except Exception as e:
            print(f"✗ Error dropping {constraint_name}: {e}")
else:
    print("No foreign keys found - they may already be dropped")

cursor.close()
conn.close()
