"""
Database Setup Script for SmartAmbulance
This script creates the MySQL database and tables automatically
Run this before starting the Flask application (optional - Flask does it automatically on startup)

Usage:
    python db_setup.py

Database Connection Settings:
    Host: localhost
    User: root
    Password: root (update if different)
    Database: smartambulance (auto-created)
"""

import mysql.connector  # type: ignore
from mysql.connector import Error  # type: ignore

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''  # Set to empty string if no password is configured
DB_NAME = 'smartambulance'

def setup_database():
    """Initialize database and create all tables"""
    try:
        print('[DB] Connecting to MySQL Server...')
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Create database
        print(f'[DB] Creating database: {DB_NAME}')
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')
        cursor.execute(f'USE {DB_NAME}')
        
        # Create hospitals table
        print('[DB] Creating hospitals table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hospitals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                address VARCHAR(255),
                phone VARCHAR(20),
                email VARCHAR(100),
                total_beds INT DEFAULT 150,
                available_beds INT DEFAULT 150,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                specialties JSON,
                website VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ambulances table
        print('[DB] Creating ambulances table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ambulances (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ambulance_number VARCHAR(20) UNIQUE NOT NULL,
                type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Available',
                hospital_id INT,
                equipment JSON,
                last_service DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
            )
        ''')
        
        # Create drivers table
        print('[DB] Creating drivers table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(20) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                cnic VARCHAR(20),
                experience INT,
                shift VARCHAR(50),
                assigned_ambulance VARCHAR(20),
                status VARCHAR(50) DEFAULT 'Available',
                hospital_id INT,
                certifications JSON,
                license VARCHAR(50),
                profile_pic VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_ambulance) REFERENCES ambulances(ambulance_number)
            )
        ''')
        
        # Create patient_requests table
        print('[DB] Creating patient_requests table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(20) UNIQUE NOT NULL,
                patient_name VARCHAR(100),
                patient_phone VARCHAR(20),
                pickup_address VARCHAR(255),
                hospital_id INT,
                reason VARCHAR(255),
                priority VARCHAR(20),
                status VARCHAR(50) DEFAULT 'pending',
                assigned_driver_id INT,
                rejected_by JSON,
                locked BOOLEAN DEFAULT FALSE,
                locked_by INT,
                locked_at TIMESTAMP NULL,
                cancelled BOOLEAN DEFAULT FALSE,
                reassignment_count INT DEFAULT 0,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                age INT,
                symptoms TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_driver_id) REFERENCES drivers(id) ON DELETE SET NULL
            )
        ''')
        
        # Create dispatches table
        print('[DB] Creating dispatches table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dispatches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dispatch_id VARCHAR(30) UNIQUE NOT NULL,
                request_id VARCHAR(20),
                patient_name VARCHAR(100),
                patient_phone VARCHAR(20),
                location VARCHAR(255),
                driver_id INT,
                driver_name VARCHAR(100),
                ambulance_id VARCHAR(20),
                hospital_id INT,
                status VARCHAR(50),
                priority VARCHAR(20),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL,
                FOREIGN KEY (ambulance_id) REFERENCES ambulances(ambulance_number) ON DELETE SET NULL
            )
        ''')
        
        # Create users table
        print('[DB] Creating users table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                address VARCHAR(255),
                blood_type VARCHAR(10),
                medical_history TEXT,
                emergency_contacts JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create attendance_records table
        print('[DB] Creating attendance_records table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                driver_id INT NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Present',
                admin_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                leave_reason TEXT,
                admin_id INT,
                approved_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_attendance (driver_id, date),
                FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
                FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        
        # Create feedback table
        print('[DB] Creating feedback table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(50),
                patient_name VARCHAR(100),
                patient_phone VARCHAR(20),
                on_time ENUM('yes', 'no'),
                rating INT CHECK (rating >= 1 AND rating <= 5),
                driver_rating INT CHECK (driver_rating >= 1 AND driver_rating <= 5),
                comment LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES patient_requests(request_id) ON DELETE SET NULL,
                INDEX idx_request_id (request_id),
                INDEX idx_created_at (created_at)
            )
        ''')
        
        # Create admins table
        print('[DB] Creating admins table...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print('[DB] All tables created successfully')
        
        # Seed default admin account (always ensure one exists)
        cursor.execute('SELECT COUNT(*) FROM admins')
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin123')")
            conn.commit()
            print('[DB] \u2713 Seeded default admin (admin/admin123)')
        
        # Seed initial data
        print('[DB] Seeding database with demo data...')
        
        # Check if data already exists
        cursor.execute('SELECT COUNT(*) FROM hospitals')
        if cursor.fetchone()[0] > 0:
            print('[DB] Database already seeded with data')
            cursor.close()
            conn.close()
            return True
        
        # Seed hospitals
        hospitals = [
            ('hospital1', 'pass123', 'City General Hospital', '123 Medical Street, Dubai', '+971421234567', 
             'emergency@citygen.ae', 150, 150, 25.1972, 55.2744, '["Emergency Medicine", "Trauma Care", "Cardiology"]', 'www.citygenhospital.ae'),
            ('hospital2', 'pass123', 'Metro Medical Center', '456 Health Avenue, Dubai', '+971429876543',
             'emergency@metromedical.ae', 200, 200, 25.2165, 55.2659, '["General Medicine", "Orthopedics", "Pediatrics"]', 'www.metromedical.ae')
        ]
        
        hospital_ids = {}
        for h in hospitals:
            cursor.execute('''
                INSERT INTO hospitals (username, password, name, address, phone, email, total_beds, available_beds, latitude, longitude, specialties, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', h)
            hospital_ids[h[0]] = cursor.lastrowid
        print('[DB] ✓ Seeded 2 hospitals')
        
        # Seed ambulances
        ambulances = [
            ('SA-001', 'Advanced Life Support', 'Available', hospital_ids['hospital1'], '["Defibrillator", "Oxygen Tank", "Emergency Stretcher"]'),
            ('SA-002', 'Advanced Life Support', 'Available', hospital_ids['hospital1'], '["Defibrillator", "Oxygen Tank", "Emergency Stretcher"]'),
            ('SA-003', 'Basic Life Support', 'Available', hospital_ids['hospital2'], '["Oxygen Tank", "Emergency Stretcher", "First Aid Kit"]'),
            ('SA-004', 'Advanced Life Support', 'Available', hospital_ids['hospital2'], '["Defibrillator", "Oxygen Tank", "Emergency Stretcher", "Portable Monitor"]')
        ]
        
        for amb in ambulances:
            cursor.execute('''
                INSERT INTO ambulances (ambulance_number, type, status, hospital_id, equipment)
                VALUES (%s, %s, %s, %s, %s)
            ''', amb)
        print('[DB] ✓ Seeded 4 ambulances')
        
        # Seed drivers
        drivers = [
            ('DRV-001', 'pass123', 'Ahmed Al-Mansouri', '+971501234567', '12345-1234567-1', 8, 'Morning', 'SA-001', 'Available', hospital_ids['hospital1'], '["EMT-P", "BLS", "ACLS", "PALS"]', 'DRV-LIC-2026-001'),
            ('DRV-002', 'pass123', 'Fatima Al-Zaabi', '+971509876543', '98765-7654321-9', 5, 'Night', 'SA-002', 'Available', hospital_ids['hospital1'], '["EMT-P", "BLS", "ACLS"]', 'DRV-LIC-2026-002'),
            ('DRV-003', 'pass123', 'Mohammed Al-Ketbi', '+971505555555', '55555-5555555-5', 3, 'Morning', 'SA-003', 'Available', hospital_ids['hospital2'], '["EMT-B", "BLS", "First Aid"]', 'DRV-LIC-2026-003'),
            ('DRV-004', 'pass123', 'Sara Johnson', '+971507777777', '77777-7777777-7', 6, 'Night', 'SA-004', 'Available', hospital_ids['hospital2'], '["EMT-P", "BLS", "ACLS", "PALS"]', 'DRV-LIC-2026-004')
        ]
        
        for drv in drivers:
            cursor.execute('''
                INSERT INTO drivers (username, password, name, phone, cnic, experience, shift, assigned_ambulance, status, hospital_id, certifications, license)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', drv)
        print('[DB] ✓ Seeded 4 drivers (DRV-001 to DRV-004)')
        
        # Seed users
        users = [
            ('user1', 'pass123', 'Ahmed Hassan', 'ahmed@gmail.com', '+971501111111', 'Dubai, UAE', 'O+', 'Type 2 Diabetes', '[]'),
            ('user2', 'pass123', 'Sarah Johnson', 'sarah@gmail.com', '+971503333333', 'Abu Dhabi, UAE', 'A+', 'Hypertension', '[]')
        ]
        
        for usr in users:
            cursor.execute('''
                INSERT INTO users (username, password, name, email, phone, address, blood_type, medical_history, emergency_contacts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', usr)
        print('[DB] ✓ Seeded 2 users (user1, user2)')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'\n[SUCCESS] Database {DB_NAME} setup completed!')
        print('\n[CREDENTIALS] Demo Login Accounts:')
        print('  Hospital 1:')
        print('    Username: hospital1')
        print('    Password: pass123')
        print('  Hospital 2:')
        print('    Username: hospital2')
        print('    Password: pass123')
        print('  Drivers (DRV-001 to DRV-004):')
        print('    Password: pass123')
        print('  Users (user1, user2):')
        print('    Password: pass123')
        print('\n[NEXT] Start Flask app with: python app.py')
        print('       Access at: http://localhost:5000')
        
        return True
        
    except Error as e:
        print(f'[ERROR] {e}')
        return False

if __name__ == '__main__':
    print('=' * 60)
    print('SmartAmbulance - MySQL Database Setup')
    print('=' * 60)
    print(f'Host: {DB_HOST}')
    print(f'User: {DB_USER}')
    print(f'Database: {DB_NAME}')
    print('-' * 60)
    
    if setup_database():
        print('\n✓ Database setup completed successfully!')
    else:
        print('\n✗ Database setup failed. Check MySQL connection.')
