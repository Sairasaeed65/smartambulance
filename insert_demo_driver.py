import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='smartambulance'
)
cursor = conn.cursor()
insert_sql = '''INSERT INTO drivers 
(username, password, name, phone, cnic, experience, 
shift, assigned_ambulance, status, hospital_id, certifications)
VALUES 
('DRV-001', 'pass123', 'Ali Hassan', '+923001234567', 
'3520112345678', 5, 'Morning', 'SA-001', 'Available', 1, 
'["Basic EMT"]')'''
try:
    cursor.execute(insert_sql)
    conn.commit()
    print('✓ Demo driver DRV-001 inserted successfully')
except mysql.connector.Error as e:
    if 'Duplicate entry' in str(e):
        print('✓ Demo driver DRV-001 already exists')
    else:
        print(f'Error: {e}')
cursor.close()
conn.close()
