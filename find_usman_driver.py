"""Search for Usman Akhtar driver"""

import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='smartambulance'
)
cursor = conn.cursor(dictionary=True)

# Search for Usman Akhtar
cursor.execute("SELECT id, username, password, name, phone, assigned_ambulance, hospital_id FROM drivers WHERE name LIKE '%Usman%' OR name LIKE '%akhtar%' OR username LIKE '%usman%'")
result = cursor.fetchall()

if result:
    print('=' * 80)
    print('FOUND USMAN AKHTAR DRIVER')
    print('=' * 80)
    for driver in result:
        print(f'\nID: {driver["id"]}')
        print(f'Username: {driver["username"]}')
        print(f'Password: {driver["password"]}')
        print(f'Name: {driver["name"]}')
        print(f'Phone: {driver["phone"]}')
        print(f'Ambulance: {driver["assigned_ambulance"]}')
        print(f'Hospital ID: {driver["hospital_id"]}')
else:
    print('=' * 80)
    print('USMAN AKHTAR NOT FOUND - AVAILABLE DRIVERS:')
    print('=' * 80)
    cursor.execute('SELECT id, username, password, name, hospital_id FROM drivers ORDER BY id')
    drivers = cursor.fetchall()
    for d in drivers:
        print(f'ID: {d["id"]:<3} | Username: {d["username"]:<20} | Password: {d["password"]:<15} | Name: {d["name"]:<30} | Hospital: {d["hospital_id"]}')

cursor.close()
conn.close()
