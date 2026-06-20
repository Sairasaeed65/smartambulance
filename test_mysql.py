"""
Quick test to verify MySQL connection and database setup
"""

import mysql.connector  # type: ignore
from mysql.connector import Error  # type: ignore

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'root'
DB_NAME = 'smartambulance'

print('=' * 60)
print('SmartAmbulance - MySQL Connection Test')
print('=' * 60)

# Test 1: Check if MySQL server is running
print('\n[TEST 1] Connecting to MySQL Server...')
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print('✓ SUCCESS: Connected to MySQL Server')
    print(f'   Host: {DB_HOST}')
    print(f'   User: {DB_USER}')
    cursor = conn.cursor()
    cursor.execute('SELECT VERSION()')
    version = cursor.fetchone()[0]
    print(f'   MySQL Version: {version}')
    cursor.close()
    conn.close()
except Error as e:
    print(f'✗ FAILED: Cannot connect to MySQL')
    print(f'   Error: {e}')
    print('\n[ACTION REQUIRED]')
    print('   1. Install MySQL Server from https://dev.mysql.com/downloads/mysql/')
    print('   2. Start MySQL Service (windows: Services > MySQL80, mac: brew services start mysql)')
    print('   3. Verify password is "root" (or update DB_PASSWORD in app.py)')
    exit(1)

# Test 2: Check if database can be created
print('\n[TEST 2] Testing database creation...')
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')
    print(f'✓ SUCCESS: Database "{DB_NAME}" is ready')
    cursor.close()
    conn.close()
except Error as e:
    print(f'✗ FAILED: Cannot create database')
    print(f'   Error: {e}')
    exit(1)

# Test 3: Check if tables can be created
print('\n[TEST 3] Testing table creation...')
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_value VARCHAR(100)
        )
    ''')
    cursor.execute('DROP TABLE IF EXISTS test_table')
    print('✓ SUCCESS: Can create and manage tables')
    cursor.close()
    conn.close()
except Error as e:
    print(f'✗ FAILED: Cannot create tables')
    print(f'   Error: {e}')
    exit(1)

print('\n' + '=' * 60)
print('✓ ALL TESTS PASSED')
print('=' * 60)
print('\n[READY] MySQL is configured and ready for SmartAmbulance')
print('\nNext Steps:')
print('1. Run: python app.py')
print('2. Access: http://localhost:5000')
print('3. Login with demo credentials from MYSQL_INTEGRATION.md')
print('\n' + '=' * 60)
