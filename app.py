"""
================================================
    SMARTAMBULANCE - FLASK APPLICATION (MySQL)
    AI-Driven Emergency Ambulance Routing System
    With Persistent MySQL Database Integration
================================================

Routes:
- / : Home page (landing)
- /emergency : Emergency dispatch endpoint
- /driver-login : Driver authentication
- /hospital-login : Hospital dashboard login
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from queue import Queue
import os
import threading
from dotenv import load_dotenv
load_dotenv()
import random
import json
import requests
import mysql.connector  # type: ignore
from mysql.connector import Error  # type: ignore
from utils.traffic_patterns import get_speed_for_hour, get_traffic_level
from services.dispatch_service import select_best_hospital
from services.maps_service import get_traffic_eta
from ai_engine import calculate_dispatch_score, predict_demand

# Initialize Flask Application with static folder configuration
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'smartambulance2024secretkey')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Global error handler: database unavailable → clean 503 instead of AttributeError crash
@app.errorhandler(RuntimeError)
def handle_db_error(e):
    msg = str(e)
    if 'Database unavailable' in msg or 'database' in msg.lower():
        print(f'[DB UNAVAILABLE] {msg}')
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Database unavailable. Please try again shortly.'}), 503
        return '<h2>Service temporarily unavailable. Database is offline.</h2>', 503
    raise e

# ==================== GOOGLE MAPS API CONFIGURATION ====================
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

@app.context_processor
def inject_maps_key():
    """Inject Google Maps API key into all templates automatically."""
    return {'GOOGLE_MAPS_KEY': GOOGLE_MAPS_API_KEY}

# ==================== DATABASE CONFIGURATION ====================
# Reads from environment variables — set these in Render dashboard
# For local dev, put them in your .env file (loaded above via dotenv)
DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_USER     = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME     = os.environ.get('DB_NAME', 'smartambulance')
DB_PORT     = int(os.environ.get('DB_PORT', 3306))

# Database connection pool
_db_pool = None

# Direct connection config (used as fallback when pool is exhausted)
# SSL enabled for Aiven — disabled automatically for localhost
_USE_SSL = DB_HOST != 'localhost'
_DB_CONFIG = dict(
    host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
    database=DB_NAME, port=DB_PORT, connection_timeout=10,
    ssl_disabled=not _USE_SSL,
    ssl_verify_cert=False,
    ssl_verify_identity=False,
)

def _init_pool():
    """Create the shared MySQL connection pool (pool_size=10)."""
    global _db_pool
    try:
        _db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name='smartambulance_pool',
            pool_size=10,
            pool_reset_session=True,
            **_DB_CONFIG
        )
        print('[DB] Connection pool initialized (size=10)')
    except Error as e:
        print(f'[DB ERROR] Pool init failed: {e}')
        _db_pool = None

def init_db_connection():
    """Legacy helper — kept for compatibility."""
    try:
        return mysql.connector.connect(**_DB_CONFIG)
    except Error as e:
        print(f'[DB ERROR] Connection failed: {e}')
        return None

def get_db():
    """Return a DB connection.
    Tries the pool first; falls back to a direct connection if the pool is
    exhausted or unavailable.  Never returns None — raises RuntimeError only
    when MySQL itself is unreachable.
    """
    global _db_pool
    # Try pool first
    if _db_pool is None:
        _init_pool()
    if _db_pool is not None:
        try:
            return _db_pool.get_connection()
        except mysql.connector.errors.PoolError:
            # Pool exhausted — fall through to direct connection
            print('[DB] Pool exhausted, using direct connection')
        except Error as e:
            # Pool broken (e.g. MySQL restarted) — rebuild it next call
            print(f'[DB] Pool error: {e}, falling back to direct connection')
            _db_pool = None
    # Fallback: direct connection (returned conn.close() actually closes it)
    try:
        conn = mysql.connector.connect(**_DB_CONFIG)
        return conn
    except Error as e:
        print(f'[DB ERROR] Direct connection failed: {e}')
        raise RuntimeError(f'Database unavailable: {e}') from e

def init_database():
    """Initialize database and create tables on first run"""
    try:
        # Connect without specifying database to create it
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Create database if not exists
        print('[DB] Creating database...')
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')
        cursor.execute(f'USE {DB_NAME}')
        
        # Hospitals table
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
                performance_score INT DEFAULT 75,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('[DB] Created hospitals table')

        # Add performance_score to existing hospitals table if missing
        try:
            cursor.execute('''
                ALTER TABLE hospitals
                ADD COLUMN IF NOT EXISTS performance_score INT DEFAULT 75
            ''')
            conn.commit()
            print('[DB] Ensured performance_score column exists in hospitals')
        except Exception:
            pass
        
        # Ambulances table
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
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
            )
        ''')
        print('[DB] Created ambulances table')
        
        # Drivers table
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
                hospital_username VARCHAR(50),
                certifications JSON,
                license VARCHAR(50),
                profile_pic VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
            )
        ''')
        print('[DB] Created drivers table')
        
        # Patient requests table
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
                assigned_driver VARCHAR(20),
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
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (assigned_driver_id) REFERENCES drivers(id)
            )
        ''')
        print('[DB] Created patient_requests table')
        
        # Dispatches table
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
                FOREIGN KEY (driver_id) REFERENCES drivers(id),
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (ambulance_id) REFERENCES ambulances(ambulance_number)
            )
        ''')
        print('[DB] Created dispatches table')
        
        # Status timeline table to track request status changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_timeline (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(20) NOT NULL,
                dispatch_id VARCHAR(30),
                old_status VARCHAR(50),
                new_status VARCHAR(50),
                action_by VARCHAR(50),
                action_type VARCHAR(50),
                driver_id INT,
                driver_name VARCHAR(100),
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES patient_requests(request_id),
                FOREIGN KEY (driver_id) REFERENCES drivers(id)
            )
        ''')
        print('[DB] Created status_timeline table')
        
        # Users table (public users)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                password VARCHAR(255),
                name VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20) UNIQUE,
                address VARCHAR(255),
                blood_type VARCHAR(10),
                medical_history TEXT,
                emergency_contacts JSON,
                cnic VARCHAR(20) UNIQUE,
                full_name VARCHAR(100),
                user_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        print('[DB] Created users table')
        
        # Add last_rejected_at column to drivers table if it doesn't exist
        try:
            cursor.execute(f"USE {DB_NAME}")
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'drivers' AND COLUMN_NAME = 'last_rejected_at' 
                AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                print('[DB] Adding last_rejected_at column to drivers table...')
                cursor.execute('''
                    ALTER TABLE drivers ADD COLUMN last_rejected_at TIMESTAMP NULL DEFAULT NULL
                ''')
                conn.commit()
                print('[DB] Added last_rejected_at column successfully')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add last_rejected_at column: {e}')
        
        # Add driver location tracking columns if they don't exist
        try:
            cursor.execute(f"USE {DB_NAME}")
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'drivers' AND COLUMN_NAME = 'current_latitude' 
                AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                print('[DB] Adding driver location tracking columns...')
                cursor.execute('''
                    ALTER TABLE drivers 
                    ADD COLUMN current_latitude DECIMAL(10,8) NULL,
                    ADD COLUMN current_longitude DECIMAL(11,8) NULL,
                    ADD COLUMN location_updated_at TIMESTAMP NULL
                ''')
                conn.commit()
                print('[DB] Added driver location tracking columns successfully')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add driver location columns: {e}')
        
        # Add auto_processed columns to patient_requests table if they don't exist
        try:
            cursor.execute(f"USE {DB_NAME}")
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'patient_requests' AND COLUMN_NAME = 'auto_processed' 
                AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                print('[DB] Adding auto_processed columns to patient_requests table...')
                cursor.execute('''
                    ALTER TABLE patient_requests 
                    ADD COLUMN auto_processed BOOLEAN DEFAULT FALSE,
                    ADD COLUMN auto_processed_at TIMESTAMP NULL DEFAULT NULL,
                    ADD COLUMN forwarded_from_hospital_id INT NULL DEFAULT NULL
                ''')
                conn.commit()
                print('[DB] Added auto_processed columns successfully')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add auto_processed columns: {e}')
        

            
            conn.commit()
            
            if cursor.rowcount > 0:
                print('[DB] Updated hospital coordinates from Dubai to Gujrat')
            else:
                print('[DB] Hospital coordinates already using Gujrat')
        except Error as e:
            print(f'[DB WARNING] Could not update hospital coordinates: {e}')
        
        # ===== ADD HOSPITAL PROFILE COLUMNS =====
        # Add hospital profile and verification columns if they don't exist
        profile_columns = [
            ('whatsapp', "VARCHAR(20)"),
            ('hospital_type', "VARCHAR(50) DEFAULT 'Private'"),
            ('gps_latitude', "DECIMAL(10,8)"),
            ('gps_longitude', "DECIMAL(11,8)"),
            ('general_beds', "INT DEFAULT 0"),
            ('icu_beds', "INT DEFAULT 0"),
            ('emergency_beds', "INT DEFAULT 0"),
            ('doctors_count', "INT DEFAULT 0"),
            ('nurses_count', "INT DEFAULT 0"),
            ('operating_hours', "JSON"),
            ('cover_photo', "VARCHAR(255)"),
            ('logo_photo', "VARCHAR(255)"),
            ('registration_certificate', "VARCHAR(255)"),
            ('is_verified', "BOOLEAN DEFAULT FALSE")
        ]
        
        for col_name, col_def in profile_columns:
            try:
                cursor.execute(f"USE {DB_NAME}")
                cursor.execute('''
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'hospitals' AND COLUMN_NAME = %s 
                    AND TABLE_SCHEMA = %s
                ''', (col_name, DB_NAME))
                if not cursor.fetchone():
                    print(f'[DB] Adding hospital column: {col_name}')
                    cursor.execute(f'''
                        ALTER TABLE hospitals ADD COLUMN {col_name} {col_def}
                    ''')
                    conn.commit()
                    print(f'[DB] Added {col_name} successfully')
            except Error as e:
                if 'Duplicate column name' not in str(e):
                    print(f'[DB WARNING] Could not add {col_name}: {e}')
        
        # ===== Anti-spam: blacklist table =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INT AUTO_INCREMENT PRIMARY KEY,
                phone VARCHAR(20) UNIQUE NOT NULL,
                reason VARCHAR(255),
                blocked_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('[DB] Ensuring blacklist table exists')

        # ===== System settings table =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(50) UNIQUE,
                setting_value VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("""
            INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES
            ('emergency_timeout', '10'),
            ('max_distance', '50')
        """)
        conn.commit()
        print('[DB] Ensuring system_settings table exists')

        # ===== Anti-spam: ip_address column on patient_requests =====
        try:
            cursor.execute(f'USE {DB_NAME}')
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'patient_requests' AND COLUMN_NAME = 'ip_address'
                AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute(
                    'ALTER TABLE patient_requests ADD COLUMN ip_address VARCHAR(45) NULL'
                )
                conn.commit()
                print('[DB] Added ip_address column to patient_requests')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add ip_address column: {e}')

        # ===== Hospital approval status column =====
        try:
            cursor.execute(f'USE {DB_NAME}')
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'hospitals' AND COLUMN_NAME = 'status' AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE hospitals ADD COLUMN status ENUM('pending','approved','rejected') DEFAULT 'approved'")
                cursor.execute("UPDATE hospitals SET status = 'approved'")
                conn.commit()
                print('[DB] Added status column to hospitals')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add status column: {e}')

        # ===== Hospital rejection reason column =====
        try:
            cursor.execute(f'USE {DB_NAME}')
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'hospitals' AND COLUMN_NAME = 'rejection_reason' AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE hospitals ADD COLUMN rejection_reason VARCHAR(255) NULL")
                conn.commit()
                print('[DB] Added rejection_reason column to hospitals')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add rejection_reason column: {e}')

        # ===== Hospital registration fields (added for self-registration) =====
        for _col, _def in [
            ('registration_number', 'VARCHAR(100)'),
            ('contact_name',        'VARCHAR(100)'),
        ]:
            try:
                cursor.execute(f'USE {DB_NAME}')
                cursor.execute('''
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'hospitals' AND COLUMN_NAME = %s AND TABLE_SCHEMA = %s
                ''', (_col, DB_NAME))
                if not cursor.fetchone():
                    cursor.execute(f'ALTER TABLE hospitals ADD COLUMN {_col} {_def}')
                    conn.commit()
                    print(f'[DB] Added {_col} column to hospitals')
            except Error as e:
                if 'Duplicate column name' not in str(e):
                    print(f'[DB WARNING] Could not add {_col}: {e}')

        # ===== Hospital is_locked column =====
        try:
            cursor.execute(f'USE {DB_NAME}')
            cursor.execute('''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'hospitals' AND COLUMN_NAME = 'is_locked' AND TABLE_SCHEMA = %s
            ''', (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE hospitals ADD COLUMN is_locked TINYINT(1) NOT NULL DEFAULT 0")
                conn.commit()
                print('[DB] Added is_locked column to hospitals')
        except Error as e:
            if 'Duplicate column name' not in str(e):
                print(f'[DB WARNING] Could not add is_locked column: {e}')

        conn.commit()
        cursor.close()
        conn.close()
        
        # Seed database with initial data
        seed_database()
        
        print('[DB] Database initialized successfully')
        return True
        
    except Error as e:
        print(f'[DB ERROR] Database initialization failed: {e}')
        return False

def seed_database():
    """Seed database with demo data on first run"""
    try:
        conn = get_db()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Check if hospitals already exist
        cursor.execute('SELECT COUNT(*) FROM hospitals')
        if cursor.fetchone()[0] > 0:
            print('[DB] Database already seeded')
            cursor.close()
            conn.close()
            return True
        
        # Seed hospitals with Gujrat, Punjab, Pakistan coordinates
        hospitals_data = []
        
        hospital_ids = {}
        for h in hospitals_data:
            cursor.execute('''
                INSERT INTO hospitals (username, password, name, address, phone, email, total_beds, available_beds, latitude, longitude, specialties, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', h)
            hospital_ids[h[0]] = cursor.lastrowid
        
        print('[DB] Seeded hospitals')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print('[DB] Database seeding completed')
        return True
        
    except Error as e:
        print(f'[DB ERROR] Seeding failed: {e}')
        return False

# Initialize database on startup (only in main process, not during Flask reloads)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or __name__ == '__main__':
    init_database()
    
    # Initialise the shared connection pool immediately after DB is ready
    _init_pool()
    
    # Test database connection on startup
    try:
        _test_conn = get_db()
        print('[DATABASE] Connected successfully!')
        _test_conn.close()
    except Exception as e:
        print(f'[DATABASE ERROR] {e}')

# ==================== PERFORMANCE OPTIMIZATIONS ====================
@app.after_request
def add_header(response):
    """Add caching and compression headers for better performance"""
    if response.content_type and ('javascript' in response.content_type or 
                                   'css' in response.content_type or
                                   'image' in response.content_type or
                                   'font' in response.content_type):
        response.cache_control.max_age = 2592000
        response.cache_control.public = True
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    return response

# Thread-safe lock for request operations
request_lock = threading.Lock()

# ==================== DATABASE HELPER FUNCTIONS ====================

def get_hospital_by_username(username):
    """Get hospital info by username"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM hospitals WHERE username = %s', (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_hospital_by_username: {e}')
        return None

def get_hospital_by_id(hospital_id):
    """Get hospital info by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM hospitals WHERE id = %s', (hospital_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_hospital_by_id: {e}')
        return None

def get_driver_by_username(username):
    """Get driver info by DRV-xxx username"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM drivers WHERE username = %s', (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_driver_by_username: {e}')
        return None

def get_driver_by_id(driver_id):
    """Get driver info by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM drivers WHERE id = %s', (driver_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_driver_by_id: {e}')
        return None

def get_user_by_username(username):
    """Get user info by username"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_user_by_username: {e}')
        return None

def get_patient_request_by_id(request_id):
    """Get patient request by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM patient_requests WHERE request_id = %s', (request_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_patient_request_by_id: {e}')
        return None

def get_ambulance_by_number(ambulance_number):
    """Get ambulance info by number"""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM ambulances WHERE ambulance_number = %s', (ambulance_number,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f'[DB ERROR] get_ambulance_by_number: {e}')
        return None

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two lat/lng points using Haversine formula"""
    import math
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(dlng/2) * math.sin(dlng/2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

# ==================== HOME ROUTE ====================
@app.route('/')
def home():
    """Render the home/landing page"""
    return render_template('index.html')

# ==================== ANTI-SPAM HELPERS ====================

def validate_phone_pk(phone):
    """Validate Pakistani mobile number: 11 digits starting with 03, not all-same."""
    if not phone or str(phone).strip() in ('', 'Not Provided', 'N/A'):
        return False, 'A valid phone number is required'
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if len(digits) != 11:
        return False, 'Phone number must be exactly 11 digits'
    if not digits.startswith('03'):
        return False, 'Phone number must start with 03 (Pakistani mobile format)'
    if len(set(digits)) == 1:
        return False, 'Phone number cannot consist of all the same digit'
    return True, None


def get_system_setting(key, default=None):
    """Fetch a value from system_settings table."""
    try:
        conn = get_db()
        if not conn:
            return default
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('SELECT setting_value FROM system_settings WHERE setting_key = %s', (key,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['setting_value'] if row else default
    except Exception:
        return default


def auto_cancel_timed_out_requests():
    """Mark pending requests older than emergency_timeout minutes as cancelled."""
    try:
        timeout_minutes = int(get_system_setting('emergency_timeout', '10') or 10)
        conn = get_db()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute(
            "UPDATE patient_requests SET status = 'cancelled', cancelled = 1 "
            "WHERE status = 'pending' "
            "AND (cancelled IS NULL OR cancelled = 0) "
            "AND TIMESTAMPDIFF(MINUTE, timestamp, NOW()) >= %s",
            (timeout_minutes,)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f'[AUTO-CANCEL] {e}')


def check_blacklist_db(phone):
    """Return (True, reason) if phone is blacklisted, else (False, None)."""
    try:
        conn = get_db()
        if not conn:
            return False, None
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('SELECT reason FROM blacklist WHERE phone = %s', (str(phone).strip(),))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return True, row.get('reason') or 'Blacklisted by administrator'
        return False, None
    except Exception:
        return False, None


def check_rate_limit_db(ip_address):
    """Return (True, wait_minutes) if IP sent a request within the last 5 minutes."""
    try:
        if not ip_address or ip_address in ('0.0.0.0', '127.0.0.1', '::1'):
            return False, 0
        conn = get_db()
        if not conn:
            return False, 0
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute(
            'SELECT MAX(timestamp) AS last_ts FROM patient_requests '
            'WHERE ip_address = %s AND timestamp >= %s',
            (ip_address, datetime.now() - timedelta(minutes=5))
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and row['last_ts']:
            elapsed = (datetime.now() - row['last_ts']).total_seconds()
            remaining = 300 - elapsed
            if remaining > 0:
                return True, max(1, int(remaining / 60) + (1 if int(remaining) % 60 > 0 else 0))
        return False, 0
    except Exception:
        return False, 0


def check_duplicate_active_request(phone):
    """Return True if this phone already has an active (non-terminal) request."""
    try:
        if not phone or str(phone).strip() in ('', 'Not Provided', 'N/A'):
            return False
        conn = get_db()
        if not conn:
            return False
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute(
            "SELECT request_id FROM patient_requests "
            "WHERE patient_phone = %s "
            "  AND status IN ('pending','accepted','assigned','en_route','picked_up') "
            "  AND (cancelled IS NULL OR cancelled = 0) "
            "LIMIT 1",
            (str(phone).strip(),)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row is not None
    except Exception:
        return False


# ==================== EMERGENCY ROUTE ====================
@app.route('/emergency', methods=['GET', 'POST'])
def emergency():
    """Handle emergency dispatch request"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Step 1: Receive patient's real GPS coordinates
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            # If coordinates are missing, return error - do not use any fallback or default
            if latitude is None or longitude is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Patient GPS coordinates are required for emergency'
                }), 400
            
            # Convert to float for calculations
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (ValueError, TypeError):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid GPS coordinates format'
                }), 400
            
            # Anti-spam: Validate location is not (0,0) or invalid
            if abs(latitude) < 0.0001 and abs(longitude) < 0.0001:
                return jsonify({'status': 'error',
                    'message': 'Valid location is required for emergency dispatch'}), 400
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return jsonify({'status': 'error',
                    'message': 'Valid location is required for emergency dispatch'}), 400

            # Anti-spam: IP rate limiting (1 request per 5 minutes per IP)
            client_ip = request.remote_addr or '0.0.0.0'
            rate_limited, wait_minutes = check_rate_limit_db(client_ip)
            if rate_limited:
                return jsonify({'status': 'error',
                    'message': f'Please wait {wait_minutes} minute(s) before sending another request'}), 429

            # Additional patient info (optional)
            accuracy = data.get('accuracy')
            location_method = data.get('location_method', 'gps')
            patient_name = data.get('patient_name', 'Anonymous Patient')
            patient_phone = data.get('patient_phone', 'Not Provided')

            # Anti-spam: Phone number validation
            phone_valid, phone_err = validate_phone_pk(patient_phone)
            if not phone_valid:
                return jsonify({'status': 'error', 'message': phone_err}), 400

            # Anti-spam: Blacklist check
            blacklisted, _bl_reason = check_blacklist_db(patient_phone)
            if blacklisted:
                return jsonify({'status': 'error',
                    'message': 'This phone number is restricted from using the service'}), 403

            # Anti-spam: Duplicate active request
            if check_duplicate_active_request(patient_phone):
                return jsonify({'status': 'error',
                    'message': 'You already have an active emergency request. Please wait for it to complete.'}), 409

            location_info = f'{latitude:.4f}, {longitude:.4f}'
            if accuracy:
                location_info += f' (±{accuracy:.1f}m)'
            print(f'[EMERGENCY] Patient at {location_info} ({location_method})')
            
            # Step 2: Query hospitals table from MySQL - get all hospitals with lat/lng
            conn = get_db()
            if not conn:
                return jsonify({
                    'status': 'error',
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT h.id, h.name, h.address, h.phone, h.latitude, h.longitude,
                       h.available_beds, h.total_beds
                FROM hospitals h
                WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL
                  AND COALESCE(h.status, 'approved') = 'approved'
                  AND EXISTS (
                      SELECT 1 FROM ambulances a WHERE a.hospital_id = h.id
                  )
            ''')
            all_hospitals = cursor.fetchall()
            cursor.close()
            
            if not all_hospitals:
                conn.close()
                return jsonify({
                    'status': 'error',
                    'message': 'No hospitals found in the system'
                }), 400
            
            # Step 3: Calculate road distance + ETA via Google Maps for each hospital
            # Falls back to Haversine if API is unavailable
            hospital_distances = []
            for hospital in all_hospitals:
                maps = get_traffic_eta(
                    latitude, longitude,
                    float(hospital['latitude']), float(hospital['longitude'])
                )

                hospital_distances.append({
                    'hospital_id': hospital['id'],
                    'name': hospital['name'],
                    'address': hospital['address'],
                    'phone': hospital['phone'],
                    'latitude': float(hospital['latitude']),
                    'longitude': float(hospital['longitude']),
                    'available_beds': hospital['available_beds'],
                    'total_beds': hospital['total_beds'],
                    'distance_km': round(maps['distance_km'], 2),
                    'eta_minutes': maps['eta_minutes'],
                    'traffic': maps['traffic'],
                })
            
            # Step 4: Filter by max_distance setting, then split
            _max_dist = float(get_system_setting('max_distance', '50') or 50)
            hospital_distances = [h for h in hospital_distances if h['distance_km'] <= _max_dist]

            registered_hospitals = [h for h in hospital_distances if h['available_beds'] > 0]
            unregistered_hospitals = [h for h in hospital_distances if h['available_beds'] == 0]
            
            # Sort both lists by ETA (fastest first), distance as tiebreaker
            registered_hospitals.sort(key=lambda x: (x['eta_minutes'], x['distance_km']))
            unregistered_hospitals.sort(key=lambda x: (x['eta_minutes'], x['distance_km']))
            
            # Step 5: Auto-select fastest (lowest ETA) registered hospital server-side (index 0)
            selected_hospital = None
            selected_hospital_id = None
            
            if registered_hospitals:
                selected_hospital = registered_hospitals[0]
                selected_hospital_id = selected_hospital['hospital_id']
            elif unregistered_hospitals:
                # If no registered hospitals, use nearest unregistered as fallback
                selected_hospital = unregistered_hospitals[0]
                selected_hospital_id = selected_hospital['hospital_id']
            else:
                conn.close()
                return jsonify({
                    'status': 'error',
                    'message': 'No suitable hospitals found'
                }), 400
            
            # Step 6: Create patient_requests record with auto-selected hospital
            request_id = f'REQ-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            emergency_id = f'EMG-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO patient_requests 
                (request_id, patient_name, patient_phone, pickup_address, hospital_id, 
                 reason, priority, status, latitude, longitude, timestamp, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_id, 
                patient_name, 
                patient_phone, 
                f'{latitude:.4f}, {longitude:.4f}',
                selected_hospital_id,
                'Emergency Call',
                'High',
                'pending',
                latitude,
                longitude,
                datetime.now(),
                client_ip
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f'[EMERGENCY ALERT] {emergency_id} - Auto-selected hospital: {selected_hospital["name"]} (ID: {selected_hospital_id})')
            print(f'[PATIENT REQUEST] Created {request_id} - Lat: {latitude:.4f}, Lng: {longitude:.4f}')
            
            # Return both lists to frontend
            emergency_data = {
                'status': 'success',
                'message': 'Emergency request received and nearest hospital auto-selected',
                'emergency_id': emergency_id,
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'patient_coordinates': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'accuracy_meters': accuracy,
                    'method': location_method
                },
                'auto_selected_hospital': {
                    'hospital_id': selected_hospital['hospital_id'],
                    'name': selected_hospital['name'],
                    'address': selected_hospital['address'],
                    'phone': selected_hospital['phone'],
                    'latitude': selected_hospital['latitude'],
                    'longitude': selected_hospital['longitude'],
                    'available_beds': selected_hospital['available_beds'],
                    'distance_km': selected_hospital['distance_km'],
                    'eta_minutes': selected_hospital['eta_minutes']
                },
                'nearby_hospitals': {
                    'registered': registered_hospitals,
                    'unregistered': unregistered_hospitals
                }
            }
            
            return jsonify(emergency_data), 200
            
        except Exception as e:
            print(f'[EMERGENCY ERROR] {str(e)}')
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    return render_template('emergency.html',
        patient_name=session.get('patient_name', ''),
        patient_phone=session.get('patient_phone', ''))

@app.route('/dispatch', methods=['POST'])
def dispatch():
    """
    AI-powered ambulance dispatch using calculate_dispatch_score() from ai_engine.py.

    Selection pipeline:
      1. Validate patient GPS coordinates + anti-spam checks
      2. If forced_hospital_id provided by frontend, use that hospital directly
      3. Otherwise: query every available driver (status='Available', has ambulance)
         and for each driver gather 5 factors:
           - distance (Haversine from ambulance/hospital to patient)
           - hour of day (traffic congestion)
           - ambulance fleet load at that hospital
           - hospital bed availability
           - driver's historical average response time
      4. Call calculate_dispatch_score() for each candidate
      5. Select the driver with the LOWEST total_score (best candidate)
      6. Create patient_request record and return enriched AI decision response
    """
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()

        # -- Validate patient GPS coordinates --
        try:
            lat = float(data.get('lat'))
            lng = float(data.get('lng'))
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'Invalid GPS coordinates'}), 400

        if abs(lat) < 0.0001 and abs(lng) < 0.0001:
            return jsonify({'status': 'error',
                'message': 'Valid location is required for emergency dispatch'}), 400
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({'status': 'error',
                'message': 'Valid location is required for emergency dispatch'}), 400

        # -- Anti-spam: IP rate limiting --
        client_ip = request.remote_addr or '0.0.0.0'
        rate_limited, wait_minutes = check_rate_limit_db(client_ip)
        if rate_limited:
            return jsonify({'status': 'error',
                'message': f'Please wait {wait_minutes} minute(s) before sending another request'}), 429

        # -- Patient identity: request body first, then session fallback --
        user_type = session.get('user_type', '')
        patient_name  = (data.get('name') or
                         data.get('patient_name') or
                         (session.get('patient_name') if user_type in ('patient', 'user') else None) or
                         (session.get('name') if user_type in ('patient', 'user') else None) or
                         'Guest Patient')
        patient_phone = (data.get('phone') or
                         data.get('patient_phone') or
                         (session.get('patient_phone') if user_type in ('patient', 'user') else None) or
                         'Not Provided')

        # -- Anti-spam: blacklist + duplicate active request --
        if patient_phone not in ('Not Provided', 'N/A', ''):
            blacklisted, _ = check_blacklist_db(patient_phone)
            if blacklisted:
                return jsonify({'status': 'error',
                    'message': 'This phone number is restricted from using the service'}), 403
            if check_duplicate_active_request(patient_phone):
                return jsonify({'status': 'error',
                    'message': 'You already have an active emergency request. Please wait for it to complete.'}), 409

        request_id   = f'REQ-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        current_hour = datetime.now().hour
        current_speed = get_speed_for_hour(current_hour)
        day_of_week  = datetime.now().weekday()     # 0=Monday … 6=Sunday
        demand_level = predict_demand(current_hour, day_of_week)

        # -- Optional: frontend explicitly forces a specific hospital --
        forced_hospital_id = data.get('forced_hospital_id')

        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # ================================================================
        # FORCED HOSPITAL PATH  (user selected from map, skip AI scoring)
        # ================================================================
        if forced_hospital_id:
            cursor.execute('''
                SELECT id, name, address, latitude, longitude,
                       COALESCE(available_beds, 0)  AS available_beds,
                       COALESCE(total_beds, 0)       AS total_beds
                FROM hospitals
                WHERE id = %s AND latitude IS NOT NULL AND longitude IS NOT NULL
                AND COALESCE(status, 'approved') = 'approved'
            ''', (forced_hospital_id,))
            forced_hospital = cursor.fetchone()

            if forced_hospital:
                hosp_lat    = float(forced_hospital['latitude'])
                hosp_lng    = float(forced_hospital['longitude'])
                # Use real Google Maps API for traffic-aware ETA
                maps_result = get_traffic_eta(hosp_lat, hosp_lng, lat, lng)
                distance_km = maps_result['distance_km']
                eta_minutes = maps_result['eta_minutes']
                traffic_level = maps_result['traffic']

                # Find an available driver at the forced hospital (for optimistic response display only)
                cursor.execute('''
                    SELECT d.id, d.name, d.phone, d.assigned_ambulance
                    FROM drivers d
                    WHERE d.hospital_id = %s AND d.status = 'Available'
                    AND d.assigned_ambulance IS NOT NULL
                    LIMIT 1
                ''', (forced_hospital_id,))
                avail_driver = cursor.fetchone()
                # NOTE: Do NOT fall back to AI selection when no driver is available.
                # The user explicitly chose this hospital — the request must go there.
                # The hospital admin will assign a driver manually from their dashboard.

            if forced_hospital:
                cursor.execute('''
                    INSERT INTO patient_requests
                    (request_id, patient_name, patient_phone, pickup_address, hospital_id,
                     reason, priority, status, latitude, longitude, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (request_id, patient_name, patient_phone,
                      f'{lat:.4f}, {lng:.4f}', forced_hospital_id,
                      'Emergency Call', 'High', 'pending', lat, lng, client_ip))
                conn.commit()

                # Broadcast new emergency to hospital via SSE (real-time alert)
                broadcast_to_hospital(forced_hospital_id, 'new_emergency', {
                    'request_id': request_id,
                    'patient_name': patient_name,
                    'patient_phone': patient_phone,
                    'latitude': lat,
                    'longitude': lng,
                    'message': 'New emergency request (user-selected hospital)'
                })

                cursor.close()
                conn.close()

                print(f'[DISPATCH FORCED] Hospital: {forced_hospital["name"]} | '
                      f'Request: {request_id}')

                return jsonify({
                    'success': True,
                    'status': 'success',
                    'message': 'Ambulance dispatch initiated (hospital manually selected)',
                    'request_id': request_id,
                    'hospital_name': forced_hospital['name'],
                    'hospital_id': forced_hospital_id,
                    'ambulance': {
                        'id': avail_driver['id'] if avail_driver else None,
                        'driver_name': avail_driver['name'] if avail_driver else 'Assigning…',
                        'driver_phone': avail_driver['phone'] if avail_driver else '',
                        'plate_number': avail_driver['assigned_ambulance'] if avail_driver else '',
                        'hospital_name': forced_hospital['name'],
                    },
                    'eta_minutes': eta_minutes,
                    'ai_decision': {
                        'score': None,
                        'reason': 'Hospital manually selected by user',
                        'demand_level': demand_level,
                        'factors': {
                            'distance_km': round(distance_km, 3),
                            'distance_score': None,
                            'time_score': None,
                            'ambulance_load_score': None,
                            'bed_availability_score': None,
                            'driver_history_score': None,
                        },
                    },
                    'timestamp': datetime.now().isoformat(),
                }), 200

            else:
                # Forced hospital not found — fall through to AI selection
                cursor.close()
                conn.close()
                print(f'[DISPATCH ERROR] Forced hospital {forced_hospital_id} not found in DB')
                return jsonify({
                    'success': False,
                    'status': 'error',
                    'message': 'Selected hospital not found. Please try again.',
                }), 200

        # ================================================================
        # AI SCORING PATH — same ETA-based logic as /nearest-hospitals
        # ================================================================

        from math import radians, sin, cos, sqrt, atan2

        def haversine_eta(lat1, lng1, lat2, lng2):
            R = 6371
            lat1, lng1, lat2, lng2 = map(radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlng/2)**2
            dist = R * 2 * atan2(sqrt(a), sqrt(1 - a))
            return max(1, round((dist / 30) * 60)), round(dist, 2)

        # Step 1: Approved hospitals with ≥1 available driver and beds > 0
        cursor.execute("""
            SELECT h.id, h.name, h.latitude, h.longitude,
                   COALESCE(h.available_beds, 0) AS available_beds,
                   COALESCE(h.total_beds, 0)     AS total_beds,
                   COUNT(d.id) AS driver_count
            FROM hospitals h
            JOIN drivers d ON d.hospital_id = h.id
                AND d.status = 'Available'
                AND d.assigned_ambulance IS NOT NULL
            WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL
              AND COALESCE(h.status, 'approved') = 'approved'
              AND COALESCE(h.available_beds, 0) > 0
            GROUP BY h.id
            HAVING driver_count > 0
        """)
        hospitals_with_drivers = cursor.fetchall()

        # Fallback: if every hospital has 0 beds, include them anyway
        if not hospitals_with_drivers:
            cursor.execute("""
                SELECT h.id, h.name, h.latitude, h.longitude,
                       COALESCE(h.available_beds, 0) AS available_beds,
                       COALESCE(h.total_beds, 0)     AS total_beds,
                       COUNT(d.id) AS driver_count
                FROM hospitals h
                JOIN drivers d ON d.hospital_id = h.id
                    AND d.status = 'Available'
                    AND d.assigned_ambulance IS NOT NULL
                WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL
                  AND COALESCE(h.status, 'approved') = 'approved'
                GROUP BY h.id
                HAVING driver_count > 0
            """)
            hospitals_with_drivers = cursor.fetchall()

        if not hospitals_with_drivers:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'status': 'error',
                'message': 'All ambulances are currently busy. Please wait or call emergency services directly.',
                'demand_level': demand_level,
            }), 200

        # Step 2: Calculate ETA for each hospital and sort ascending (lowest ETA first)
        hospital_scores = []
        for h in hospitals_with_drivers:
            eta, dist = haversine_eta(h['latitude'], h['longitude'], lat, lng)
            hospital_scores.append({
                'hospital':    h,
                'eta_minutes': eta,
                'distance_km': dist,
            })
            print(f"[DISPATCH] {h['name']}: {dist}km, {eta}min, "
                  f"beds={h['available_beds']}, drivers={h['driver_count']}")

        hospital_scores.sort(key=lambda x: (x['eta_minutes'], x['distance_km']))
        hospital_scores = hospital_scores[:6]  # Only consider top 6 nearest hospitals (same as /nearest-hospitals)
        best_data    = hospital_scores[0]
        best_hospital = best_data['hospital']
        eta_minutes   = best_data['eta_minutes']
        distance_km   = best_data['distance_km']
        hospital_id   = best_hospital['id']

        print(f"[SELECTED] {best_hospital['name']} - ETA: {eta_minutes}min, dist: {distance_km}km")

        # Step 3: Pick one available driver from the winning hospital
        cursor.execute("""
            SELECT id AS driver_id, name AS driver_name,
                   phone AS driver_phone, assigned_ambulance AS plate_number,
                   hospital_id
            FROM drivers
            WHERE hospital_id = %s AND status = 'Available'
              AND assigned_ambulance IS NOT NULL
            LIMIT 1
        """, (hospital_id,))
        best_driver = cursor.fetchone()

        if not best_driver:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'status': 'error',
                'message': 'No driver available at selected hospital. Please try again.',
            }), 200

        # Step 4: Persist patient request
        cursor.execute('''
            INSERT INTO patient_requests
            (request_id, patient_name, patient_phone, pickup_address, hospital_id,
             reason, priority, status, latitude, longitude, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (request_id, patient_name, patient_phone,
              f'{lat:.4f}, {lng:.4f}', hospital_id,
              'Emergency Call', 'High', 'pending', lat, lng, client_ip))

        conn.commit()
        cursor.close()
        conn.close()

        # Broadcast to hospital via SSE
        broadcast_to_hospital(hospital_id, 'new_emergency', {
            'request_id':   request_id,
            'patient_name': patient_name,
            'patient_phone': patient_phone,
            'latitude':     lat,
            'longitude':    lng,
            'message':      'New emergency request',
        })

        print(f'[AI DISPATCH] Request {request_id} | '
              f'Driver: {best_driver["driver_name"]} | '
              f'Hospital: {best_hospital["name"]} | '
              f'ETA: {eta_minutes}min | '
              f'Demand: {demand_level}')

        # Step 5: Return response
        return jsonify({
            'success': True,
            'status': 'success',
            'message': 'Ambulance dispatch initiated — selected by AI (lowest ETA)',
            'request_id': request_id,
            'ambulance': {
                'id':           best_driver['driver_id'],
                'driver_name':  best_driver['driver_name'],
                'driver_phone': best_driver['driver_phone'] or '',
                'plate_number': best_driver['plate_number'] or '',
                'hospital_name': best_hospital['name'],
            },
            'eta_minutes': eta_minutes,
            'ai_decision': {
                'score':        None,
                'reason':       f"Lowest ETA: {eta_minutes} min ({distance_km} km)",
                'demand_level': demand_level,
                'factors': {
                    'distance_km': distance_km,
                    'eta_minutes': eta_minutes,
                },
            },
            # Legacy fields — kept for frontend compatibility
            'hospital_name':  best_hospital['name'],
            'hospital_id':    hospital_id,
            'distance_km':    distance_km,
            'traffic_level':  get_traffic_level(current_hour),
            'dispatch_score': None,
            'is_registered':  True,
            'timestamp':      datetime.now().isoformat(),
        }), 200

    except Exception as e:
        print(f'[DISPATCH ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 400

# ==================== TRACK AMBULANCE ====================
@app.route('/track')
def track_ambulance():
    """Patient/Public-facing ambulance tracking page"""
    return render_template('track.html')

# ==================== DRIVER LOGIN ROUTE ====================
@app.route('/driver-login', methods=['GET', 'POST'])
def driver_login():
    """Handle driver authentication and login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        hospital_id = request.form.get('hospital_id', '').strip()
        
        # Validate all fields are present
        if not username or not password or not hospital_id:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id, name FROM hospitals')
            hospitals = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('driver_login.html', 
                                   error='All fields are required',
                                   hospitals=hospitals)
        
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            
            # Query database for driver with hospital_id
            cursor.execute('SELECT * FROM drivers WHERE username = %s AND password = %s AND hospital_id = %s', 
                          (username, password, hospital_id))
            driver = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if driver:
                session.permanent = True
                session['user_type'] = 'driver'
                session['username'] = username
                session['driver_username'] = username
                session['driver_id'] = driver['id']
                session['name'] = driver['name']
                session['ambulance'] = driver['assigned_ambulance']
                session['hospital_id'] = int(hospital_id)
                session.modified = True
                
                print(f'[DRIVER LOGIN] Success: {username} (Hospital:{hospital_id})')
                print(f'[DRIVER LOGIN] Session after login: {dict(session)}')
                
                # Create response with proper session handling
                response = make_response(redirect(url_for('driver_dashboard')))
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            else:
                # Get hospitals for re-display
                conn = get_db()
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT id, name FROM hospitals')
                hospitals = cursor.fetchall()
                cursor.close()
                conn.close()
                
                return render_template('driver_login.html', 
                                       error='Invalid credentials',
                                       hospitals=hospitals)
        
        except Exception as e:
            print(f'[DRIVER LOGIN ERROR] {str(e)}')
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id, name FROM hospitals')
            hospitals = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('driver_login.html', error='Login error. Please try again.', hospitals=hospitals)
    
    # GET request - show login form with hospitals list
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name FROM hospitals')
        hospitals = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('driver_login.html', hospitals=hospitals)
    
    except Exception as e:
        print(f'[DRIVER LOGIN ERROR] {str(e)}')
        return render_template('driver_login.html', error='Error loading page', hospitals=[])

# ==================== DRIVER DASHBOARD ====================
@app.route('/driver-dashboard')
def driver_dashboard():
    """Display driver dashboard (requires authentication)"""
    if 'user_type' not in session or session['user_type'] != 'driver':
        return redirect(url_for('driver_login'))
    
    driver_username = session.get('driver_username') or session.get('username')
    print(f'[DRIVER DASHBOARD] Loading for: {driver_username}')
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get driver info with hospital name + GPS via JOIN
        cursor.execute('''
            SELECT d.*, h.name as hospital_name, h.latitude as hospital_lat, h.longitude as hospital_lng
            FROM drivers d 
            LEFT JOIN hospitals h ON d.hospital_id = h.id 
            WHERE d.username = %s
        ''', (driver_username,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            print(f'[DRIVER DASHBOARD] Driver not found: {driver_username}')
            return redirect(url_for('driver_login'))
        
        # Find active assignment
        cursor.execute('''
            SELECT * FROM patient_requests 
            WHERE assigned_driver = %s AND status NOT IN ('completed', 'rejected', 'pending')
            LIMIT 1
        ''', (driver_username,))
        active_assignment = cursor.fetchone()

        # Attach dispatch_id to active_assignment so the template can pass it to updateStatus()
        if active_assignment:
            # Primary: find active dispatch for this driver + request
            cursor.execute('''
                SELECT dispatch_id FROM dispatches
                WHERE request_id = %s AND driver_id = %s
                  AND status NOT IN ('driver_rejected', 'completed')
                ORDER BY timestamp DESC LIMIT 1
            ''', (active_assignment['request_id'], driver['id']))
            disp_row = cursor.fetchone()

            # Fallback: any dispatch for this driver+request (handles edge case where
            # dispatch was auto-marked rejected while trip was already in progress)
            if not disp_row:
                cursor.execute('''
                    SELECT dispatch_id FROM dispatches
                    WHERE request_id = %s AND driver_id = %s
                    ORDER BY timestamp DESC LIMIT 1
                ''', (active_assignment['request_id'], driver['id']))
                disp_row = cursor.fetchone()
                # If we found it via fallback, restore its status to match the trip
                if disp_row:
                    trip_status = active_assignment.get('status', 'en_route')
                    if trip_status not in ('driver_rejected', 'completed'):
                        cursor.execute(
                            'UPDATE dispatches SET status=%s WHERE dispatch_id=%s',
                            (trip_status, disp_row['dispatch_id'])
                        )

            if disp_row:
                active_assignment['dispatch_id'] = disp_row['dispatch_id']
        
        # Count completed trips today
        cursor.execute('''
            SELECT COUNT(*) as count FROM patient_requests 
            WHERE assigned_driver = %s AND status = 'completed' 
            AND DATE(timestamp) = CURDATE()
        ''', (driver_username,))
        completed_today = cursor.fetchone()['count']
        
        # Get today's attendance for logged-in driver
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE driver_id = %s AND date = CURDATE()
        ''', (driver['id'],))
        attendance_today = cursor.fetchone()
        
        # Get last 7 days of attendance history
        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE driver_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            ORDER BY date DESC
        ''', (driver['id'],))
        attendance_history = cursor.fetchall()
        
        # Get completed call history (last 30 days)
        cursor.execute('''
            SELECT 
                id,
                patient_name,
                pickup_address as location,
                status,
                DATE_FORMAT(timestamp, '%b %d, %Y %H:%i') as dispatch_date,
                'Completed' as duration
            FROM patient_requests 
            WHERE assigned_driver = %s AND status = 'completed' 
            AND DATE(timestamp) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY timestamp DESC
            LIMIT 20
        ''', (driver_username,))
        call_history = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Pass complete driver data to template
        dashboard_data = {
            'driver_id': driver['id'],
            'driver_username': driver['username'],
            'driver_name': driver['name'],
            'phone': driver['phone'],
            'cnic': driver['cnic'],
            'experience': driver['experience'],
            'shift': driver['shift'],
            'status': driver['status'],
            'ambulance_id': driver['assigned_ambulance'],
            'hospital_id': driver['hospital_id'],
            'hospital_name': driver['hospital_name'],
            'hospital_lat': float(driver['hospital_lat']) if driver.get('hospital_lat') else None,
            'hospital_lng': float(driver['hospital_lng']) if driver.get('hospital_lng') else None,
            'profile_pic': driver.get('profile_pic'),
            'license': driver['license'],
            'current_location': 'Main Station',
            'active_calls': 1 if active_assignment else 0,
            'completed_today': completed_today,
            'response_time_avg': '6.2 minutes',
            'active_assignment': active_assignment,
            'assignment_status_step': {'assigned': 0, 'dispatched': 0, 'en_route': 1, 'picked_up': 2, 'completed': 3}.get(active_assignment.get('status', ''), 0) if active_assignment else -1,
            'vehicle_type': 'Advanced Life Support',
            'certifications': driver['certifications'] if isinstance(driver['certifications'], list) else [],
            'attendance_today': attendance_today,
            'attendance_history': attendance_history if attendance_history else [],
            'call_history': call_history if call_history else []
        }
        
        print(f'[DRIVER DASHBOARD] Loaded successfully for {driver["name"]}')
        return render_template('driver_dashboard.html', data=dashboard_data)
    
    except Exception as e:
        print(f'[DRIVER DASHBOARD ERROR] {str(e)}')
        return redirect(url_for('driver_login'))

# ==================== DRIVER CHANGE PASSWORD ====================
@app.route('/driver-change-password', methods=['POST'])
def driver_change_password():
    """Handle driver password change with current password verification"""
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    driver_id = session.get('driver_id')
    
    if not driver_id:
        print('[CHANGE PASSWORD ERROR] No driver_id in session')
        return jsonify({'status': 'error', 'message': 'Session error'}), 401
    
    # Handle JSON request
    if request.is_json:
        data = request.get_json()
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        verify_only = data.get('verify_only', False)
    else:
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        verify_only = False
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Step 1: Get current driver password from database by driver_id
        print(f'[CHANGE PASSWORD] Querying driver with id={driver_id}')
        cursor.execute('SELECT id, password FROM drivers WHERE id = %s', (driver_id,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            print(f'[CHANGE PASSWORD ERROR] Driver with id={driver_id} not found')
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        # Step 2: Verify current password
        print(f'[CHANGE PASSWORD] Comparing password - entered: {old_password[:3]}..., stored: {driver["password"][:3]}...')
        
        if driver['password'] != old_password:
            cursor.close()
            conn.close()
            print(f'[CHANGE PASSWORD ERROR] Password mismatch for driver {driver_id}')
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 400
        
        print(f'[CHANGE PASSWORD] Password verification SUCCESS for driver {driver_id}')
        
        # If only verifying password, return success here
        if verify_only:
            cursor.close()
            conn.close()
            return jsonify({'status': 'success'}), 200
        
        # Step 3: Validate new password length (minimum 6 characters)
        if not new_password or len(new_password) < 6:
            cursor.close()
            conn.close()
            print(f'[CHANGE PASSWORD ERROR] New password too short for driver {driver_id}')
            return jsonify({'status': 'error', 'message': 'New password is invalid'}), 400
        
        # Step 4: Check if passwords match
        if new_password != confirm_password:
            cursor.close()
            conn.close()
            print(f'[CHANGE PASSWORD ERROR] Password mismatch (new vs confirm) for driver {driver_id}')
            return jsonify({'status': 'error', 'message': 'Passwords do not match'}), 400
        
        # Step 5: Update password
        cursor.execute('UPDATE drivers SET password = %s WHERE id = %s', 
                      (new_password, driver_id))
        conn.commit()
        
        print(f'[DRIVER PASSWORD CHANGE] Driver {driver_id} changed password successfully')
        
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Password changed successfully'}), 200
    
    except Exception as e:
        print(f'[CHANGE PASSWORD ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Server error, try again'}), 500

@app.route('/driver/forgot-password', methods=['POST'])
def driver_forgot_password():
    """Handle driver password reset without old password verification"""
    if request.method == 'POST':
        # Handle JSON request
        if request.is_json:
            data = request.get_json()
            driver_id = data.get('driver_id', '').strip()
            new_password = data.get('new_password', '').strip()
            check_only = data.get('check_only', False)
        else:
            driver_id = request.form.get('driver_id', '').strip()
            new_password = request.form.get('new_password', '').strip()
            check_only = False
        
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            
            # Step 1: Check if driver exists by username (driver_id)
            cursor.execute('SELECT id FROM drivers WHERE username = %s', (driver_id,))
            driver = cursor.fetchone()
            
            if not driver:
                cursor.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Driver ID not found'}), 404
            
            # If only checking if driver exists, return success
            if check_only:
                cursor.close()
                conn.close()
                return jsonify({'status': 'success'}), 200
            
            # Step 2: Validate new password
            if not new_password:
                cursor.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'New password is required'}), 400
            
            if len(new_password) < 6:
                cursor.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'New password is invalid'}), 400
            
            # Step 3: Update password
            cursor.execute('UPDATE drivers SET password = %s WHERE username = %s', 
                          (new_password, driver_id))
            conn.commit()
            
            print(f'[DRIVER PASSWORD RESET] Driver ID {driver_id} (ID: {driver["id"]}) reset password successfully')
            
            cursor.close()
            conn.close()
            
            return jsonify({'status': 'success', 'message': 'Password reset successfully'}), 200
        
        except Exception as e:
            print(f'[DRIVER PASSWORD RESET ERROR] {str(e)}')
            import traceback
            print(traceback.format_exc())
            return jsonify({'status': 'error', 'message': 'Error resetting password'}), 500
    
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405

# ==================== HOSPITAL SESSION CHECK ====================
def check_hospital_session():
    """Check and log hospital session information"""
    print(f'[SESSION] user_type={session.get("user_type")}, hospital_id={session.get("hospital_id")}')
    return session.get('user_type') == 'hospital' and session.get('hospital_id') is not None

def is_admin_logged_in():
    """Check if the current session belongs to an authenticated admin"""
    return session.get('user_type') == 'admin' and session.get('admin_id') is not None

# ==================== ADMIN LOGIN / LOGOUT ROUTES ====================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Handle admin authentication and login"""
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('admin_login.html', error='Username and password are required')

        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM admins WHERE username = %s', (username,))
            admin = cursor.fetchone()
            cursor.close()
            conn.close()

            if admin and admin['password'] == password:
                session.clear()
                session['user_type'] = 'admin'
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session.permanent = True
                session.modified = True
                print(f'[ADMIN LOGIN] {username} logged in')
                return redirect(url_for('admin_dashboard'))
            else:
                return render_template('admin_login.html', error='Invalid username or password')

        except Exception as e:
            print(f'[ADMIN LOGIN ERROR] {str(e)}')
            return render_template('admin_login.html', error='A server error occurred. Please try again.')

    success = 'Logged out successfully' if request.args.get('msg') == 'loggedout' else None
    return render_template('admin_login.html', success=success)

@app.route('/admin-logout')
def admin_logout():
    """Logout admin user"""
    session.clear()
    return redirect(url_for('admin_login', msg='loggedout'))


# ==================== ADMIN REPORTS ====================

@app.route('/admin-reports')
def admin_reports():
    """System-wide reports and analytics page"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    try:
        conn = get_db()
        if not conn:
            return render_template('admin_reports.html',
                summary={}, trend_7days=[], trend_30days=[],
                status_breakdown=[], hospital_perf=[], driver_activity=[],
                admin_username=session.get('admin_username', 'Admin'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        # --- Summary Cards ---
        cursor.execute('SELECT COUNT(*) AS cnt FROM patient_requests')
        total_emergencies = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM hospitals WHERE COALESCE(status,'approved') = 'approved'")
        approved_hospitals = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM drivers WHERE LOWER(status) = 'available'")
        active_drivers = cursor.fetchone()['cnt']

        cursor.execute('SELECT MIN(timestamp) AS first_ts FROM patient_requests')
        row = cursor.fetchone()
        first_ts = row['first_ts'] if row else None
        from datetime import datetime as _dt
        if first_ts:
            delta = _dt.now() - first_ts
            uptime_days = delta.days
            uptime_label = f'{uptime_days} day{"s" if uptime_days != 1 else ""}'
        else:
            uptime_label = 'No data yet'

        summary = {
            'total_emergencies': total_emergencies,
            'approved_hospitals': approved_hospitals,
            'active_drivers': active_drivers,
            'uptime': uptime_label,
        }

        # --- 7-Day Emergency Trend ---
        cursor.execute('''
            SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
            FROM patient_requests
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY day
        ''')
        rows_7 = cursor.fetchall()
        # Build full 7-day map (fill missing days with 0)
        import datetime as _datetime
        day_map_7 = {}
        for r in rows_7:
            day_map_7[str(r['day'])] = r['cnt']
        trend_7days = []
        for i in range(6, -1, -1):
            d = (_datetime.date.today() - _datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            trend_7days.append({'day': d, 'cnt': day_map_7.get(d, 0)})

        # --- Status Breakdown ---
        cursor.execute('''
            SELECT COALESCE(LOWER(status), 'unknown') AS status, COUNT(*) AS cnt
            FROM patient_requests
            GROUP BY LOWER(status)
            ORDER BY cnt DESC
        ''')
        status_breakdown = [{'status': r['status'].replace('_', ' ').title(), 'cnt': r['cnt']} for r in cursor.fetchall()]

        # --- Hospital Performance ---
        cursor.execute('''
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
        ''')
        hospital_perf_raw = cursor.fetchall()
        hospital_perf = []
        for h in hospital_perf_raw:
            total = int(h['total'] or 0)
            completed = int(h['completed'] or 0)
            success_rate = round((completed / total * 100) if total > 0 else 0, 1)
            avg = float(h['avg_response_min']) if h['avg_response_min'] is not None else None
            if avg is None:
                rating, rating_cls = 'N/A', 'na'
            elif avg < 8:
                rating, rating_cls = 'EXCELLENT', 'excellent'
            elif avg <= 15:
                rating, rating_cls = 'GOOD', 'good'
            else:
                rating, rating_cls = 'POOR', 'poor'
            hospital_perf.append({
                'name': h['name'],
                'total': total,
                'completed': completed,
                'success_rate': success_rate,
                'avg_response_min': round(avg, 1) if avg is not None else None,
                'rating': rating,
                'rating_cls': rating_cls,
            })

        # --- Driver Activity ---
        cursor.execute('''
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
        ''')
        driver_rows = cursor.fetchall()
        driver_activity = []
        for dr in driver_rows:
            avg = float(dr['avg_response_min']) if dr['avg_response_min'] is not None else None
            driver_activity.append({
                'name': dr['name'],
                'hospital_name': dr['hospital_name'] or 'Unassigned',
                'total': int(dr['total'] or 0),
                'completed': int(dr['completed'] or 0),
                'avg_response_min': round(avg, 1) if avg is not None else None,
            })

        # --- 30-Day Trend ---
        cursor.execute('''
            SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
            FROM patient_requests
            WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY day
        ''')
        rows_30 = cursor.fetchall()
        day_map_30 = {}
        for r in rows_30:
            day_map_30[str(r['day'])] = r['cnt']
        trend_30days = []
        for i in range(29, -1, -1):
            d = (_datetime.date.today() - _datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            trend_30days.append({'day': d, 'cnt': day_map_30.get(d, 0)})

        cursor.close()
        conn.close()

        return render_template(
            'admin_reports.html',
            summary=summary,
            trend_7days=trend_7days,
            trend_30days=trend_30days,
            status_breakdown=status_breakdown,
            hospital_perf=hospital_perf,
            driver_activity=driver_activity,
            admin_username=session.get('admin_username', 'Admin')
        )

    except Exception as e:
        print(f'[ADMIN REPORTS ERROR] {str(e)}')
        return render_template('admin_reports.html',
            summary={'total_emergencies': 0, 'approved_hospitals': 0, 'active_drivers': 0, 'uptime': 'N/A'},
            trend_7days=[], trend_30days=[], status_breakdown=[],
            hospital_perf=[], driver_activity=[],
            admin_username=session.get('admin_username', 'Admin'))


@app.route('/admin-dashboard')
def admin_dashboard():
    """Admin main dashboard — shows system-wide stats"""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Total hospitals
        cursor.execute('SELECT COUNT(*) AS total FROM hospitals')
        total_hospitals = cursor.fetchone()['total']

        # Total drivers (active = Available, offline = everything else)
        cursor.execute("SELECT COUNT(*) AS total FROM drivers")
        total_drivers = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS active FROM drivers WHERE status = 'Available'")
        active_drivers = cursor.fetchone()['active']
        offline_drivers = total_drivers - active_drivers

        # Today's emergencies
        cursor.execute(
            "SELECT COUNT(*) AS today FROM patient_requests WHERE DATE(timestamp) = CURDATE()"
        )
        emergencies_today = cursor.fetchone()['today']

        # Average response time (minutes) — dispatches completed today
        cursor.execute("""
            SELECT AVG(TIMESTAMPDIFF(MINUTE, pr.timestamp, d.timestamp)) AS avg_minutes
            FROM dispatches d
            JOIN patient_requests pr ON pr.request_id = d.request_id
            WHERE DATE(d.timestamp) = CURDATE()
        """)
        row = cursor.fetchone()
        avg_response = round(row['avg_minutes'], 1) if row['avg_minutes'] else 0

        # Total users (patients registered in the system)
        cursor.execute('SELECT COUNT(*) AS total FROM users')
        total_users_row = cursor.fetchone()
        total_users = total_users_row['total'] if total_users_row else 0

        cursor.close()
        conn.close()

        stats = {
            'total_hospitals': total_hospitals,
            'total_drivers': total_drivers,
            'active_drivers': active_drivers,
            'offline_drivers': offline_drivers,
            'emergencies_today': emergencies_today,
            'avg_response': avg_response,
            'total_users': total_users,
        }

        return render_template(
            'admin_dashboard.html',
            stats=stats,
            admin_username=session.get('admin_username', 'Admin')
        )

    except Exception as e:
        print(f'[ADMIN DASHBOARD ERROR] {str(e)}')
        stats = {
            'total_hospitals': 0, 'total_drivers': 0,
            'active_drivers': 0, 'offline_drivers': 0,
            'emergencies_today': 0, 'avg_response': 0,
            'total_users': 0,
        }
        return render_template(
            'admin_dashboard.html',
            stats=stats,
            admin_username=session.get('admin_username', 'Admin')
        )

# ==================== ADMIN HOSPITALS MANAGEMENT ====================

@app.route('/admin-hospitals')
def admin_hospitals():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    try:
        conn = get_db()
        if not conn:
            return render_template('admin_hospitals.html', pending_hospitals=[], approved_hospitals=[], rejected_hospitals=[], stats={}, admin_username=session.get('admin_username', 'Admin'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)
        cursor.execute("""
            SELECT id, name, username, address, phone, email,
                   total_beds, available_beds, specialties,
                   COALESCE(latitude, 0) AS latitude,
                   COALESCE(longitude, 0) AS longitude,
                   COALESCE(is_verified, 0) AS is_verified,
                   COALESCE(status, 'approved') AS status,
                   COALESCE(is_locked, 0) AS is_locked,
                   rejection_reason, created_at
            FROM hospitals
            ORDER BY created_at DESC
        """)
        hospitals = cursor.fetchall()
        
        # Convert latitude and longitude to float for all hospitals
        for h in hospitals:
            h['latitude'] = float(h['latitude']) if h['latitude'] else 0.0
            h['longitude'] = float(h['longitude']) if h['longitude'] else 0.0
        
        total = len(hospitals)
        pending_hospitals = [h for h in hospitals if h['status'] == 'pending']
        approved_hospitals = [h for h in hospitals if h['status'] == 'approved']
        rejected_hospitals = [h for h in hospitals if h['status'] == 'rejected']
        cursor.close()
        conn.close()
        stats = {
            'total': total,
            'pending': len(pending_hospitals),
            'approved': len(approved_hospitals),
            'rejected': len(rejected_hospitals)
        }
        return render_template(
            'admin_hospitals.html',
            pending_hospitals=pending_hospitals,
            approved_hospitals=approved_hospitals,
            rejected_hospitals=rejected_hospitals,
            stats=stats,
            admin_username=session.get('admin_username', 'Admin')
        )
    except Exception as e:
        print(f'[ADMIN HOSPITALS ERROR] {str(e)}')
        return render_template('admin_hospitals.html', pending_hospitals=[], approved_hospitals=[], rejected_hospitals=[], stats={'total':0,'pending':0,'approved':0,'rejected':0}, admin_username=session.get('admin_username', 'Admin'))


@app.route('/admin-verify-hospital/<int:hospital_id>', methods=['POST'])
def admin_verify_hospital(hospital_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("UPDATE hospitals SET is_verified = 1 WHERE id = %s", (hospital_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hospital verified'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-remove-hospital/<int:hospital_id>', methods=['POST'])
def admin_remove_hospital(hospital_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        # Nullify foreign key references before deleting the hospital
        cursor.execute("UPDATE patient_requests SET hospital_id = NULL WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("UPDATE dispatches SET hospital_id = NULL WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("UPDATE drivers SET hospital_id = NULL WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("UPDATE ambulances SET hospital_id = NULL WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("DELETE FROM hospitals WHERE id = %s", (hospital_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hospital removed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-update-hospital-location/<int:hospital_id>', methods=['POST'])
def admin_update_hospital_location(hospital_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is None or longitude is None:
            return jsonify({'status': 'error', 'message': 'Missing coordinates'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("UPDATE hospitals SET latitude = %s, longitude = %s WHERE id = %s",
                       (float(latitude), float(longitude), hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Location updated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-approve-hospital/<int:hospital_id>', methods=['POST'])
def admin_approve_hospital(hospital_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("UPDATE hospitals SET status = 'approved', rejection_reason = NULL WHERE id = %s", (hospital_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hospital approved'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-reject-hospital/<int:hospital_id>', methods=['POST'])
def admin_reject_hospital(hospital_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        reason = (data.get('reason') or '').strip() or 'Rejected by admin'
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("UPDATE hospitals SET status = 'rejected', rejection_reason = %s WHERE id = %s", (reason, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Hospital rejected'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-lock-hospital/<int:hospital_id>', methods=['POST'])
def admin_lock_hospital(hospital_id):
    """Lock or unlock an approved hospital. Locked hospitals cannot login."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json() or {}
        action = data.get('action', '')
        if action not in ('lock', 'unlock'):
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
        is_locked = 1 if action == 'lock' else 0
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("UPDATE hospitals SET is_locked = %s WHERE id = %s", (is_locked, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        msg = 'Hospital locked' if action == 'lock' else 'Hospital unlocked'
        return jsonify({'status': 'success', 'message': msg, 'is_locked': is_locked})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
def admin_api_pending_count():
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'count': 0})
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("SELECT COUNT(*) FROM hospitals WHERE COALESCE(status, 'approved') = 'pending'")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0})


# ==================== ADMIN DRIVERS MANAGEMENT ====================

@app.route('/admin-drivers')
def admin_drivers():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    try:
        conn = get_db()
        if not conn:
            return render_template('admin_drivers.html', drivers=[], stats={'total':0,'available':0,'busy':0,'offline':0}, admin_username=session.get('admin_username', 'Admin'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)
        cursor.execute("""
            SELECT
                d.id, d.name, d.username, d.phone, d.cnic, d.experience,
                d.status, d.profile_pic, d.shift, d.assigned_ambulance, d.license,
                d.current_latitude, d.current_longitude, d.location_updated_at,
                d.created_at,
                h.name AS hospital_name
            FROM drivers d
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            ORDER BY
                CASE WHEN LOWER(d.status) = 'available' THEN 0
                     WHEN LOWER(d.status) IN ('busy','on trip','responding') THEN 1
                     ELSE 2 END,
                d.name ASC
        """)
        drivers = cursor.fetchall()
        # Serialize datetimes
        for d in drivers:
            for col in ('created_at', 'location_updated_at'):
                if d.get(col) and hasattr(d[col], 'strftime'):
                    d[col] = d[col].strftime('%Y-%m-%d %H:%M:%S')
        total = len(drivers)
        available = sum(1 for d in drivers if d['status'] and d['status'].lower() == 'available')
        busy = sum(1 for d in drivers if d['status'] and d['status'].lower() in ('busy', 'on trip', 'responding'))
        offline = total - available - busy
        cursor.close()
        conn.close()
        return render_template(
            'admin_drivers.html',
            drivers=drivers,
            stats={'total': total, 'available': available, 'busy': busy, 'offline': offline},
            admin_username=session.get('admin_username', 'Admin')
        )
    except Exception as e:
        print(f'[ADMIN DRIVERS ERROR] {str(e)}')
        return render_template('admin_drivers.html', drivers=[], stats={'total':0,'available':0,'busy':0,'offline':0}, admin_username=session.get('admin_username', 'Admin'))


@app.route('/admin-drivers-live')
def admin_drivers_live():
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify([])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)
        cursor.execute("SELECT id, status, location_updated_at FROM drivers")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'status': r['status'] or 'Offline',
                'location_updated_at': r['location_updated_at'].strftime('%Y-%m-%d %H:%M:%S') if r['location_updated_at'] else None
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-driver-details/<int:driver_id>')
def admin_driver_details(driver_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)
        cursor.execute("""
            SELECT d.id, d.name, d.username, d.phone, d.cnic, d.experience,
                   d.status, d.profile_pic, d.shift, d.assigned_ambulance, d.license,
                   d.current_latitude, d.current_longitude, d.location_updated_at,
                   d.created_at, h.name AS hospital_name
            FROM drivers d
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.id = %s
        """, (driver_id,))
        driver = cursor.fetchone()
        if not driver:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        # Attendance last 7 days
        cursor.execute("""
            SELECT date, status, admin_status
            FROM attendance_records
            WHERE driver_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            ORDER BY date DESC
        """, (driver_id,))
        attendance = cursor.fetchall()
        # Total emergencies handled
        cursor.execute("""
            SELECT COUNT(*) AS total FROM patient_requests
            WHERE assigned_driver_id = %s AND status = 'completed'
        """, (driver_id,))
        emerg_row = cursor.fetchone()
        total_emergencies = emerg_row['total'] if emerg_row else 0
        cursor.close()
        conn.close()
        for col in ('created_at', 'location_updated_at'):
            if driver.get(col) and hasattr(driver[col], 'strftime'):
                driver[col] = driver[col].strftime('%Y-%m-%d %H:%M:%S')
        for row in attendance:
            if row.get('date') and hasattr(row['date'], 'strftime'):
                row['date'] = row['date'].strftime('%Y-%m-%d')
        driver.pop('password', None)
        return jsonify({'status': 'success', 'driver': driver, 'attendance': attendance, 'total_emergencies': total_emergencies})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-remove-driver/<int:driver_id>', methods=['POST'])
def admin_remove_driver(driver_id):
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute("USE " + DB_NAME)
        cursor.execute("DELETE FROM drivers WHERE id = %s", (driver_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Driver removed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN EMERGENCIES MANAGEMENT ====================

_ACTIVE_STATUSES = ('pending', 'accepted', 'assigned', 'en_route', 'picked_up')

def _serialize_row(row):
    """Convert datetime/date values in a dict to strings."""
    for k, v in row.items():
        if v and hasattr(v, 'strftime'):
            row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
    return row


@app.route('/admin-emergencies')
def admin_emergencies():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    empty_stats = {'total_today': 0, 'active': 0, 'completed': 0,
                   'forwarded': 0, 'avg_response': 0}
    try:
        conn = get_db()
        if not conn:
            return render_template('admin_emergencies.html', active_rows=[], history_rows=[],
                                   stats=empty_stats, admin_username=session.get('admin_username', 'Admin'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)

        base_select = """
            SELECT
                pr.id, pr.request_id, pr.patient_name, pr.patient_phone,
                pr.pickup_address, pr.latitude, pr.longitude,
                pr.reason, pr.priority, pr.status,
                pr.age, pr.symptoms,
                pr.cancelled, pr.auto_processed,
                pr.forwarded_from_hospital_id,
                pr.reassignment_count,
                pr.ip_address,
                pr.timestamp AS created_at,
                h.name  AS hospital_name,
                d.name  AS driver_name,
                d.phone AS driver_phone,
                fh.name AS forwarded_from_name
            FROM patient_requests pr
            LEFT JOIN hospitals h  ON pr.hospital_id = h.id
            LEFT JOIN drivers  d  ON pr.assigned_driver_id = d.id
            LEFT JOIN hospitals fh ON pr.forwarded_from_hospital_id = fh.id
        """

        # Active emergencies
        cursor.execute(base_select +
            "WHERE pr.status IN ('pending','accepted','assigned','en_route','picked_up') "
            "AND (pr.cancelled IS NULL OR pr.cancelled = 0) "
            "ORDER BY pr.timestamp DESC"
        )
        active_rows = [_serialize_row(r) for r in cursor.fetchall()]

        # History (completed + no_hospital_available + cancelled)
        cursor.execute(base_select +
            "WHERE pr.status NOT IN ('pending','accepted','assigned','en_route','picked_up') "
            "   OR pr.cancelled = 1 "
            "ORDER BY pr.timestamp DESC LIMIT 500"
        )
        history_rows = [_serialize_row(r) for r in cursor.fetchall()]

        # Stats
        cursor.execute("SELECT COUNT(*) AS c FROM patient_requests WHERE DATE(timestamp) = CURDATE()")
        total_today = (cursor.fetchone() or {}).get('c', 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests "
            "WHERE status IN ('pending','accepted','assigned','en_route','picked_up') "
            "AND (cancelled IS NULL OR cancelled = 0)"
        )
        active_count = (cursor.fetchone() or {}).get('c', 0)

        cursor.execute("SELECT COUNT(*) AS c FROM patient_requests WHERE status = 'completed'")
        completed_count = (cursor.fetchone() or {}).get('c', 0)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests "
            "WHERE auto_processed = 1 OR forwarded_from_hospital_id IS NOT NULL"
        )
        forwarded_count = (cursor.fetchone() or {}).get('c', 0)

        # Avg response (minutes) from dispatches table response
        try:
            cursor.execute("""
                SELECT AVG(TIMESTAMPDIFF(MINUTE, pr.timestamp, st.timestamp)) AS avg_min
                FROM status_timeline st
                JOIN patient_requests pr ON pr.request_id = st.request_id
                WHERE st.new_status = 'completed'
                  AND st.timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            avg_row = cursor.fetchone()
            avg_response = round(float(avg_row['avg_min']), 1) if avg_row and avg_row['avg_min'] else 0
        except Exception:
            avg_response = 0

        # ===== Suspicious activity detection =====
        suspicious_ips = set()
        suspicious_phones = set()
        try:
            cursor.execute("""
                SELECT ip_address, COUNT(*) AS cnt
                FROM patient_requests
                WHERE ip_address IS NOT NULL AND ip_address != ''
                  AND timestamp >= %s
                GROUP BY ip_address
                HAVING cnt >= 3
            """, (datetime.now() - timedelta(hours=1),))
            suspicious_ips = {row['ip_address'] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT patient_phone, COUNT(*) AS cnt
                FROM patient_requests
                WHERE patient_phone IS NOT NULL
                  AND patient_phone NOT IN ('Not Provided', 'N/A', '')
                  AND DATE(timestamp) = CURDATE()
                GROUP BY patient_phone
                HAVING cnt >= 5
            """)
            suspicious_phones = {row['patient_phone'] for row in cursor.fetchall()}
        except Exception:
            pass

        cursor.close()
        conn.close()

        def _label_suspicious(rows):
            for row in rows:
                reasons = []
                if row.get('ip_address') and row['ip_address'] in suspicious_ips:
                    reasons.append('Same IP: 3+ requests in 1 hour')
                if row.get('patient_phone') and row['patient_phone'] in suspicious_phones:
                    reasons.append('Same phone: 5+ requests today')
                try:
                    rlat = float(row.get('latitude') or 0)
                    rlng = float(row.get('longitude') or 0)
                    if rlat != 0.0 or rlng != 0.0:
                        if not (23.0 <= rlat <= 37.0 and 60.0 <= rlng <= 77.0):
                            reasons.append('Location outside Pakistan')
                except Exception:
                    pass
                row['is_suspicious'] = bool(reasons)
                row['suspicious_reasons'] = '; '.join(reasons)

        _label_suspicious(active_rows)
        _label_suspicious(history_rows)

        stats = {
            'total_today': total_today,
            'active': active_count,
            'completed': completed_count,
            'forwarded': forwarded_count,
            'avg_response': avg_response,
        }
        return render_template(
            'admin_emergencies.html',
            active_rows=active_rows,
            history_rows=history_rows,
            stats=stats,
            admin_username=session.get('admin_username', 'Admin')
        )
    except Exception as e:
        print(f'[ADMIN EMERGENCIES ERROR] {str(e)}')
        return render_template('admin_emergencies.html', active_rows=[], history_rows=[],
                               stats=empty_stats, admin_username=session.get('admin_username', 'Admin'))


@app.route('/admin-emergencies-live')
def admin_emergencies_live():
    """Lightweight JSON endpoint for 15-second auto-refresh of active emergencies."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'active': [], 'stats': {}})
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)
        cursor.execute("""
            SELECT
                pr.request_id, pr.patient_name, pr.pickup_address,
                pr.status, pr.priority, pr.timestamp AS created_at,
                h.name AS hospital_name, d.name AS driver_name
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            LEFT JOIN drivers  d ON pr.assigned_driver_id = d.id
            WHERE pr.status IN ('pending','accepted','assigned','en_route','picked_up')
              AND (pr.cancelled IS NULL OR pr.cancelled = 0)
            ORDER BY pr.timestamp DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            _serialize_row(r)

        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests "
            "WHERE status IN ('pending','accepted','assigned','en_route','picked_up') "
            "AND (cancelled IS NULL OR cancelled = 0)"
        )
        active_count = (cursor.fetchone() or {}).get('c', 0)
        cursor.close()
        conn.close()
        return jsonify({'active': rows, 'active_count': active_count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-emergency-details/<request_id>')
def admin_emergency_details(request_id):
    """Full detail JSON for the row-click modal."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE " + DB_NAME)

        cursor.execute("""
            SELECT
                pr.*,
                h.name  AS hospital_name,
                h.address AS hospital_address,
                d.name  AS driver_name, d.phone AS driver_phone,
                fh.name AS forwarded_from_name
            FROM patient_requests pr
            LEFT JOIN hospitals h  ON pr.hospital_id = h.id
            LEFT JOIN drivers  d  ON pr.assigned_driver_id = d.id
            LEFT JOIN hospitals fh ON pr.forwarded_from_hospital_id = fh.id
            WHERE pr.request_id = %s
        """, (request_id,))
        req = cursor.fetchone()
        if not req:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Not found'}), 404
        _serialize_row(req)
        # Remove nulls that can't be JSON serialised
        req.pop('rejected_by', None)

        # Timeline
        cursor.execute("""
            SELECT old_status, new_status, action_by, action_type,
                   driver_name, notes, timestamp
            FROM status_timeline
            WHERE request_id = %s
            ORDER BY timestamp ASC
        """, (request_id,))
        timeline = []
        for t in cursor.fetchall():
            _serialize_row(t)
            timeline.append(t)

        # ===== Suspicious flags for this request =====
        is_suspicious = False
        suspicious_reasons = []
        is_blacklisted = False
        try:
            if req.get('ip_address'):
                cursor.execute(
                    'SELECT COUNT(*) AS cnt FROM patient_requests '
                    'WHERE ip_address = %s AND timestamp >= %s',
                    (req['ip_address'], datetime.now() - timedelta(hours=1))
                )
                cnt = (cursor.fetchone() or {}).get('cnt', 0)
                if cnt >= 3:
                    suspicious_reasons.append(f'Same IP: {cnt} requests in 1 hour')
            if req.get('patient_phone') and req['patient_phone'] not in ('Not Provided', 'N/A', ''):
                cursor.execute(
                    'SELECT COUNT(*) AS cnt FROM patient_requests '
                    'WHERE patient_phone = %s AND DATE(timestamp) = CURDATE()',
                    (req['patient_phone'],)
                )
                cnt = (cursor.fetchone() or {}).get('cnt', 0)
                if cnt >= 5:
                    suspicious_reasons.append(f'Same phone: {cnt} requests today')
                cursor.execute('SELECT id FROM blacklist WHERE phone = %s', (req['patient_phone'],))
                is_blacklisted = cursor.fetchone() is not None
            try:
                rlat = float(req.get('latitude') or 0)
                rlng = float(req.get('longitude') or 0)
                if rlat != 0.0 or rlng != 0.0:
                    if not (23.0 <= rlat <= 37.0 and 60.0 <= rlng <= 77.0):
                        suspicious_reasons.append('Location outside Pakistan')
            except Exception:
                pass
            is_suspicious = bool(suspicious_reasons)
        except Exception:
            pass

        cursor.close()
        conn.close()
        req['is_suspicious'] = is_suspicious
        req['suspicious_reasons'] = '; '.join(suspicious_reasons)
        req['is_blacklisted'] = is_blacklisted
        return jsonify({'status': 'success', 'request': req, 'timeline': timeline})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN USERS MANAGEMENT ====================

@app.route('/admin-users')
def admin_users():
    """Admin users management page — lists all registered patients."""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    empty_stats = {'total_users': 0, 'active_today': 0, 'total_requests': 0, 'new_this_week': 0}
    try:
        conn = get_db()
        if not conn:
            return render_template('admin_users.html', users=[], stats=empty_stats,
                                   admin_username=session.get('admin_username', 'Admin'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        # All users with request count and last request date
        cursor.execute("""
            SELECT u.id, u.full_name, u.cnic, u.phone, u.user_type,
                   u.created_at,
                   COUNT(pr.id)         AS total_requests,
                   MAX(pr.timestamp)    AS last_request
            FROM users u
            LEFT JOIN patient_requests pr ON pr.patient_phone = u.phone
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        users = [_serialize_row(r) for r in cursor.fetchall()]

        total_users = len(users)

        # Active today — users who submitted a request today
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id) AS c
            FROM users u
            JOIN patient_requests pr ON pr.patient_phone = u.phone
            WHERE DATE(pr.timestamp) = CURDATE()
        """)
        active_today = (cursor.fetchone() or {}).get('c', 0)

        # Total requests ever
        cursor.execute('SELECT COUNT(*) AS c FROM patient_requests')
        total_requests = (cursor.fetchone() or {}).get('c', 0)

        # New users this week
        cursor.execute("""
            SELECT COUNT(*) AS c FROM users
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        new_this_week = (cursor.fetchone() or {}).get('c', 0)

        cursor.close()
        conn.close()

        stats = {
            'total_users': total_users,
            'active_today': active_today,
            'total_requests': total_requests,
            'new_this_week': new_this_week,
        }
        return render_template('admin_users.html', users=users, stats=stats,
                               admin_username=session.get('admin_username', 'Admin'))
    except Exception as e:
        print(f'[ADMIN USERS ERROR] {str(e)}')
        return render_template('admin_users.html', users=[], stats=empty_stats,
                               admin_username=session.get('admin_username', 'Admin'))


@app.route('/admin-user-details/<int:user_id>')
def admin_user_details(user_id):
    """JSON endpoint — full profile + request history for modal."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB unavailable'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        cursor.execute(
            'SELECT id, full_name, cnic, phone, user_type, created_at FROM users WHERE id = %s',
            (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            cursor.close(); conn.close()
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        _serialize_row(user)

        # Full request history
        cursor.execute("""
            SELECT pr.request_id, pr.patient_name, pr.pickup_address,
                   pr.reason, pr.priority, pr.status, pr.cancelled,
                   pr.timestamp AS created_at,
                   h.name AS hospital_name
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            WHERE pr.patient_phone = %s
            ORDER BY pr.timestamp DESC
            LIMIT 50
        """, (user['phone'],))
        requests = [_serialize_row(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'user': user, 'requests': requests})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-remove-user/<int:user_id>', methods=['POST'])
def admin_remove_user(user_id):
    """Delete a user/patient account."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB unavailable'}), 500
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        if affected == 0:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        return jsonify({'status': 'success', 'message': 'User removed successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN API — EMERGENCY STATS ====================
@app.route('/admin-api/emergency-stats')
def admin_api_emergency_stats():
    """Lightweight stats + active rows for 15s polling."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'active': [], 'active_count': 0, 'total_today': 0})
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute("""
            SELECT pr.request_id, pr.patient_name, pr.patient_phone,
                   pr.pickup_address, pr.latitude, pr.longitude,
                   pr.status, pr.priority, pr.auto_processed,
                   pr.forwarded_from_hospital_id, pr.ip_address,
                   pr.timestamp AS created_at,
                   h.name AS hospital_name, d.name AS driver_name
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            LEFT JOIN drivers  d ON pr.assigned_driver_id = d.id
            WHERE pr.status IN ('pending','accepted','assigned','en_route','picked_up')
              AND (pr.cancelled IS NULL OR pr.cancelled = 0)
            ORDER BY pr.timestamp DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            _serialize_row(r)
        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests WHERE DATE(timestamp) = CURDATE()"
        )
        total_today = (cursor.fetchone() or {}).get('c', 0)
        # ===== Suspicious flags for live rows =====
        suspicious_ips = set()
        suspicious_phones = set()
        try:
            cursor.execute("""
                SELECT ip_address, COUNT(*) AS cnt FROM patient_requests
                WHERE ip_address IS NOT NULL AND ip_address != ''
                  AND timestamp >= %s
                GROUP BY ip_address HAVING cnt >= 3
            """, (datetime.now() - timedelta(hours=1),))
            suspicious_ips = {row['ip_address'] for row in cursor.fetchall()}
            cursor.execute("""
                SELECT patient_phone, COUNT(*) AS cnt FROM patient_requests
                WHERE patient_phone IS NOT NULL
                  AND patient_phone NOT IN ('Not Provided', 'N/A', '')
                  AND DATE(timestamp) = CURDATE()
                GROUP BY patient_phone HAVING cnt >= 5
            """)
            suspicious_phones = {row['patient_phone'] for row in cursor.fetchall()}
        except Exception:
            pass
        for r in rows:
            reasons = []
            if r.get('ip_address') and r['ip_address'] in suspicious_ips:
                reasons.append('Same IP: 3+ requests in 1 hour')
            if r.get('patient_phone') and r['patient_phone'] in suspicious_phones:
                reasons.append('Same phone: 5+ requests today')
            try:
                rlat = float(r.get('latitude') or 0)
                rlng = float(r.get('longitude') or 0)
                if rlat != 0.0 or rlng != 0.0:
                    if not (23.0 <= rlat <= 37.0 and 60.0 <= rlng <= 77.0):
                        reasons.append('Location outside Pakistan')
            except Exception:
                pass
            r['is_suspicious'] = bool(reasons)
            r['suspicious_reasons'] = '; '.join(reasons)
        cursor.close()
        conn.close()
        return jsonify({
            'active': rows,
            'active_count': len(rows),
            'total_today': total_today
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN ALL-STATS API ====================

@app.route('/admin-api/all-stats')
def admin_api_all_stats():
    """Central stats endpoint — single source of truth for all admin pages."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'total_hospitals': 0, 'total_drivers': 0,
                            'emergencies_today': 0, 'active_emergencies': 0, 'pending_hospitals': 0})
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        cursor.execute('SELECT COUNT(*) AS c FROM hospitals')
        total_hospitals = cursor.fetchone()['c']

        cursor.execute('SELECT COUNT(*) AS c FROM drivers')
        total_drivers = cursor.fetchone()['c']

        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests WHERE DATE(timestamp) = CURDATE()"
        )
        emergencies_today = cursor.fetchone()['c']

        cursor.execute(
            "SELECT COUNT(*) AS c FROM patient_requests "
            "WHERE status IN ('pending','accepted','assigned','en_route','picked_up') "
            "AND (cancelled IS NULL OR cancelled = 0)"
        )
        active_emergencies = cursor.fetchone()['c']

        cursor.execute(
            "SELECT COUNT(*) AS c FROM hospitals WHERE COALESCE(status,'approved') = 'pending'"
        )
        pending_hospitals = cursor.fetchone()['c']

        cursor.close()
        conn.close()
        return jsonify({
            'total_hospitals': total_hospitals,
            'total_drivers': total_drivers,
            'emergencies_today': emergencies_today,
            'active_emergencies': active_emergencies,
            'pending_hospitals': pending_hospitals
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN BLACKLIST API ====================

@app.route('/admin-api/blacklist', methods=['GET'])
def admin_api_blacklist_list():
    """List all blacklisted phone numbers."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'blacklist': []})
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('SELECT phone, reason, blocked_by, created_at FROM blacklist ORDER BY created_at DESC')
        rows = [_serialize_row(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'blacklist': rows})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-api/blacklist', methods=['POST'])
def admin_api_blacklist_add():
    """Blacklist a phone number."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        data = request.get_json() or {}
        phone = str(data.get('phone', '')).strip()
        reason = str(data.get('reason', 'Flagged by administrator')).strip()[:255]
        if not phone:
            return jsonify({'status': 'error', 'message': 'Phone is required'}), 400
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute(
            'INSERT INTO blacklist (phone, reason, blocked_by) VALUES (%s, %s, %s) '
            'ON DUPLICATE KEY UPDATE reason = VALUES(reason), blocked_by = VALUES(blocked_by)',
            (phone, reason, session.get('admin_username', 'admin'))
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f'[BLACKLIST] {phone} blacklisted by {session.get("admin_username")}: {reason}')
        return jsonify({'status': 'success', 'message': f'{phone} has been blacklisted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin-api/unblacklist/<phone>', methods=['POST'])
def admin_api_blacklist_remove(phone):
    """Remove a phone number from the blacklist."""
    if not is_admin_logged_in():
        return jsonify({'status': 'error'}), 401
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'DB error'}), 500
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('DELETE FROM blacklist WHERE phone = %s', (phone.strip(),))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'message': f'{phone} removed from blacklist'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ADMIN SETTINGS ====================

@app.route('/admin-settings')
def admin_settings():
    """Admin settings page: password, system settings, blacklist management."""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    auto_cancel_timed_out_requests()
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        # Current admin record
        cursor.execute('SELECT id, username FROM admins WHERE id = %s', (session['admin_id'],))
        admin_record = cursor.fetchone() or {}

        # System settings
        cursor.execute('SELECT setting_key, setting_value FROM system_settings')
        settings_raw = cursor.fetchall()
        settings = {r['setting_key']: r['setting_value'] for r in settings_raw}

        # Blacklist
        cursor.execute('SELECT phone, reason, blocked_by, created_at FROM blacklist ORDER BY created_at DESC')
        blacklist = [_serialize_row(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return render_template(
            'admin_settings.html',
            admin_record=admin_record,
            settings=settings,
            blacklist=blacklist,
            admin_username=session.get('admin_username', 'Admin')
        )
    except Exception as e:
        print(f'[ADMIN SETTINGS] {e}')
        return render_template(
            'admin_settings.html',
            admin_record={},
            settings={},
            blacklist=[],
            admin_username=session.get('admin_username', 'Admin')
        )


@app.route('/admin-change-password', methods=['POST'])
def admin_change_password():
    """Change admin password."""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    current_pw = request.form.get('current_password', '').strip()
    new_pw = request.form.get('new_password', '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()
    error = None
    success = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('SELECT password FROM admins WHERE id = %s', (session['admin_id'],))
        admin = cursor.fetchone()
        if not admin or admin['password'] != current_pw:
            error = 'Current password is incorrect'
        elif new_pw != confirm_pw:
            error = 'New passwords do not match'
        elif len(new_pw) < 4:
            error = 'New password must be at least 4 characters'
        else:
            cursor.execute('UPDATE admins SET password = %s WHERE id = %s', (new_pw, session['admin_id']))
            conn.commit()
            success = 'Password updated successfully'
        cursor.close()
        conn.close()
    except Exception as e:
        error = 'A server error occurred'
        print(f'[CHANGE PASSWORD] {e}')

    # Re-render settings page with message
    try:
        conn2 = get_db()
        cursor2 = conn2.cursor(dictionary=True)
        cursor2.execute('USE ' + DB_NAME)
        cursor2.execute('SELECT setting_key, setting_value FROM system_settings')
        settings = {r['setting_key']: r['setting_value'] for r in cursor2.fetchall()}
        cursor2.execute('SELECT phone, reason, blocked_by, created_at FROM blacklist ORDER BY created_at DESC')
        blacklist = [_serialize_row(r) for r in cursor2.fetchall()]
        cursor2.execute('SELECT id, username FROM admins WHERE id = %s', (session['admin_id'],))
        admin_record = cursor2.fetchone() or {}
        cursor2.close()
        conn2.close()
    except Exception:
        settings = {}
        blacklist = []
        admin_record = {}

    return render_template(
        'admin_settings.html',
        pw_error=error,
        pw_success=success,
        admin_record=admin_record,
        settings=settings,
        blacklist=blacklist,
        admin_username=session.get('admin_username', 'Admin')
    )


@app.route('/admin-save-settings', methods=['POST'])
def admin_save_settings():
    """Save system settings (emergency_timeout, max_distance)."""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    error = None
    success = None
    try:
        timeout_val = request.form.get('emergency_timeout', '10').strip()
        distance_val = request.form.get('max_distance', '50').strip()
        # Validate numbers
        timeout_int = int(timeout_val)
        distance_int = int(distance_val)
        if timeout_int < 1 or timeout_int > 1440:
            raise ValueError('Timeout must be 1–1440 minutes')
        if distance_int < 1 or distance_int > 500:
            raise ValueError('Distance must be 1–500 km')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute(
            "INSERT INTO system_settings (setting_key, setting_value) VALUES ('emergency_timeout', %s) "
            "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)",
            (str(timeout_int),)
        )
        cursor.execute(
            "INSERT INTO system_settings (setting_key, setting_value) VALUES ('max_distance', %s) "
            "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)",
            (str(distance_int),)
        )
        conn.commit()
        cursor.close()
        conn.close()
        success = 'Settings saved successfully'
    except ValueError as ve:
        error = str(ve)
    except Exception as e:
        error = 'A server error occurred'
        print(f'[SAVE SETTINGS] {e}')

    try:
        conn2 = get_db()
        cursor2 = conn2.cursor(dictionary=True)
        cursor2.execute('USE ' + DB_NAME)
        cursor2.execute('SELECT setting_key, setting_value FROM system_settings')
        settings = {r['setting_key']: r['setting_value'] for r in cursor2.fetchall()}
        cursor2.execute('SELECT phone, reason, blocked_by, created_at FROM blacklist ORDER BY created_at DESC')
        blacklist = [_serialize_row(r) for r in cursor2.fetchall()]
        cursor2.execute('SELECT id, username FROM admins WHERE id = %s', (session['admin_id'],))
        admin_record = cursor2.fetchone() or {}
        cursor2.close()
        conn2.close()
    except Exception:
        settings = {}
        blacklist = []
        admin_record = {}

    return render_template(
        'admin_settings.html',
        sys_error=error,
        sys_success=success,
        admin_record=admin_record,
        settings=settings,
        blacklist=blacklist,
        admin_username=session.get('admin_username', 'Admin')
    )


@app.route('/admin-unban/<path:phone>', methods=['POST'])
def admin_unban_phone(phone):
    """Unban a phone number from the settings page."""
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('USE ' + DB_NAME)
        cursor.execute('DELETE FROM blacklist WHERE phone = %s', (phone.strip(),))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f'[UNBAN] {e}')
    return redirect(url_for('admin_settings') + '?unban=1')


# ==================== LOGOUT ROUTES ====================
@app.route('/logout')
def logout():
    """Logout generic user"""
    session.clear()
    return redirect(url_for('home'))

@app.route('/hospital-logout')
def hospital_logout():
    """Logout hospital user"""
    session.clear()
    return redirect(url_for('hospital_login'))

@app.route('/driver-logout')
def driver_logout():
    """Logout driver user"""
    session.clear()
    return redirect(url_for('driver_login'))

# ==================== HOSPITAL ADMIN UPLOAD DRIVER PHOTO ====================
@app.route('/admin/upload-driver-photo', methods=['POST'])
def admin_upload_driver_photo():
    """Allow hospital admin to upload/change driver profile photo"""
    if session.get('user_type') != 'hospital':
        return jsonify({'status': 'error', 'message': 'Only hospital admins can upload driver photos'}), 401
    
    try:
        if 'photo' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        driver_id = request.form.get('driver_id')
        if not driver_id:
            return jsonify({'status': 'error', 'message': 'Driver ID required'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'status': 'error', 'message': 'Invalid file type. Only PNG, JPG, JPEG, GIF allowed'}), 400
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Generate unique filename
        filename = f"driver_{driver_id}_{datetime.now().timestamp()}.png"
        filepath = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(filepath)
        
        # Update driver profile_pic in database
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        photo_path = f"/static/uploads/{filename}"
        
        # Get driver details for logging
        cursor.execute('SELECT username, name FROM drivers WHERE id = %s', (driver_id,))
        driver = cursor.fetchone()
        
        cursor.execute('UPDATE drivers SET profile_pic = %s WHERE id = %s', (photo_path, driver_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        admin_username = session.get('hospital_username') or session.get('username')
        print(f'[DRIVER PHOTO] Admin {admin_username} uploaded photo for driver {driver_id} ({driver["name"] if driver else "Unknown"}): {filename}')
        
        return jsonify({
            'status': 'success',
            'message': f'Photo uploaded successfully for {driver["name"] if driver else "driver"}',
            'photo_path': photo_path
        })
        
    except Exception as e:
        print(f'[DRIVER PHOTO ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== DRIVER PHOTO UPLOAD (DEPRECATED - Hospital Admin Only) ====================
@app.route('/driver-upload-photo', methods=['POST'])
def driver_upload_photo():
    """Deprecated: Use /admin/upload-driver-photo instead. Only hospital admin can upload driver photos."""
    return jsonify({'status': 'error', 'message': 'Drivers cannot upload their own photos. Please contact hospital admin'}), 403

# ==================== DRIVER MARK ATTENDANCE ====================
@app.route('/driver/attendance-check', methods=['GET'])
def driver_attendance_check():
    """Check if driver's attendance is marked for today"""
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Driver ID not found'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT id, status, admin_status FROM attendance_records 
            WHERE driver_id = %s AND date = CURDATE()
        ''', (driver_id,))
        
        record = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if record:
            return jsonify({
                'status': 'success',
                'marked': True,
                'attendance_status': record['status'],
                'admin_status': record['admin_status']
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'marked': False,
                'attendance_status': None,
                'admin_status': None
            }), 200
            
    except Exception as e:
        print(f'[ATTENDANCE-CHECK ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/driver/attendance-records', methods=['GET'])
def driver_attendance_records():
    """Get all attendance records for current month with driver joining date (for calendar coloring)"""
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Driver ID not found'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get driver's joining date
        cursor.execute('''
            SELECT created_at FROM drivers WHERE id = %s
        ''', (driver_id,))
        
        driver = cursor.fetchone()
        joining_date = str(driver['created_at'].date()) if driver and driver['created_at'] else None
        
        # Get all records for current month
        cursor.execute('''
            SELECT date, status, admin_status, leave_reason FROM attendance_records 
            WHERE driver_id = %s 
              AND MONTH(date) = MONTH(CURDATE())
              AND YEAR(date) = YEAR(CURDATE())
            ORDER BY date ASC
        ''', (driver_id,))
        
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert records to dictionary with date as key
        record_dict = {}
        for record in records:
            record_dict[str(record['date'])] = {
                'status': record['status'],
                'admin_status': record['admin_status'],
                'leave_reason': record['leave_reason']
            }
        
        print(f'[ATTENDANCE-RECORDS] Driver {driver_id}: {len(records)} records found for current month, joining date: {joining_date}')
        
        return jsonify({
            'status': 'success',
            'records': record_dict,
            'total_records': len(records),
            'joining_date': joining_date
        }), 200
            
    except Exception as e:
        print(f'[ATTENDANCE-RECORDS ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Handle driver attendance marking (present or leave request)"""
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        status = data.get('status', '').strip()  # 'Present' or 'On Leave'
        leave_reason = data.get('leave_reason', '').strip() if status == 'On Leave' else None
        
        if status not in ['Present', 'On Leave']:
            return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
        
        if status == 'On Leave':
            if not leave_reason:
                return jsonify({'status': 'error', 'message': 'Leave reason required'}), 400
            word_count = len(leave_reason.split())
            if word_count < 3:
                return jsonify({'status': 'error', 'message': 'Leave reason must be at least 3 words'}), 400
        
        driver_username = session.get('driver_username') or session.get('username')
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get driver ID
        cursor.execute('SELECT id FROM drivers WHERE username = %s', (driver_username,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        driver_id = driver['id']
        admin_status = 'pending'
        
        # Handle multi-date leave requests
        leave_from = data.get('leave_from')
        leave_to = data.get('leave_to')
        
        if status == 'On Leave' and leave_from and leave_to:
            # Parse dates
            try:
                from_date = datetime.strptime(leave_from, '%Y-%m-%d').date()
                to_date = datetime.strptime(leave_to, '%Y-%m-%d').date()
                
                if from_date > to_date:
                    cursor.close()
                    conn.close()
                    return jsonify({'status': 'error', 'message': 'From date must be before To date'}), 400
                
                # Generate date range
                date_range = []
                current_date = from_date
                while current_date <= to_date:
                    date_range.append(current_date)
                    current_date += timedelta(days=1)
                
                # Check which dates already have records
                placeholders = ','.join(['%s'] * len(date_range))
                cursor.execute(f'''
                    SELECT date FROM attendance_records 
                    WHERE driver_id = %s AND date IN ({placeholders})
                ''', [driver_id] + date_range)
                
                existing_dates = {record['date'] for record in cursor.fetchall()}
                
                # Insert records for dates that don't exist
                inserted_count = 0
                for current_date in date_range:
                    if current_date not in existing_dates:
                        cursor.execute('''
                            INSERT INTO attendance_records (driver_id, date, status, admin_status, leave_reason)
                            VALUES (%s, %s, %s, %s, %s)
                        ''', (driver_id, current_date, status, admin_status, leave_reason))
                        inserted_count += 1
                
                # Skip existing dates message
                skipped_count = len(date_range) - inserted_count
                
                conn.commit()
                cursor.close()
                conn.close()
                
                message = f'Leave request submitted for {inserted_count} day(s)'
                if skipped_count > 0:
                    message += f'. ({skipped_count} date(s) already marked, skipped)'
                
                print(f'[ATTENDANCE] {driver_username} requested leave from {from_date} to {to_date} ({inserted_count} days inserted, {skipped_count} skipped)')
                return jsonify({'status': 'success', 'message': message})
                
            except ValueError as ve:
                cursor.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
        
        # Handle single date marking (today)
        cursor.execute('''
            SELECT id FROM attendance_records 
            WHERE driver_id = %s AND date = CURDATE()
        ''', (driver_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing attendance
            cursor.execute('''
                UPDATE attendance_records SET status = %s, admin_status = %s, leave_reason = %s 
                WHERE driver_id = %s AND date = CURDATE()
            ''', (status, admin_status, leave_reason, driver_id))
            message = 'Attendance updated successfully'
        else:
            # Insert new attendance record
            cursor.execute('''
                INSERT INTO attendance_records (driver_id, date, status, admin_status, leave_reason)
                VALUES (%s, CURDATE(), %s, %s, %s)
            ''', (driver_id, status, admin_status, leave_reason))
            message = 'Attendance marked successfully'
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[ATTENDANCE] {driver_username} marked {status} for today')
        return jsonify({'status': 'success', 'message': message})
        
    except Exception as e:
        print(f'[ATTENDANCE ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOSPITAL REGISTER ROUTE ====================
@app.route('/hospital-register', methods=['GET'])
def hospital_register_get():
    """Show hospital self-registration form"""
    return render_template('hospital_register.html',
                           google_maps_api_key=GOOGLE_MAPS_API_KEY)


@app.route('/hospital-register', methods=['POST'])
def hospital_register_post():
    """Process hospital self-registration submission"""
    try:
        data                = request.get_json() or {}
        hospital_name       = data.get('hospital_name', '').strip()
        hospital_type       = data.get('hospital_type', '').strip()
        registration_number = data.get('registration_number', '').strip()
        latitude            = data.get('latitude', None)
        longitude           = data.get('longitude', None)
        address             = data.get('address', '').strip()
        contact_name        = data.get('contact_name', '').strip()
        phone               = data.get('phone', '').strip()
        email               = data.get('email', '').strip()
        username            = data.get('username', '').strip()
        password            = data.get('password', '')
        confirm_password    = data.get('confirm_password', '')

        # Basic field checks
        if not all([hospital_name, username, password, email]):
            return jsonify({'success': False,
                            'message': 'Hospital name, username, email, and password are required.'})

        # Password match
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'})

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE ' + DB_NAME)

        # Duplicate username check
        cursor.execute('SELECT id FROM hospitals WHERE username = %s', (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False,
                            'message': 'This username is already taken. Please choose another.'})

        # Duplicate email check
        cursor.execute('SELECT id FROM hospitals WHERE email = %s', (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False,
                            'message': 'This email is already registered.'})

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        lat_val = float(latitude)  if latitude  not in (None, '', '0') else None
        lng_val = float(longitude) if longitude not in (None, '', '0') else None

        cursor2 = conn.cursor()
        cursor2.execute('''
            INSERT INTO hospitals
                (username, password, name, address, phone, email,
                 latitude, longitude, status,
                 hospital_type, registration_number, contact_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            username, hashed_password, hospital_name, address, phone, email,
            lat_val, lng_val, 'pending',
            hospital_type, registration_number, contact_name
        ))
        conn.commit()
        cursor2.close()
        cursor.close()
        conn.close()

        print(f'[HOSPITAL REGISTER] New registration: {hospital_name} ({username}) — status=pending')
        return jsonify({'success': True,
                        'message': 'Registration submitted successfully!'})

    except Exception as e:
        print(f'[HOSPITAL REGISTER ERROR] {e}')
        return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500


# ==================== HOSPITAL LOGIN ROUTE ====================
@app.route('/hospital-login', methods=['GET', 'POST'])
def hospital_login():
    """Handle hospital staff authentication and login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        hospital = get_hospital_by_username(username)
        
        if hospital and check_password_hash(hospital['password'], password):
            # Check approval status before granting access
            h_status = hospital.get('status', 'approved')
            if h_status == 'pending':
                conn2 = get_db()
                cursor2 = conn2.cursor(dictionary=True)
                cursor2.execute('SELECT username FROM hospitals')
                hospitals_list = [h['username'] for h in cursor2.fetchall()]
                cursor2.close()
                conn2.close()
                return render_template('hospital_login.html',
                    error='Your registration is under review. You will be activated once admin approves your account.',
                    demo_users=hospitals_list)
            if h_status == 'rejected':
                reason = hospital.get('rejection_reason') or 'No reason provided'
                conn2 = get_db()
                cursor2 = conn2.cursor(dictionary=True)
                cursor2.execute('SELECT username FROM hospitals')
                hospitals_list = [h['username'] for h in cursor2.fetchall()]
                cursor2.close()
                conn2.close()
                return render_template('hospital_login.html',
                    error=f'Your registration was rejected. Reason: {reason}',
                    demo_users=hospitals_list)

            session.clear()
            session['user_type'] = 'hospital'
            session['username'] = hospital['username']
            session['hospital_id'] = hospital['id']
            session['hospital_name'] = hospital['name']
            session.permanent = True
            session.modified = True
            
            print(f'[HOSPITAL LOGIN] {username} ({hospital["name"]}) logged in')
            return redirect(url_for('hospital_dashboard'))
        else:
            # Get all hospitals for demo display
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT username FROM hospitals')
            hospitals = [h['username'] for h in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return render_template('hospital_login.html',
                                   error='Invalid username or password',
                                   demo_users=hospitals)
    
    # GET request - show login form with demo credentials
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT username FROM hospitals')
    hospitals = [h['username'] for h in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return render_template('hospital_login.html', demo_users=hospitals)

# ==================== HOSPITAL DASHBOARD ====================
@app.route('/hospital-dashboard')
def hospital_dashboard():
    """Display hospital management dashboard"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return redirect(url_for('hospital_login'))
    
    username = session.get('username')
    hospital = get_hospital_by_username(username)
    
    if not hospital:
        return redirect(url_for('hospital_login'))
    
    # GET ONLY ESSENTIAL DATA FOR INITIAL PAGE LOAD
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get assigned drivers (critical for display)
    cursor.execute('''
        SELECT id, username, name, assigned_ambulance, status, phone, experience 
        FROM drivers WHERE hospital_id = %s LIMIT 10
    ''', (hospital['id'],))
    assigned_drivers = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Prepare minimal dashboard data
    dashboard_data = {
        'hospital_name': hospital['name'],
        'hospital_address': hospital['address'],
        'hospital_phone': hospital['phone'],
        'hospital_email': hospital['email'],
        'total_beds': hospital['total_beds'],
        'available_beds': hospital['available_beds'],
        'occupied_beds': hospital['total_beds'] - hospital['available_beds'],
        'assigned_drivers': assigned_drivers,
        'specialties': hospital['specialties'] if isinstance(hospital['specialties'], list) else [],
        'hospital_lat': float(hospital['latitude']) if hospital.get('latitude') else 31.5204,
        'hospital_lng': float(hospital['longitude']) if hospital.get('longitude') else 74.3587
    }
    
    return render_template('hospital_dashboard.html', data=dashboard_data)

# ==================== HOSPITAL DASHBOARD STATS (ASYNC LOAD) ====================
@app.route('/get-hospital-dashboard-stats', methods=['GET'])
def get_hospital_dashboard_stats():
    """Get hospital dashboard statistics (called asynchronously after page load)"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Count incoming ambulances (active dispatches)
        cursor.execute('''
            SELECT COUNT(*) as count FROM dispatches 
            WHERE hospital_id = %s AND status IN ('dispatched', 'en_route')
        ''', (hospital_id,))
        incoming_ambulances = cursor.fetchone()['count']
        
        # Count active emergency cases
        cursor.execute('''
            SELECT COUNT(*) as count FROM patient_requests 
            WHERE hospital_id = %s AND status NOT IN ('completed', 'no_hospital_available')
        ''', (hospital_id,))
        emergency_cases = cursor.fetchone()['count']
        
        # Get ambulances
        cursor.execute('''
            SELECT a.ambulance_number, a.status, a.type
            FROM ambulances a
            WHERE a.hospital_id = %s
            ORDER BY a.status DESC, a.created_at ASC LIMIT 20
        ''', (hospital_id,))
        ambulances_in_area = []
        for amb in cursor.fetchall():
            ambulances_in_area.append({
                'id': amb['ambulance_number'],
                'status': amb['status'],
                'type': amb['type'],
                'eta': '...'
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'incoming_ambulances': incoming_ambulances,
            'emergency_cases': emergency_cases,
            'ambulances_in_area': ambulances_in_area
        })
    
    except Error as e:
        print(f'[DB ERROR] get_hospital_dashboard_stats: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOSPITAL PROFILE ROUTES ====================
@app.route('/hospital-profile')
def hospital_profile():
    """Redirect hospital profile to dashboard profile section"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return redirect(url_for('hospital_login'))
    return redirect(url_for('hospital_dashboard'))

@app.route('/get-hospital-profile-data', methods=['GET'])
def get_hospital_profile_data():
    """Get hospital profile data with computed fields"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get hospital data
        cursor.execute('SELECT * FROM hospitals WHERE id = %s', (hospital_id,))
        hospital = cursor.fetchone()
        
        if not hospital:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
        
        # Count drivers
        cursor.execute('SELECT COUNT(*) as count FROM drivers WHERE hospital_id = %s', (hospital_id,))
        driver_count = cursor.fetchone()['count']
        
        # Count ambulances
        cursor.execute('SELECT COUNT(*) as count FROM ambulances WHERE hospital_id = %s', (hospital_id,))
        ambulance_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        # Calculate total beds
        general_beds = hospital.get('general_beds', 0) or 0
        icu_beds = hospital.get('icu_beds', 0) or 0
        emergency_beds = hospital.get('emergency_beds', 0) or 0
        total_beds = general_beds + icu_beds + emergency_beds
        
        # Parse specialties safely
        try:
            specialties = hospital.get('specialties', '[]')
            if isinstance(specialties, str):
                import json
                specialties = json.loads(specialties) if specialties else []
            elif specialties is None:
                specialties = []
        except:
            specialties = []
        
        # Parse operating_hours safely
        try:
            operating_hours = hospital.get('operating_hours')
            if isinstance(operating_hours, str):
                import json
                operating_hours = json.loads(operating_hours) if operating_hours else {}
            elif operating_hours is None:
                operating_hours = {}
        except:
            operating_hours = {}
        
        # Build response with all fields converted to strings
        response = {
            'status': 'success',
            'hospital': {
                'id': str(hospital['id']),
                'name': hospital.get('name', ''),
                'phone': hospital.get('phone', ''),
                'whatsapp': hospital.get('whatsapp', ''),
                'email': hospital.get('email', ''),
                'address': hospital.get('address', ''),
                'website': hospital.get('website', ''),
                'hospital_type': hospital.get('hospital_type', 'Private'),
                'latitude': str(hospital.get('latitude', '')),
                'longitude': str(hospital.get('longitude', '')),
                'gps_latitude': str(hospital.get('gps_latitude', '')),
                'gps_longitude': str(hospital.get('gps_longitude', '')),
                'general_beds': str(hospital.get('general_beds', 0) or 0),
                'icu_beds': str(hospital.get('icu_beds', 0) or 0),
                'emergency_beds': str(hospital.get('emergency_beds', 0) or 0),
                'total_beds': str(total_beds),
                'doctors_count': str(hospital.get('doctors_count', 0) or 0),
                'nurses_count': str(hospital.get('nurses_count', 0) or 0),
                'specialties': specialties,
                'operating_hours': operating_hours,
                'cover_photo': hospital.get('cover_photo', ''),
                'logo_photo': hospital.get('logo_photo', ''),
                'registration_certificate': hospital.get('registration_certificate', ''),
                'is_verified': bool(hospital.get('is_verified', False)),
                'driver_count': str(driver_count),
                'ambulance_count': str(ambulance_count)
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print(f'[GET HOSPITAL PROFILE ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update-hospital-profile', methods=['POST'])
def update_hospital_profile():
    """Update hospital profile"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        
        # Validate required fields
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        
        if not name or not phone or not email:
            return jsonify({'status': 'error', 'message': 'Name, phone, and email are required'}), 400
        
        # Extract all fields
        whatsapp = data.get('whatsapp', '').strip()
        address = data.get('address', '').strip()
        website = data.get('website', '').strip()
        hospital_type = data.get('hospital_type', 'Private').strip()
        latitude = data.get('latitude', '')
        longitude = data.get('longitude', '')
        gps_latitude = data.get('latitude', '')  # Also update gps_latitude
        gps_longitude = data.get('longitude', '')  # Also update gps_longitude
        general_beds = data.get('general_beds', 0)
        icu_beds = data.get('icu_beds', 0)
        emergency_beds = data.get('emergency_beds', 0)
        doctors_count = data.get('doctors_count', 0)
        nurses_count = data.get('nurses_count', 0)
        specialties = data.get('specialties', [])
        operating_hours = data.get('operating_hours', {})
        
        # Convert to proper types
        try:
            general_beds = int(general_beds) if general_beds else 0
            icu_beds = int(icu_beds) if icu_beds else 0
            emergency_beds = int(emergency_beds) if emergency_beds else 0
            doctors_count = int(doctors_count) if doctors_count else 0
            nurses_count = int(nurses_count) if nurses_count else 0
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None
            gps_latitude = float(gps_latitude) if gps_latitude else None
            gps_longitude = float(gps_longitude) if gps_longitude else None
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Invalid numeric values'}), 400
        
        # Convert specialties and operating_hours to JSON strings
        import json
        specialties_json = json.dumps(specialties)
        operating_hours_json = json.dumps(operating_hours)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE hospitals SET
                name = %s,
                phone = %s,
                whatsapp = %s,
                email = %s,
                address = %s,
                website = %s,
                hospital_type = %s,
                latitude = %s,
                longitude = %s,
                gps_latitude = %s,
                gps_longitude = %s,
                general_beds = %s,
                icu_beds = %s,
                emergency_beds = %s,
                doctors_count = %s,
                nurses_count = %s,
                specialties = %s,
                operating_hours = %s
            WHERE id = %s
        ''', (
            name, phone, whatsapp, email, address, website, hospital_type,
            latitude, longitude, gps_latitude, gps_longitude,
            general_beds, icu_beds, emergency_beds, doctors_count, nurses_count,
            specialties_json, operating_hours_json, hospital_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[HOSPITAL PROFILE UPDATE] Hospital {hospital_id} profile updated')
        
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully',
            'hospital': {
                'id': hospital_id,
                'name': name,
                'phone': phone,
                'email': email
            }
        }), 200
    
    except Exception as e:
        print(f'[UPDATE HOSPITAL PROFILE ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload-hospital-logo', methods=['POST'])
def upload_hospital_logo():
    """Upload hospital logo"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        if 'logo' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Validate file type and size
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'status': 'error', 'message': 'Only PNG, JPG, JPEG, GIF files allowed'}), 400
        
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 2 * 1024 * 1024:  # 2MB
            return jsonify({'status': 'error', 'message': 'File must be under 2MB'}), 400
        
        # Create directory if it doesn't exist
        photos_dir = os.path.join('static', 'hospital_photos')
        if not os.path.exists(photos_dir):
            os.makedirs(photos_dir)
        
        # Generate unique filename
        filename = f"hospital_{hospital_id}_logo_{int(datetime.now().timestamp())}.png"
        filepath = os.path.join(photos_dir, filename)
        
        # Save file
        file.save(filepath)
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        photo_url = f"/static/hospital_photos/{filename}"
        cursor.execute('UPDATE hospitals SET logo_photo = %s WHERE id = %s', (photo_url, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[HOSPITAL LOGO UPLOAD] Hospital {hospital_id}: {filename}')
        return jsonify({'status': 'success', 'photo_url': photo_url}), 200
    
    except Exception as e:
        print(f'[UPLOAD HOSPITAL LOGO ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload-hospital-cover', methods=['POST'])
def upload_hospital_cover():
    """Upload hospital cover photo"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        if 'cover' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['cover']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Validate file type and size
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'status': 'error', 'message': 'Only PNG, JPG, JPEG, GIF files allowed'}), 400
        
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 2 * 1024 * 1024:  # 2MB
            return jsonify({'status': 'error', 'message': 'File must be under 2MB'}), 400
        
        # Create directory if it doesn't exist
        photos_dir = os.path.join('static', 'hospital_photos')
        if not os.path.exists(photos_dir):
            os.makedirs(photos_dir)
        
        # Generate unique filename
        filename = f"hospital_{hospital_id}_cover_{int(datetime.now().timestamp())}.png"
        filepath = os.path.join(photos_dir, filename)
        
        # Save file
        file.save(filepath)
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        photo_url = f"/static/hospital_photos/{filename}"
        cursor.execute('UPDATE hospitals SET cover_photo = %s WHERE id = %s', (photo_url, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[HOSPITAL COVER UPLOAD] Hospital {hospital_id}: {filename}')
        return jsonify({'status': 'success', 'photo_url': photo_url}), 200
    
    except Exception as e:
        print(f'[UPLOAD HOSPITAL COVER ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload-hospital-certificate', methods=['POST'])
def upload_hospital_certificate():
    """Upload hospital registration certificate"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        if 'certificate' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['certificate']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Validate file type and size
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'status': 'error', 'message': 'Only PDF, PNG, JPG, JPEG files allowed'}), 400
        
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'status': 'error', 'message': 'File must be under 5MB'}), 400
        
        # Create directory if it doesn't exist
        docs_dir = os.path.join('static', 'hospital_documents')
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)
        
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"hospital_{hospital_id}_certificate_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(docs_dir, filename)
        
        # Save file
        file.save(filepath)
        
        # Update database
        conn = get_db()
        cursor = conn.cursor()
        file_url = f"/static/hospital_documents/{filename}"
        cursor.execute('UPDATE hospitals SET registration_certificate = %s WHERE id = %s', (file_url, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[HOSPITAL CERTIFICATE UPLOAD] Hospital {hospital_id}: {filename}')
        return jsonify({'status': 'success', 'file_url': file_url}), 200
    
    except Exception as e:
        print(f'[UPLOAD HOSPITAL CERTIFICATE ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== USER LOGIN ====================
@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    """Handle user authentication"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = get_user_by_username(username)
        
        if user and user['password'] == password:
            session.permanent = True
            session['user_type'] = 'user'
            session['username'] = username
            session['name'] = user['name']
            session['email'] = user['email']
            session['patient_name'] = user['name']
            session['patient_phone'] = user['phone']
            session.modified = True
            
            print(f'[USER LOGIN] {username} ({user["name"]}) logged in')
            return redirect(url_for('user_dashboard'))
        else:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT username FROM users')
            demo_users = [u['username'] for u in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return render_template('user_login.html', 
                                   error='Invalid username or password',
                                   demo_users=demo_users)
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT username FROM users')
    demo_users = [u['username'] for u in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return render_template('user_login.html', demo_users=demo_users)

# ==================== USER SMART LOGIN (CNIC-based) ====================
@app.route('/user-smart-login', methods=['POST'])
def user_smart_login():
    """
    Smart Patient Authentication with CNIC and Phone
    - Validates CNIC and Phone Number together
    - Auto-registers new patients
    
    @route POST /user-smart-login
    @return JSON: {success: bool, user_id: str, message: str}
    """
    conn = None
    cursor = None
    try:
        import traceback
        
        # Get JSON data from request
        data = request.get_json()
        
        cnic = data.get('cnic', '').strip()
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validate input
        if not cnic or not full_name or not phone:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Validate CNIC format (13 digits)
        cnic_digits_only = ''.join(c for c in cnic if c.isdigit())
        if len(cnic_digits_only) != 13:
            return jsonify({
                'success': False,
                'message': 'CNIC must contain exactly 13 digits'
            }), 400
        
        # Validate phone format (exactly 11 digits, starts with 03)
        if len(phone) != 11 or not phone.startswith('03') or not phone.isdigit():
            return jsonify({
                'success': False,
                'message': 'Phone number must be 11 digits starting with 03 (e.g., 03001234567)'
            }), 400
        
        # Open fresh MySQL connection
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='smartambulance'
        )
        cursor = conn.cursor(dictionary=True)
        
        # Check if CNIC exists in database
        cursor.execute('SELECT * FROM users WHERE cnic = %s', (cnic,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # CNIC found - verify phone matches same record
            if existing_user['phone'] == phone:
                # Phone matches - allow login
                session.permanent = True
                session['user_type'] = 'patient'
                session['patient_cnic'] = cnic
                session['patient_name'] = existing_user['full_name']
                session['patient_phone'] = existing_user['phone']
                session.modified = True
                
                print(f'[PATIENT LOGIN] {existing_user["full_name"]} ({cnic}) logged in successfully')
                
                return jsonify({
                    'success': True,
                    'user_id': cnic,
                    'message': 'Welcome back! Logging in...'
                }), 200
            else:
                # Phone doesn't match - invalid credentials
                print(f'[LOGIN FAILED] CNIC {cnic} with mismatched phone: {phone}')
                return jsonify({
                    'success': False,
                    'message': 'Invalid credentials'
                }), 401
        
        # CNIC not found - check if phone already exists
        cursor.execute('SELECT * FROM users WHERE phone = %s', (phone,))
        phone_exists = cursor.fetchone()
        
        if phone_exists:
            # Phone already registered
            print(f'[REGISTRATION FAILED] Phone already registered: {phone}')
            return jsonify({
                'success': False,
                'message': 'This phone number is already registered'
            }), 409
        
        # Phone is free - insert new user record
        now = datetime.now()
        cursor.execute('''
            INSERT INTO users (cnic, full_name, phone, user_type, registered_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (cnic, full_name, phone, 'patient', now))
        
        conn.commit()
        
        # Create session
        session.permanent = True
        session['user_type'] = 'patient'
        session['patient_cnic'] = cnic
        session['patient_name'] = full_name
        session['patient_phone'] = phone
        session.modified = True
        
        print(f'[PATIENT REGISTRATION] {full_name} ({cnic}) registered and logged in successfully')
        
        return jsonify({
            'success': True,
            'user_id': cnic,
            'message': 'Account created and logged in successfully!'
        }), 200
    
    except Exception as e:
        import traceback
        print('[USER LOGIN ERROR]', traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==================== USER UPDATE PROFILE ====================
@app.route('/user-update-profile', methods=['POST'])
def user_update_profile():
    """
    Update patient profile information
    - Full Name and Phone can be updated
    - CNIC cannot be changed
    - Phone number cannot be changed to one already in use
    
    @route POST /user-update-profile
    @return JSON: {success: bool, message: str}
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        cnic = data.get('cnic', '').strip()
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validate input
        if not cnic or not full_name or not phone:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Validate full name
        if len(full_name) < 3:
            return jsonify({
                'success': False,
                'message': 'Full name must be at least 3 characters'
            }), 400
        
        # Validate phone format (exactly 11 digits, starts with 03)
        if len(phone) != 11 or not phone.startswith('03') or not phone.isdigit():
            return jsonify({
                'success': False,
                'message': 'Phone number must be 11 digits starting with 03 (e.g., 03001234567)'
            }), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Check if CNIC exists
        cursor.execute('SELECT id, full_name, phone FROM users WHERE cnic = %s', (cnic,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            print(f'[PROFILE UPDATE FAILED] Patient not found: {cnic}')
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': False,
                'message': 'Patient not found'
            }), 404
        
        # Check if phone number is being changed
        if existing_user['phone'] != phone:
            # Phone number is being changed - check if new phone is already in use
            cursor.execute('SELECT id FROM users WHERE phone = %s AND cnic != %s', (phone, cnic))
            if cursor.fetchone():
                # New phone number already in use by another account
                print(f'[PROFILE UPDATE FAILED] Duplicate phone number attempt: {phone}')
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': False,
                    'message': 'This phone number is already registered'
                }), 409
        
        # Update patient profile in database
        now = datetime.now()
        cursor.execute('''
            UPDATE users 
            SET full_name = %s, phone = %s, updated_at = %s
            WHERE cnic = %s
        ''', (full_name, phone, now, cnic))
        
        conn.commit()
        
        # Update session if user is currently logged in
        if 'patient_cnic' in session and session['patient_cnic'] == cnic:
            session['patient_name'] = full_name
            session['patient_phone'] = phone
        
        print(f'[PATIENT PROFILE UPDATE] {full_name} ({cnic}) profile updated - Phone: {phone}')
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200
    
    except Exception as e:
        print(f'[USER LOGIN ERROR] {e}')
        return jsonify({
            'success': False,
            'message': 'Server error during profile update'
        }), 500

# ==================== USER DASHBOARD ====================
@app.route('/user-dashboard')
def user_dashboard():
    """Display user dashboard"""
    if 'user_type' not in session or session['user_type'] != 'user':
        return redirect(url_for('user_login'))
    
    username = session.get('username')
    user = get_user_by_username(username)
    
    if not user:
        return redirect(url_for('user_login'))
    
    dashboard_data = {
        'user_name': user['name'],
        'email': user['email'],
        'phone': user['phone'],
        'address': user['address'],
        'blood_type': user['blood_type'],
        'medical_history': user['medical_history'],
        'emergency_contacts': user['emergency_contacts'] if isinstance(user['emergency_contacts'], list) else [],
        'request_history': []
    }
    
    return render_template('user_dashboard.html', data=dashboard_data)

# ==================== HOSPITAL API ROUTES ====================

@app.route('/check-session', methods=['GET'])
def check_session():
    """Debug endpoint to check session status"""
    return jsonify({
        'user_type': session.get('user_type'),
        'hospital_id': session.get('hospital_id'),
        'hospital_name': session.get('hospital_name'),
        'username': session.get('username')
    })

@app.route('/get-hospital-requests', methods=['GET'])
def get_hospital_requests():
    """Get all patient requests for the logged-in hospital"""
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        print(f'[SESSION] hospital_id is missing. Session data: {dict(session)}')
        return jsonify({'status': 'error', 'error': 'Not logged in'}), 401
    
    session.modified = True
    hospital_name = session.get('hospital_name', 'Unknown')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Query pending + assigned + en_route requests for this hospital
    cursor.execute('''
        SELECT pr.*,
               h.name as hospital_name,
               d.dispatch_id,
               d.driver_id as dispatch_driver_id,
               d.ambulance_id as dispatch_ambulance,
               dr.name as driver_name
        FROM patient_requests pr
        JOIN hospitals h ON pr.hospital_id = h.id
        LEFT JOIN dispatches d ON pr.request_id = d.request_id
            AND d.status NOT IN ('driver_rejected', 'completed')
        LEFT JOIN drivers dr ON d.driver_id = dr.id
        WHERE pr.hospital_id = %s
          AND pr.status IN ('pending', 'assigned', 'en_route')
        GROUP BY pr.request_id
        ORDER BY FIELD(pr.status,'pending','assigned','en_route'), pr.timestamp DESC
    ''', (hospital_id,))
    requests = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert datetime objects to strings
    for req in requests:
        for key in ('timestamp', 'locked_at', 'created_at'):
            if req.get(key) and hasattr(req[key], 'isoformat'):
                req[key] = req[key].isoformat()

    print(f'[DEBUG] Hospital {hospital_name} (ID: {hospital_id}) has {len(requests)} active requests')
    
    return jsonify({
        'status': 'success',
        'hospital': hospital_name,
        'hospital_id': hospital_id,
        'count': len(requests),
        'requests': requests
    }), 200

@app.route('/accept-request', methods=['POST'])
def accept_request():
    """Accept a patient request and assign ambulance"""
    # Check credentials
    if session.get('user_type') != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'error': 'Please login again'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        request_id = data.get('request_id')
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get request
        cursor.execute('SELECT * FROM patient_requests WHERE request_id = %s', (request_id,))
        req = cursor.fetchone()
        
        if not req:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Request not found', 'status': 404}), 404
        
        # Find available driver from this hospital using hospital_id
        cursor.execute('''
            SELECT * FROM drivers 
            WHERE hospital_id = %s AND status = 'Available' 
            AND assigned_ambulance IS NOT NULL
            LIMIT 1
        ''', (hospital_id,))
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No ambulance available. All ambulances are currently on duty. Please wait for one to become free.', 'status': 400}), 400
        
        print(f'[ACCEPT] request_id={request_id}')
        print(f'[ACCEPT] driver found: {driver}')

        # Update request status to 'assigned' and store driver
        cursor.execute('''
            UPDATE patient_requests SET status = 'assigned', assigned_driver = %s, assigned_driver_id = %s, locked = 1, locked_at = NOW()
            WHERE request_id = %s
        ''', (driver['username'], driver['id'], request_id))

        # Update driver status to On Duty
        cursor.execute('UPDATE drivers SET status = %s WHERE id = %s', ('On Duty', driver['id']))
        cursor.execute("UPDATE ambulances SET status = 'On Duty' WHERE ambulance_number = %s", (driver['assigned_ambulance'],))
        # Auto assign next available ambulance to drivers who have none
        cursor.execute('''SELECT ambulance_number FROM ambulances 
            WHERE hospital_id = %s AND status = 'Available'
            AND ambulance_number NOT IN (
                SELECT assigned_ambulance FROM drivers 
                WHERE assigned_ambulance IS NOT NULL AND hospital_id = %s
            )
            LIMIT 1''', (hospital_id, hospital_id))
        free_amb = cursor.fetchone()
        if free_amb:
            cursor.execute('''UPDATE drivers SET assigned_ambulance = %s 
                WHERE hospital_id = %s 
                AND status = 'Available' 
                AND assigned_ambulance IS NULL 
                LIMIT 1''', (free_amb['ambulance_number'], hospital_id))
        
        # Create dispatch record with status='dispatched'
        dispatch_id = f"DSP-2026-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute('''
            INSERT INTO dispatches (dispatch_id, request_id, patient_name, patient_phone, location, driver_id, driver_name, ambulance_id, hospital_id, status, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (dispatch_id, request_id, req['patient_name'], req['patient_phone'], req['pickup_address'],
              driver['id'], driver['name'], driver['assigned_ambulance'], driver['hospital_id'], 'dispatched', req.get('priority', 'Medium')))

        conn.commit()
        cursor.close()
        conn.close()

        print(f'[ACCEPT] dispatch created: {dispatch_id}')
        print(f'[ACCEPT REQUEST] {request_id} assigned to {driver["name"]} (driver_id={driver["id"]})')
        
        return jsonify({
            'status': 'success',
            'message': f'Request accepted and assigned to {driver["name"]}',
            'driver_info': {
                'id': driver['id'],
                'name': driver['name'],
                'phone': driver['phone'],
                'ambulance': driver['assigned_ambulance'],
                'status': 'On Duty'
            }
        }), 200
    
    except Exception as e:
        print(f'[ACCEPT ERROR] {str(e)}')
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/reject-request', methods=['POST'])
def reject_request():
    """Reject a patient request"""
    # Check credentials
    if session.get('user_type') != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'error': 'Please login again'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        request_id = data.get('request_id')
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Update request status to rejected for this hospital
        cursor.execute('''
            UPDATE patient_requests 
            SET status = 'rejected' 
            WHERE request_id = %s AND hospital_id = %s
        ''', (request_id, hospital_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[REJECT REQUEST] {request_id} marked as rejected by hospital {hospital_id}')
        
        return jsonify({
            'status': 'success',
            'message': 'Request rejected'
        }), 200
    
    except Exception as e:
        print(f'[REJECT ERROR] {str(e)}')
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/update-beds', methods=['POST'])
def update_beds():
    """Update available beds count"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        available_beds = int(data.get('available_beds', 0))
        hospital_id = session.get('hospital_id')
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT total_beds FROM hospitals WHERE id = %s', (hospital_id,))
        hospital = cursor.fetchone()
        
        if not hospital:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Hospital not found', 'status': 404}), 404
        
        total_beds = hospital['total_beds']
        if available_beds < 0 or available_beds > total_beds:
            cursor.close()
            conn.close()
            return jsonify({
                'error': f'Invalid bed count. Must be between 0 and {total_beds}',
                'status': 400
            }), 400
        
        # Update beds
        cursor.execute('''
            UPDATE hospitals SET available_beds = %s WHERE id = %s
        ''', (available_beds, hospital_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[UPDATE BEDS] Hospital updated beds to {available_beds}/{total_beds}')
        
        return jsonify({
            'status': 'success',
            'message': 'Beds updated successfully',
            'available_beds': available_beds,
            'occupied_beds': total_beds - available_beds,
            'total_beds': total_beds
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 500}), 500

@app.route('/update-total-beds', methods=['POST'])
def update_total_beds():
    """Update total bed count for hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'success': False}), 401
    
    try:
        hospital_id = session.get('hospital_id')
        data = request.get_json() if request.is_json else request.form.to_dict()
        total_beds = int(data.get('total_beds', 0))
        
        if total_beds < 0:
            return jsonify({'success': False, 'error': 'Total beds cannot be negative'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get current available beds
        cursor.execute('SELECT available_beds FROM hospitals WHERE id = %s', (hospital_id,))
        hospital = cursor.fetchone()
        
        if not hospital:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Hospital not found'}), 404
        
        # If new total is less than current available, cap available at new total
        available_beds = min(hospital['available_beds'], total_beds)
        
        # Update both total and available beds
        cursor.execute('''
            UPDATE hospitals SET total_beds = %s, available_beds = %s WHERE id = %s
        ''', (total_beds, available_beds, hospital_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add-driver', methods=['POST'])
def add_driver():
    """Add a new driver to the hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    hospital_username = session.get('username')
    
    try:
        import traceback
        
        data = request.get_json()
        driver_name = data.get('driver_name', '').strip()
        phone = data.get('phone', '').strip()
        cnic = data.get('cnic', '').strip()
        experience_years = int(data.get('experience_years', 0))
        assigned_ambulance = data.get('assigned_ambulance', None)
        shift = data.get('shift', 'Any')
        
        # Handle empty ambulance values - set to None to avoid FK constraint issues
        if not assigned_ambulance or assigned_ambulance == '' or assigned_ambulance == 'null' or assigned_ambulance == 'undefined':
            assigned_ambulance = None
        
        if not all([driver_name, phone, cnic]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
        
        # Generate credentials
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Use MAX numeric suffix to avoid collisions when drivers are deleted
            cursor.execute("SELECT username FROM drivers WHERE username LIKE 'DRV-%'")
            existing = [row['username'] for row in cursor.fetchall()]
            max_num = 0
            for uname in existing:
                try:
                    max_num = max(max_num, int(uname.split('-')[1]))
                except (IndexError, ValueError):
                    pass
            candidate = max_num + 1
            # Keep incrementing until we find a username not already taken
            while True:
                driver_username = f'DRV-{str(candidate).zfill(3)}'
                cursor.execute('SELECT id FROM drivers WHERE username = %s', (driver_username,))
                if not cursor.fetchone():
                    break
                candidate += 1
            driver_password = str(random.randint(100000, 999999))
            
            # Auto assign first available ambulance that has no driver
            cursor.execute('''SELECT ambulance_number FROM ambulances 
                WHERE hospital_id = %s AND status = 'Available'
                AND ambulance_number NOT IN (SELECT assigned_ambulance FROM drivers WHERE assigned_ambulance IS NOT NULL AND hospital_id = %s)
                LIMIT 1''', (hospital_id, hospital_id))
            available_amb = cursor.fetchone()
            auto_ambulance = available_amb['ambulance_number'] if available_amb else None
            
            # Create driver - columns must match drivers table exactly
            insert_query = '''
                INSERT INTO drivers (username, password, name, phone, cnic, experience, shift, assigned_ambulance, status, hospital_id, certifications)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            
            cursor.execute(insert_query, (
                driver_username,
                driver_password,
                driver_name,
                phone,
                cnic,
                experience_years,
                shift,
                auto_ambulance,
                'Available',
                hospital_id,
                '["Basic EMT"]'
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f'[ADD DRIVER] Hospital {hospital_username} added driver {driver_username} ({driver_name})')
            
            return jsonify({
                'status': 'success',
                'message': f'Driver {driver_name} added successfully',
                'driver_username': driver_username,
                'driver_password': driver_password
            }), 201
            
        except Exception as sql_error:
            cursor.close()
            conn.close()
            print(f'[ADD DRIVER SQL ERROR] {str(sql_error)}')
            print(traceback.format_exc())
            return jsonify({'status': 'error', 'message': f'Database error: {str(sql_error)}'}), 500
    
    except Exception as e:
        print(f'[ADD DRIVER ERROR] {str(e)}')
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/remove-driver', methods=['POST'])
def remove_driver():
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    session.modified = True
    hospital_id = session.get('hospital_id')
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        if not driver_id:
            return jsonify({'status': 'error', 'message': 'Driver ID required'}), 400
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT name, assigned_ambulance FROM drivers WHERE id = %s AND hospital_id = %s', (driver_id, hospital_id))
        driver = cursor.fetchone()
        if not driver:
            cursor.close(); conn.close()
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        if driver['assigned_ambulance']:
            cursor.execute("UPDATE ambulances SET status = 'Available' WHERE ambulance_number = %s", (driver['assigned_ambulance'],))
        cursor.execute('DELETE FROM drivers WHERE id = %s AND hospital_id = %s', (driver_id, hospital_id))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'status': 'success', 'message': f"Driver {driver['name']} removed"}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get-drivers', methods=['GET'])
def get_drivers():
    """Get all drivers for the hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT d.id, d.username, d.password, d.name, d.phone, d.cnic, d.experience,
               d.assigned_ambulance, d.certifications, d.shift, d.created_at,
               d.current_latitude, d.current_longitude, d.location_updated_at,
               d.profile_pic,
               CASE
                   WHEN EXISTS (
                       SELECT 1 FROM dispatches disp
                       WHERE disp.driver_id = d.id
                       AND disp.status NOT IN ("completed", "driver_rejected")
                   ) THEN "On Duty"
                   ELSE "Available"
               END AS status
        FROM drivers d WHERE d.hospital_id = %s
    ''', (hospital_id,))
    drivers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert datetime objects to strings
    for driver in drivers:
        if driver.get('created_at') and hasattr(driver['created_at'], 'isoformat'):
            driver['created_at'] = driver['created_at'].isoformat()
        if driver.get('location_updated_at') and hasattr(driver['location_updated_at'], 'isoformat'):
            driver['location_updated_at'] = driver['location_updated_at'].isoformat()
        # Flag whether GPS is fresh (within last 60 seconds)
        from datetime import datetime as _dt, timedelta as _td
        if driver.get('location_updated_at'):
            try:
                updated = _dt.fromisoformat(driver['location_updated_at'])
                driver['gps_live'] = (_dt.now() - updated).total_seconds() <= 60
            except Exception:
                driver['gps_live'] = False
        else:
            driver['gps_live'] = False
        # Convert Decimal GPS fields to float
        driver['current_latitude']  = float(driver['current_latitude'])  if driver.get('current_latitude')  else None
        driver['current_longitude'] = float(driver['current_longitude']) if driver.get('current_longitude') else None
    
    return jsonify({
        'status': 'success',
        'count': len(drivers),
        'drivers': drivers
    }), 200

@app.route('/add-ambulance', methods=['POST'])
def add_ambulance():
    """Add a new ambulance to the hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    
    try:
        data = request.get_json()
        ambulance_id = (data.get('ambulance_number') or data.get('ambulance_id', '')).strip()
        ambulance_type = data.get('type', 'Basic').strip()
        
        if not ambulance_id:
            return jsonify({'status': 'error', 'message': 'Ambulance number required'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Insert ambulance
        cursor.execute('''
            INSERT INTO ambulances (ambulance_number, type, status, hospital_id)
            VALUES (%s, %s, 'Available', %s)
        ''', (ambulance_id, ambulance_type, hospital_id))
        
        # Auto assign this ambulance to first driver who has no ambulance
        cursor.execute('''UPDATE drivers SET assigned_ambulance = %s 
    WHERE hospital_id = %s 
    AND status = 'Available' 
    AND assigned_ambulance IS NULL 
    LIMIT 1''', (ambulance_id, hospital_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[ADD AMBULANCE] Ambulance {ambulance_id} ({ambulance_type}) added to hospital {hospital_id}')
        
        return jsonify({
            'status': 'success',
            'message': f'Ambulance {ambulance_id} added successfully'
        }), 201
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/remove-ambulance', methods=['POST'])
def remove_ambulance():
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    session.modified = True
    try:
        data = request.get_json()
        ambulance_number = data.get('ambulance_number') or data.get('ambulance_id')
        hospital_id = session.get('hospital_id')
        if not ambulance_number:
            return jsonify({'status': 'error', 'message': 'Ambulance number required'}), 400
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE drivers SET assigned_ambulance = NULL, status = 'Available' WHERE assigned_ambulance = %s AND hospital_id = %s", (ambulance_number, hospital_id))
        cursor.execute("DELETE FROM ambulances WHERE ambulance_number = %s AND hospital_id = %s", (ambulance_number, hospital_id))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'status': 'success', 'message': f'Ambulance {ambulance_number} removed'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get-ambulances', methods=['GET'])
def get_ambulances():
    """Get all ambulances for the hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ambulances WHERE hospital_id = %s', (hospital_id,))
    ambulances = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert datetime objects to strings
    for ambulance in ambulances:
        if ambulance.get('last_service') and hasattr(ambulance['last_service'], 'isoformat'):
            ambulance['last_service'] = ambulance['last_service'].isoformat()
        if ambulance.get('created_at') and hasattr(ambulance['created_at'], 'isoformat'):
            ambulance['created_at'] = ambulance['created_at'].isoformat()
    
    return jsonify({
        'status': 'success',
        'count': len(ambulances),
        'ambulances': ambulances
    }), 200

@app.route('/get-dispatches', methods=['GET'])
def get_dispatches():
    """Get dispatches for the current user"""
    if 'user_type' not in session:
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if session['user_type'] == 'hospital':
        hospital_id = session.get('hospital_id')
        cursor.execute('SELECT * FROM dispatches WHERE hospital_id = %s', (hospital_id,))
    elif session['user_type'] == 'driver':
        # Use the same key set at login: session['driver_id']
        raw_id = (session.get('driver_id') or
                  session.get('id') or
                  session.get('user_id'))
        try:
            driver_id = int(raw_id)
        except (TypeError, ValueError):
            driver_id = None
        print(f'[GET-DISPATCHES] driver_id={driver_id}')
        if not driver_id:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'No driver id in session', 'dispatches': []}), 404
        cursor.execute('''
            SELECT d.*, pr.pickup_address, pr.patient_name, pr.patient_phone, pr.reason,
                   pr.priority, pr.latitude, pr.longitude
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.driver_id = %s AND d.status = 'dispatched'
            ORDER BY d.timestamp DESC
            LIMIT 1
        ''', (driver_id,))
    else:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid user type', 'dispatches': []}), 403
    
    dispatches = cursor.fetchall()
    print(f'[GET-DISPATCHES] Found {len(dispatches)} active dispatches')
    cursor.close()
    conn.close()
    
    # Convert datetime objects to strings
    for dispatch in dispatches:
        for key in ('timestamp', 'updated_at', 'created_at'):
            if dispatch.get(key) and hasattr(dispatch[key], 'isoformat'):
                dispatch[key] = dispatch[key].isoformat()
    
    return jsonify({
        'success': True,
        'status': 'success',
        'count': len(dispatches),
        'dispatches': dispatches
    }), 200

@app.route('/driver-accept-dispatch', methods=['POST'])
def driver_accept_dispatch():
    """Driver accepts a dispatched assignment — sets status to en_route"""
    if session.get('user_type') != 'driver':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        dispatch_id = data.get('dispatch_id')
        if not dispatch_id:
            return jsonify({'success': False, 'message': 'dispatch_id required'}), 400
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        # Get the request_id so we can sync patient_requests status
        cursor.execute("SELECT request_id FROM dispatches WHERE dispatch_id=%s", (dispatch_id,))
        disp_row = cursor.fetchone()
        cursor.execute("UPDATE dispatches SET status='en_route' WHERE dispatch_id=%s", (dispatch_id,))
        cursor.execute("UPDATE drivers SET status='On Duty' WHERE id=%s", (session.get('driver_id'),))
        if disp_row:
            cursor.execute("UPDATE patient_requests SET status='en_route' WHERE request_id=%s", (disp_row['request_id'],))
        conn.commit()
        cursor.close()
        conn.close()
        print(f'[DRIVER-ACCEPT] dispatch_id={dispatch_id} accepted by driver {session.get("driver_id")}')
        return jsonify({'success': True})
    except Exception as e:
        print(f'[DRIVER-ACCEPT ERROR] {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/driver-reject-dispatch', methods=['POST'])
def driver_reject_dispatch():
    """Driver rejects a dispatched assignment"""
    if session.get('user_type') != 'driver':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        dispatch_id = data.get('dispatch_id')
        if not dispatch_id:
            return jsonify({'success': False, 'message': 'dispatch_id required'}), 400
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("UPDATE dispatches SET status='driver_rejected' WHERE dispatch_id=%s", (dispatch_id,))
        # Reset driver back to Available so they can receive future dispatches
        cursor.execute("UPDATE drivers SET status='Available' WHERE id=%s", (session.get('driver_id'),))
        conn.commit()
        cursor.close()
        conn.close()
        print(f'[DRIVER-REJECT] dispatch_id={dispatch_id} rejected by driver {session.get("driver_id")}')
        return jsonify({'success': True})
    except Exception as e:
        print(f'[DRIVER-REJECT ERROR] {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/update-dispatch-status', methods=['POST'])
def update_dispatch_status():
    """
    Update dispatch status with timeline logging.
    Valid statuses: en_route, picked_up, completed
    On completion: mark driver Available, free ambulance, log to timeline
    """
    if 'user_type' not in session or session['user_type'] != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        dispatch_id = data.get('dispatch_id')
        new_status = data.get('status', '').lower()
        
        # Validate status value
        valid_statuses = ['en_route', 'picked_up', 'completed']
        if new_status not in valid_statuses:
            return jsonify({
                'status': 'error', 
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        driver_uname = session.get('driver_username') or session.get('username')
        
        # Find dispatch by dispatch_id
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT id FROM drivers WHERE username = %s', (driver_uname,))
        drv_row = cursor.fetchone()
        if not drv_row:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        driver_int_id = drv_row['id']
        
        # Get current dispatch
        cursor.execute('''
            SELECT d.*, pr.request_id FROM dispatches d
            JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.dispatch_id = %s AND d.driver_id = %s
        ''', (dispatch_id, driver_int_id))
        dispatch = cursor.fetchone()
        
        if not dispatch:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Dispatch not found or not assigned to you'}), 404
        
        old_status = dispatch.get('status')
        request_id = dispatch['request_id']
        
        # Update dispatch status
        cursor.execute('''
            UPDATE dispatches SET status = %s WHERE dispatch_id = %s
        ''', (new_status, dispatch_id))
        
        # Update corresponding patient_request
        if request_id:
            cursor.execute('''
                UPDATE patient_requests SET status = %s WHERE request_id = %s
            ''', (new_status, request_id))
        
        # Log status change to timeline with server timestamp
        cursor.execute('''
            INSERT INTO status_timeline 
            (request_id, dispatch_id, old_status, new_status, action_by, action_type, driver_id, driver_name, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            request_id, dispatch_id, old_status, new_status,
            driver_uname, 'driver_update', driver_int_id, dispatch['driver_name'],
            f'Driver updated status from {old_status} to {new_status}'
        ))
        
        # Handle completion cleanup
        if new_status == 'completed':
            # Get ambulance information before freeing
            cursor.execute('''
                SELECT assigned_ambulance, hospital_id FROM drivers WHERE id = %s
            ''', (dispatch['driver_id'],))
            drv_info = cursor.fetchone()
            ambulance_number = drv_info['assigned_ambulance'] if drv_info else None
            hospital_id = drv_info['hospital_id'] if drv_info else None
            
            # Free current driver back to Available
            cursor.execute('''
                UPDATE drivers SET status = 'Available' WHERE id = %s
            ''', (dispatch['driver_id'],))
            
            # Free the ambulance back to Available
            if ambulance_number:
                cursor.execute('''
                    UPDATE ambulances SET status = 'Available' WHERE ambulance_number = %s
                ''', (ambulance_number,))
                
                # Auto assign ambulance to next available driver who has no ambulance
                cursor.execute('''
                    UPDATE drivers SET assigned_ambulance = %s 
                    WHERE hospital_id = %s
                    AND status = 'Available' 
                    AND assigned_ambulance IS NULL
                    AND id != %s
                    LIMIT 1
                ''', (ambulance_number, hospital_id, dispatch['driver_id']))
            
            # Log final completion entry to timeline
            cursor.execute('''
                INSERT INTO status_timeline 
                (request_id, dispatch_id, old_status, new_status, action_by, action_type, driver_id, driver_name, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_id, dispatch_id, 'dispatched', 'completed',
                driver_uname, 'trip_completed', driver_int_id, dispatch['driver_name'],
                'Trip completed successfully. Driver and ambulance freed.'
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[UPDATE DISPATCH] {request_id}: {old_status} -> {new_status} (Driver: {driver_uname})')
        
        return jsonify({
            'status': 'success',
            'message': f'Dispatch status updated to {new_status}',
            'dispatch_id': dispatch_id,
            'old_status': old_status,
            'new_status': new_status
        }), 200
    
    except Exception as e:
        print(f'[UPDATE-DISPATCH-STATUS ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Error updating dispatch status: ' + str(e)
        }), 500

@app.route('/get-hospital-stats', methods=['GET'])
def get_hospital_stats():
    """Get real-time hospital statistics"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get hospital info
    cursor.execute('SELECT total_beds, available_beds FROM hospitals WHERE id = %s', (hospital_id,))
    hosp = cursor.fetchone()
    
    # Get ambulance counts
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) as available
        FROM ambulances WHERE hospital_id = %s
    ''', (hospital_id,))
    amb = cursor.fetchone()
    
    # Get driver counts
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) as available
        FROM drivers WHERE hospital_id = %s
    ''', (hospital_id,))
    drv = cursor.fetchone()
    
    # Get active emergencies
    cursor.execute('''
        SELECT COUNT(*) as count FROM patient_requests 
        WHERE hospital_id = %s AND status IN ('pending', 'accepted', 'en_route', 'picked_up')
    ''', (hospital_id,))
    active = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    total_beds = hosp['total_beds']
    available_beds = hosp['available_beds']
    occupied_beds = total_beds - available_beds
    
    return jsonify({
        'status': 'success',
        'beds': {
            'total': total_beds,
            'available': available_beds,
            'occupied': occupied_beds,
            'occupancy_rate': int((occupied_beds / total_beds) * 100) if total_beds > 0 else 0,
            'is_full': available_beds == 0
        },
        'ambulances': {
            'total': amb['total'],
            'available': amb['available'],
            'assigned': amb['total'] - amb['available']
        },
        'drivers': {
            'total': drv['total'],
            'available': drv['available']
        },
        'emergencies': active['count']
    }), 200

# ==================== HOSPITAL CHANGE DRIVER PASSWORD ====================
@app.route('/change-driver-password', methods=['POST'])
def change_driver_password():
    """Change driver password by hospital admin"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        driver_id = data.get('driver_id')
        new_password = data.get('new_password', '').strip()
        
        # Validate inputs
        if not driver_id or not new_password:
            return jsonify({'status': 'error', 'message': 'Driver ID and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters'}), 400
        
        # Verify driver exists and belongs to hospital
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT id, username, name FROM drivers WHERE id = %s AND hospital_id = %s',
            (driver_id, hospital_id)
        )
        driver = cursor.fetchone()
        
        if not driver:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Driver not found or does not belong to your hospital'}), 404
        
        # Update password
        cursor.execute(
            'UPDATE drivers SET password = %s WHERE id = %s AND hospital_id = %s',
            (new_password, driver_id, hospital_id)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f'[HOSPITAL CHANGE DRIVER PASSWORD] Driver {driver["username"]} ({driver["name"]}) password changed by hospital {hospital_id}')
        
        return jsonify({
            'status': 'success',
            'message': f'Password for driver {driver["name"]} changed successfully'
        }), 200
        
    except Exception as e:
        print(f'[ERROR] change_driver_password: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== GET DISPATCH HISTORY ====================
@app.route('/get-dispatch-history', methods=['GET'])
def get_dispatch_history():
    """Get dispatch history for hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get last 50 dispatches for hospital
        cursor.execute('''
            SELECT dispatch_id, request_id, patient_name, patient_phone, location, 
                   driver_id, driver_name, ambulance_id, status, priority, 
                   timestamp, updated_at
            FROM dispatches 
            WHERE hospital_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''', (hospital_id,))
        
        dispatches = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert datetime objects to isoformat strings
        for dispatch in dispatches:
            if dispatch['timestamp']:
                dispatch['timestamp'] = dispatch['timestamp'].isoformat()
            if dispatch['updated_at']:
                dispatch['updated_at'] = dispatch['updated_at'].isoformat()
        
        return jsonify({
            'status': 'success',
            'dispatches': dispatches
        }), 200
        
    except Exception as e:
        print(f'[ERROR] get_dispatch_history: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/reset-all-status', methods=['POST'])
def reset_all_status():
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    hospital_id = session.get('hospital_id')
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE drivers SET status = 'Available' WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("UPDATE ambulances SET status = 'Available' WHERE hospital_id = %s", (hospital_id,))
        # Delete child records first to avoid FK issues
        cursor.execute("DELETE st FROM status_timeline st JOIN patient_requests pr ON st.request_id = pr.request_id WHERE pr.hospital_id = %s", (hospital_id,))
        cursor.execute("DELETE FROM dispatches WHERE hospital_id = %s", (hospital_id,))
        cursor.execute("DELETE FROM patient_requests WHERE hospital_id = %s", (hospital_id,))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'status': 'success', 'message': 'Everything reset successfully'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== ATTENDANCE MANAGEMENT ====================
@app.route('/get-pending-attendance', methods=['GET'])
def get_pending_attendance():
    """Get all pending attendance records for hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get pending attendance records with driver info
        cursor.execute('''
            SELECT ar.id, ar.driver_id, ar.date, ar.status, ar.admin_status, ar.leave_reason,
                   d.name as driver_name, d.username as driver_username
            FROM attendance_records ar
            JOIN drivers d ON ar.driver_id = d.id
            WHERE d.hospital_id = %s AND ar.admin_status = 'pending'
            ORDER BY ar.date DESC
        ''', (hospital_id,))
        
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert date objects to ISO format
        for record in records:
            if record['date']:
                record['date'] = record['date'].isoformat()
        
        return jsonify({
            'status': 'success',
            'records': records
        }), 200
        
    except Exception as e:
        print(f'[ERROR] get_pending_attendance: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/approve-attendance', methods=['POST'])
def approve_attendance():
    """Approve or reject attendance record(s) - supports single or batch approval"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'approved' or 'rejected'
        
        if action not in ['approved', 'rejected']:
            return jsonify({'status': 'error', 'message': 'Invalid action'}), 400
        
        # Support both single and batch approval
        attendance_ids = []
        if data.get('attendance_ids'):  # Batch approval (array)
            attendance_ids = data.get('attendance_ids', [])
        elif data.get('attendance_id'):  # Single approval (backward compatibility)
            attendance_ids = [data.get('attendance_id')]
        else:
            return jsonify({'status': 'error', 'message': 'No attendance IDs provided'}), 400
        
        if not attendance_ids or len(attendance_ids) == 0:
            return jsonify({'status': 'error', 'message': 'No attendance IDs provided'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Verify all attendance records belong to hospital
        placeholders = ','.join(['%s'] * len(attendance_ids))
        cursor.execute(f'''
            SELECT ar.id, d.hospital_id FROM attendance_records ar
            JOIN drivers d ON ar.driver_id = d.id
            WHERE ar.id IN ({placeholders})
        ''', attendance_ids)
        
        records = cursor.fetchall()
        
        if len(records) != len(attendance_ids):
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'One or more attendance records not found'}), 404
        
        # Verify all records belong to the same hospital
        for record in records:
            if record['hospital_id'] != hospital_id:
                cursor.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Unauthorized - records belong to different hospital'}), 403
        
        # Update all attendance records
        cursor.execute(f'''
            UPDATE attendance_records 
            SET admin_status = %s, approved_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', [action] + attendance_ids)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        record_count = len(attendance_ids)
        print(f'[ATTENDANCE] {record_count} attendance record(s) marked as {action}')
        return jsonify({
            'status': 'success',
            'message': f'{record_count} attendance record(s) {action} successfully'
        }), 200
        
    except Exception as e:
        print(f'[ATTENDANCE ERROR] approve_attendance: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
    except Exception as e:
        print(f'[ERROR] approve_attendance: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/all-attendance', methods=['GET'])
def get_all_attendance():
    """Get all attendance records for hospital"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get all attendance records with driver info, ordered by date descending
        cursor.execute('''
            SELECT ar.id, ar.driver_id, ar.date, ar.status, ar.admin_status, ar.leave_reason,
                   d.name as driver_name, d.username as driver_username
            FROM attendance_records ar
            JOIN drivers d ON ar.driver_id = d.id
            WHERE d.hospital_id = %s
            ORDER BY ar.date DESC
            LIMIT 500
        ''', (hospital_id,))
        
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert date objects to ISO format
        for record in records:
            if record['date']:
                record['date'] = record['date'].isoformat()
        
        return jsonify({
            'status': 'success',
            'records': records
        }), 200
        
    except Exception as e:
        print(f'[ERROR] get_all_attendance: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/edit-attendance', methods=['POST'])
def edit_attendance():
    """Edit an attendance record"""
    if 'user_type' not in session or session['user_type'] != 'hospital':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    session.modified = True
    hospital_id = session.get('hospital_id')
    
    try:
        data = request.get_json()
        attendance_id = data.get('attendance_id')
        status = data.get('status', '').strip()
        leave_reason = data.get('leave_reason', '').strip() if status == 'On Leave' else None
        
        if not attendance_id or status not in ['Present', 'On Leave']:
            return jsonify({'status': 'error', 'message': 'Invalid input'}), 400
        
        if status == 'On Leave':
            if not leave_reason:
                return jsonify({'status': 'error', 'message': 'Leave reason required'}), 400
            word_count = len(leave_reason.split())
            if word_count < 3:
                return jsonify({'status': 'error', 'message': 'Leave reason must be at least 3 words'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Verify attendance record belongs to hospital
        cursor.execute('''
            SELECT ar.id, d.hospital_id FROM attendance_records ar
            JOIN drivers d ON ar.driver_id = d.id
            WHERE ar.id = %s
        ''', (attendance_id,))
        
        record = cursor.fetchone()
        
        if not record or record['hospital_id'] != hospital_id:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Attendance record not found'}), 404
        
        # Update attendance record
        cursor.execute('''
            UPDATE attendance_records 
            SET status = %s, leave_reason = %s
            WHERE id = %s
        ''', (status, leave_reason, attendance_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[ATTENDANCE] Attendance #{attendance_id} edited - Status: {status}')
        return jsonify({
            'status': 'success',
            'message': 'Attendance record updated successfully'
        }), 200
        
    except Exception as e:
        print(f'[ERROR] edit_attendance: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/nearest-hospitals', methods=['POST'])
def nearest_hospitals():
    try:
        data = request.get_json()
        patient_lat = float(data.get('latitude'))
        patient_lng = float(data.get('longitude'))

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Fetch all approved hospitals with coordinates
        cursor.execute('''
            SELECT id, name, address, phone, latitude, longitude, available_beds
            FROM hospitals
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            AND COALESCE(status, 'approved') = 'approved'
        ''')
        db_hospitals = cursor.fetchall()

        import math

        def haversine(lat1, lng1, lat2, lng2):
            R = 6371
            dlat = math.radians(float(lat2) - lat1)
            dlng = math.radians(float(lng2) - lng1)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(lat1)) * math.cos(math.radians(float(lat2)))
                 * math.sin(dlng / 2) ** 2)
            return R * 2 * math.asin(math.sqrt(a))

        candidates = []
        for h in db_hospitals:
            hospital_id = h['id']

            # Explicit per-hospital available-driver count
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM drivers
                WHERE hospital_id = %s AND status = 'Available'
                AND assigned_ambulance IS NOT NULL
            """, (hospital_id,))
            driver_row   = cursor.fetchone()
            driver_count = int(driver_row['cnt']) if driver_row else 0

            dist        = haversine(patient_lat, patient_lng, h['latitude'], h['longitude'])
            # ETA: distance / 30 km/h urban speed * 60 min
            eta_minutes = max(1, round((dist / 30) * 60))

            print(f"[NEAREST] {h['name']}: dist={dist:.2f}km, ETA={eta_minutes}min, "
                  f"beds={h['available_beds']}, drivers={driver_count}")

            candidates.append({
                'hospital_id':    hospital_id,
                'name':           h['name'],
                'address':        h['address'] or 'Gujrat, Pakistan',
                'phone':          h['phone'] or '',
                'latitude':       float(h['latitude']),
                'longitude':      float(h['longitude']),
                'available_beds': h['available_beds'],
                'distance_km':    round(dist, 2),
                'eta_minutes':    eta_minutes,
                'traffic':        'unknown',
                'driver_count':   driver_count,
                'ai_selected':    False,
            })

        cursor.close()
        conn.close()

        # Sort: hospitals with available drivers first, then by ETA, then by distance
        candidates.sort(key=lambda x: (0 if x['driver_count'] > 0 else 1, x['eta_minutes'], x['distance_km']))

        # Mark only the first hospital (lowest ETA) as AI selected
        if candidates:
            candidates[0]['ai_selected'] = True

        registered_hospitals = candidates[:6]

        ai_name = registered_hospitals[0]['name'] if registered_hospitals else 'None'
        print(f'[NEAREST HOSPITALS] {len(registered_hospitals)} hospitals found | '
              f'AI selected: {ai_name}')

        return jsonify({
            'status': 'success',
            'registered_hospitals': registered_hospitals,
            'unregistered_hospitals': []
        }), 200

    except Exception as e:
        print(f'[NEAREST HOSPITALS ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== AUTO-ACCEPT REQUEST (Hospital Dashboard) ====================
@app.route('/auto-accept-request', methods=['POST'])
def auto_accept_request():
    """
    Auto-process pending requests for hospital:
    1. Find available drivers (status='Available', assigned_ambulance not null, not recently rejected)
    2. Sort by distance to patient, assign to nearest
    3. If no drivers: add hospital to rejected_by, reroute to next nearest registered hospital
    4. If all hospitals exhausted: set status to no_hospital_available
    
    Requires hospital login.
    """
    if session.get('user_type') != 'hospital':
        return jsonify({'error': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # STEP 1: Get first pending request for this hospital
        cursor.execute('''
            SELECT * FROM patient_requests 
            WHERE hospital_id = %s AND status = 'pending'
            ORDER BY timestamp ASC
            LIMIT 1
        ''', (hospital_id,))
        req = cursor.fetchone()
        
        if not req:
            cursor.close()
            conn.close()
            return jsonify({'status': 'success', 'action': 'no_request'}), 200
        
        print(f'[AUTO-PROCESS] Processing request {req["request_id"]} for hospital {hospital_id}')
        
        # STEP 2: Get all available drivers - status='Available', has ambulance, 
        # exclude those who rejected in last 5 minutes
        cursor.execute('''
            SELECT * FROM drivers 
            WHERE hospital_id = %s 
            AND status = 'Available' 
            AND assigned_ambulance IS NOT NULL
            AND (last_rejected_at IS NULL OR TIMESTAMPDIFF(MINUTE, last_rejected_at, NOW()) >= 5)
        ''', (hospital_id,))
        available_drivers = cursor.fetchall()
        
        # If drivers available, sort by distance to patient and assign to nearest
        if available_drivers:
            patient_lat = float(req['latitude'])
            patient_lng = float(req['longitude'])
            
            # Calculate distance from each driver to patient
            # For now, drivers don't have stored GPS location, so we use hospital as proxy
            # In future with real-time GPS tracking, we would use driver_latitude/driver_longitude
            drivers_with_distance = []
            for driver in available_drivers:
                # If driver has GPS location stored, use it; otherwise use hospital location
                if driver.get('driver_latitude') and driver.get('driver_longitude'):
                    driver_lat = float(driver['driver_latitude'])
                    driver_lng = float(driver['driver_longitude'])
                else:
                    # Get hospital location as proxy for driver location
                    cursor.execute('''
                        SELECT latitude, longitude FROM hospitals WHERE id = %s
                    ''', (hospital_id,))
                    hosp = cursor.fetchone()
                    if hosp:
                        driver_lat = float(hosp['latitude'])
                        driver_lng = float(hosp['longitude'])
                    else:
                        driver_lat = patient_lat
                        driver_lng = patient_lng
                
                # Calculate distance using Haversine formula
                distance_km = calculate_distance(driver_lat, driver_lng, patient_lat, patient_lng)
                drivers_with_distance.append({
                    'driver': driver,
                    'distance_km': distance_km
                })
            
            # Sort by distance (nearest first)
            drivers_with_distance.sort(key=lambda x: x['distance_km'])
            nearest_driver = drivers_with_distance[0]['driver']
            distance_to_patient = drivers_with_distance[0]['distance_km']
            
            print(f'[AUTO-ASSIGN] {nearest_driver["name"]} is {distance_to_patient:.2f}km from patient')
            
            # Assign request to nearest driver
            cursor.execute('''
                UPDATE patient_requests 
                SET status = 'assigned', assigned_driver = %s, assigned_driver_id = %s, auto_processed = TRUE, auto_processed_at = NOW()
                WHERE request_id = %s
            ''', (nearest_driver['username'], nearest_driver['id'], req['request_id']))
            
            # Update driver status to On Duty
            cursor.execute('''
                UPDATE drivers SET status = 'On Duty' WHERE id = %s
            ''', (nearest_driver['id'],))
            
            # Update ambulance status to On Duty
            cursor.execute('''
                UPDATE ambulances SET status = 'On Duty' WHERE ambulance_number = %s
            ''', (nearest_driver['assigned_ambulance'],))
            
            # Create dispatch record
            dispatch_id = f"DSP-2026-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute('''
                INSERT INTO dispatches 
                (dispatch_id, request_id, patient_name, patient_phone, location, driver_id, driver_name, 
                 ambulance_id, hospital_id, status, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                dispatch_id, req['request_id'], req['patient_name'], req['patient_phone'], 
                req['pickup_address'], nearest_driver['id'], nearest_driver['name'], 
                nearest_driver['assigned_ambulance'], hospital_id, 'dispatched', 
                req.get('priority', 'High')
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f'[AUTO-ASSIGNED] {req["request_id"]} -> Driver: {nearest_driver["name"]}, Hospital: {hospital_id}')
            
            return jsonify({
                'status': 'success',
                'action': 'auto_assigned',
                'request_id': req['request_id'],
                'driver_name': nearest_driver['name'],
                'driver_id': nearest_driver['id'],
                'dispatch_id': dispatch_id
            }), 200
        
        else:
            # STEP 3: No available drivers - handle hospital cycling
            print(f'[AUTO-NO-DRIVERS] No drivers available at hospital {hospital_id} for {req["request_id"]}')
            
            # Add current hospital to rejected_by JSON array
            rejected_by = req.get('rejected_by')
            if isinstance(rejected_by, str):
                try:
                    rejected_by = json.loads(rejected_by)
                except:
                    rejected_by = []
            elif not isinstance(rejected_by, list):
                rejected_by = []
            
            # Add hospital only if not already there
            if hospital_id not in rejected_by:
                rejected_by.append(hospital_id)
            
            # Get patient coordinates
            patient_lat = float(req['latitude'])
            patient_lng = float(req['longitude'])
            
            # Query all registered hospitals (available_beds > 0) not in rejected_by
            cursor.execute('''
                SELECT id, name, latitude, longitude, available_beds
                FROM hospitals
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                AND available_beds > 0
                AND COALESCE(status, 'approved') = 'approved'
            ''')
            registered_hospitals = cursor.fetchall()
            
            # Calculate distances to all registered hospitals not in rejected_by
            hospital_distances = []
            for hospital in registered_hospitals:
                if hospital['id'] not in rejected_by:
                    distance_km = calculate_distance(
                        patient_lat, patient_lng,
                        float(hospital['latitude']), float(hospital['longitude'])
                    )
                    hospital_distances.append({
                        'hospital_id': hospital['id'],
                        'name': hospital['name'],
                        'distance_km': distance_km
                    })
            
            if hospital_distances:
                # Sort by distance and get nearest
                hospital_distances.sort(key=lambda x: x['distance_km'])
                next_hospital = hospital_distances[0]
                next_hospital_id = next_hospital['hospital_id']
                
                # Update request: change hospital_id, keep status as pending, update rejected_by, set forwarded_from_hospital_id
                cursor.execute('''
                    UPDATE patient_requests 
                    SET hospital_id = %s, rejected_by = %s, status = 'pending', forwarded_from_hospital_id = %s
                    WHERE request_id = %s
                ''', (next_hospital_id, json.dumps(rejected_by), hospital_id, req['request_id']))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                print(f'[AUTO-REROUTE] {req["request_id"]} rerouted to hospital {next_hospital["name"]} (ID: {next_hospital_id})')
                
                return jsonify({
                    'status': 'success',
                    'action': 'auto_rerouted',
                    'request_id': req['request_id'],
                    'from_hospital_id': hospital_id,
                    'to_hospital_id': next_hospital_id,
                    'to_hospital_name': next_hospital['name'],
                    'message': f'Rerouted to {next_hospital["name"]}'
                }), 200
            
            else:
                # No more registered hospitals available
                cursor.execute('''
                    UPDATE patient_requests
                    SET status = 'no_hospital_available', rejected_by = %s
                    WHERE request_id = %s
                ''', (json.dumps(rejected_by), req['request_id']))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                print(f'[AUTO-UNABLE] {req["request_id"]} - no hospitals available (all hospitals rejected or have no beds)')
                
                return jsonify({
                    'status': 'success',
                    'action': 'no_hospital_available',
                    'request_id': req['request_id'],
                    'message': 'No hospitals available with available drivers and beds',
                    'rejected_by_count': len(rejected_by)
                }), 200
    
    except Exception as e:
        print(f'[AUTO-ACCEPT ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ==================== CHECK DRIVER ASSIGNMENT ====================
@app.route('/check-assignment', methods=['GET'])
def check_assignment():
    """
    Get current dispatch assignment for driver.
    Called by driver dashboard every 3 seconds.
    - Returns assigned dispatch if status = 'dispatched'
    - Includes countdown timer (seconds_remaining = 60 - elapsed)
    - Auto-rejects driver if no response after 1 minute, escalates to next driver
    """
    if session.get('user_type') != 'driver':
        return jsonify({'error': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get current assignment with 'dispatched' status
        cursor.execute('''
            SELECT d.*, pr.latitude, pr.longitude, pr.pickup_address, pr.hospital_id
            FROM dispatches d
            JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.driver_id = %s AND d.status = 'dispatched'
            ORDER BY d.timestamp DESC
            LIMIT 1
        ''', (driver_id,))
        
        assignment = cursor.fetchone()
        
        if not assignment:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'has_assignment': False
            }), 200
        
        # Calculate seconds elapsed and remaining
        timestamp = assignment['timestamp']
        now = datetime.now()
        
        if hasattr(timestamp, 'timestamp'):
            # Use Unix timestamp if available
            seconds_elapsed = int((now - timestamp).total_seconds())
        else:
            seconds_elapsed = int((now - timestamp).total_seconds())
        
        seconds_remaining = max(0, 60 - seconds_elapsed)
        
        # If driver hasn't responded after 1 minute, auto-reject and escalate
        if seconds_elapsed > 60:
            dispatch_id_str = assignment['dispatch_id']
            request_id_str  = assignment['request_id']
            hospital_id     = assignment['hospital_id']
            print(f'[1-MIN TIMEOUT] dispatch={dispatch_id_str}, driver={driver_id}')

            # Mark current dispatch driver_rejected
            cursor.execute(
                "UPDATE dispatches SET status='driver_rejected' WHERE dispatch_id=%s",
                (dispatch_id_str,))

            # Reset current driver to Available
            cursor.execute(
                "UPDATE drivers SET status='Available', last_rejected_at=NOW() WHERE id=%s",
                (driver_id,))

            # Clear assignment on patient_request
            cursor.execute(
                "UPDATE patient_requests SET assigned_driver=NULL, assigned_driver_id=NULL, status='pending' WHERE request_id=%s",
                (request_id_str,))

            # Log to timeline
            cursor.execute('''
                INSERT INTO status_timeline
                (request_id, dispatch_id, old_status, new_status, action_by, action_type, driver_id, driver_name, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', (request_id_str, dispatch_id_str, 'dispatched', 'driver_rejected',
                  'system', 'driver_timeout', driver_id, assignment['driver_name'],
                  'Driver did not respond within 1 minute'))

            conn.commit()

            # --- ESCALATION: find next available driver in same hospital ---
            cursor.execute('''
                SELECT * FROM drivers
                WHERE hospital_id=%s AND status='Available' AND assigned_ambulance IS NOT NULL
                AND id != %s
                ORDER BY id ASC LIMIT 1
            ''', (hospital_id, driver_id))
            next_driver = cursor.fetchone()

            if next_driver:
                import time as _time
                new_dispatch_id = f"DSP-{int(_time.time())}"
                cursor.execute('''
                    INSERT INTO dispatches
                    (dispatch_id, request_id, patient_name, patient_phone, location,
                     driver_id, driver_name, ambulance_id, hospital_id, status, priority)
                    SELECT %s, request_id, patient_name, patient_phone, pickup_address,
                           %s, %s, %s,
                           hospital_id, 'dispatched', priority
                    FROM patient_requests WHERE request_id=%s
                ''', (new_dispatch_id, next_driver['id'], next_driver['name'],
                      next_driver['assigned_ambulance'], request_id_str))
                cursor.execute(
                    "UPDATE drivers SET status='On Duty' WHERE id=%s",
                    (next_driver['id'],))
                cursor.execute(
                    "UPDATE patient_requests SET status='assigned', assigned_driver=%s, assigned_driver_id=%s WHERE request_id=%s",
                    (next_driver['username'], next_driver['id'], request_id_str))
                conn.commit()
                print(f'[ESCALATE] Reassigned request {request_id_str} to next driver: {next_driver["name"]} (id={next_driver["id"]})')
            else:
                # No drivers left in this hospital → leave pending so next hospital can pick it up
                print(f'[ESCALATE] No available drivers left in hospital {hospital_id} → request {request_id_str} back to pending for next hospital')
                conn.commit()

            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'has_assignment': False,
                'timeout_action': 'rejected_and_reassigned'
            }), 200
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'has_assignment': True,
            'dispatch_id': assignment['dispatch_id'],
            'request_id': assignment['request_id'],
            'patient_name': assignment['patient_name'],
            'patient_phone': assignment['patient_phone'],
            'location': assignment['pickup_address'],
            'latitude': float(assignment['latitude']),
            'longitude': float(assignment['longitude']),
            'priority': assignment['priority'],
            'timestamp': assignment['timestamp'].isoformat() if hasattr(assignment['timestamp'], 'isoformat') else str(assignment['timestamp']),
            'seconds_elapsed': seconds_elapsed,
            'seconds_remaining': seconds_remaining
        }), 200
    
    except Exception as e:
        print(f'[CHECK-ASSIGNMENT ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ==================== HOSPITAL - GET ACTIVE REQUESTS ====================
@app.route('/get-hospital-active-requests', methods=['GET'])
def get_hospital_active_requests():
    """
    Get active requests for hospital dashboard.
    Requires hospital session.
    
    Returns two lists:
    1. accepted_requests: Requests with status in (accepted, assigned, en_route, picked_up)
    2. forwarded_requests: Requests that were forwarded to other hospitals
    
    For each request calculates:
    - Distance from hospital to patient using calculate_distance()
    - Time since request created using TIMESTAMPDIFF
    - Status in human-readable form
    """
    if session.get('user_type') != 'hospital':
        return jsonify({'status': 'error', 'message': 'Hospital login required'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Hospital ID not found'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get hospital coordinates
        cursor.execute('SELECT latitude, longitude FROM hospitals WHERE id = %s', (hospital_id,))
        hosp_data = cursor.fetchone()
        if not hosp_data:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404
        
        hosp_lat = float(hosp_data['latitude'])
        hosp_lng = float(hosp_data['longitude'])
        
        # PART 1: Query accepted requests
        cursor.execute('''
            SELECT 
                pr.request_id,
                pr.patient_name,
                pr.patient_phone,
                pr.assigned_driver,
                pr.assigned_driver_id,
                pr.latitude,
                pr.longitude,
                pr.status,
                pr.timestamp,
                d.name as driver_name,
                d.current_latitude  as driver_lat,
                d.current_longitude as driver_lng,
                d.location_updated_at as driver_location_updated_at,
                a.ambulance_number
            FROM patient_requests pr
            LEFT JOIN drivers d ON pr.assigned_driver_id = d.id
            LEFT JOIN ambulances a ON d.assigned_ambulance = a.ambulance_number
            WHERE pr.hospital_id = %s AND pr.status IN ('accepted', 'assigned', 'en_route', 'picked_up')
            ORDER BY pr.timestamp ASC
        ''', (hospital_id,))
        accepted_requests_rows = cursor.fetchall()
        
        accepted_requests = []
        for row in accepted_requests_rows:
            if row['latitude'] and row['longitude']:
                distance_km = calculate_distance(hosp_lat, hosp_lng, float(row['latitude']), float(row['longitude']))
            else:
                distance_km = 0
            
            cursor.execute('SELECT TIMESTAMPDIFF(MINUTE, %s, NOW()) as minutes_ago', (row['timestamp'],))
            time_result = cursor.fetchone()
            minutes_since = time_result['minutes_ago'] if time_result else 0
            
            # Check if driver GPS is fresh (within 60s)
            driver_gps_live = False
            if row.get('driver_location_updated_at') and row.get('driver_lat') and row.get('driver_lng'):
                from datetime import datetime as _dt2
                try:
                    diff = (_dt2.now() - row['driver_location_updated_at']).total_seconds()
                    driver_gps_live = diff <= 60
                except Exception:
                    pass

            accepted_requests.append({
                'request_id': row['request_id'],
                'patient_name': row['patient_name'] or 'N/A',
                'patient_phone': row['patient_phone'] or 'N/A',
                'driver_name': row['driver_name'] or 'Unassigned',
                'ambulance_number': row['ambulance_number'] or 'N/A',
                'status': row['status'],
                'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                'minutes_since': minutes_since,
                'distance_km': round(distance_km, 2),
                'driver_lat': float(row['driver_lat']) if row.get('driver_lat') else None,
                'driver_lng': float(row['driver_lng']) if row.get('driver_lng') else None,
                'driver_gps_live': driver_gps_live,
                'patient_lat': float(row['latitude']) if row.get('latitude') else None,
                'patient_lng': float(row['longitude']) if row.get('longitude') else None
            })
        
        # PART 2: Query forwarded requests
        cursor.execute('''
            SELECT 
                pr.request_id,
                pr.patient_name,
                pr.patient_phone,
                pr.status,
                pr.hospital_id as current_hospital_id,
                pr.timestamp,
                h.name as forwarded_to_hospital
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            WHERE pr.forwarded_from_hospital_id = %s
            ORDER BY pr.timestamp ASC
        ''', (hospital_id,))
        forwarded_requests_rows = cursor.fetchall()
        
        forwarded_requests = []
        for row in forwarded_requests_rows:
            cursor.execute('SELECT TIMESTAMPDIFF(MINUTE, %s, NOW()) as minutes_ago', (row['timestamp'],))
            time_result = cursor.fetchone()
            minutes_since = time_result['minutes_ago'] if time_result else 0
            
            forwarded_requests.append({
                'request_id': row['request_id'],
                'patient_name': row['patient_name'] or 'N/A',
                'patient_phone': row['patient_phone'] or 'N/A',
                'forwarded_to': row['forwarded_to_hospital'] or 'Unknown',
                'reason': 'No driver available',
                'status': row['status'],
                'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                'minutes_since': minutes_since
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'accepted_requests': accepted_requests,
            'forwarded_requests': forwarded_requests
        }), 200
    
    except Exception as e:
        print(f'[GET-ACTIVE-REQUESTS ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOSPITAL - GET HISTORY ====================
@app.route('/get-hospital-history', methods=['GET'])
def get_hospital_history():
    """
    Get hospital history filtered by month and year.
    Requires hospital session.
    
    Query parameters:
    - month: 1-12
    - year: 4 digit year
    
    Returns:
    - history: List of requests with status, driver, ambulance, timestamps
    - summary: Cards with total, accepted, rejected, completed counts and avg response time
    
    Uses MONTH() and YEAR() functions to filter by month.
    Uses LEFT JOIN on dispatches so requests that were never dispatched still appear.
    Displays timestamps in Pakistan timezone (+05:00).
    """
    if session.get('user_type') != 'hospital':
        return jsonify({'status': 'error', 'message': 'Hospital login required'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Hospital ID not found'}), 400
    
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if not month or not year or month < 1 or month > 12 or year < 2000 or year > 2100:
            return jsonify({'status': 'error', 'message': 'Invalid month or year'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get history for this hospital in the specified month/year
        cursor.execute('''
            SELECT 
                pr.request_id,
                pr.patient_name,
                pr.patient_phone,
                pr.status,
                pr.assigned_driver_id,
                pr.forwarded_from_hospital_id,
                pr.timestamp,
                CONVERT_TZ(pr.timestamp, '+00:00', '+05:00') as timestamp_pk,
                d.name as driver_name,
                a.ambulance_number,
                dsp.updated_at as dispatch_updated_at,
                CONVERT_TZ(dsp.updated_at, '+00:00', '+05:00') as dispatch_updated_at_pk,
                TIMESTAMPDIFF(MINUTE, pr.timestamp, dsp.updated_at) as duration_minutes,
                h_forwarded.name as forwarded_from_hospital_name
            FROM patient_requests pr
            LEFT JOIN dispatches dsp ON pr.request_id = dsp.request_id
            LEFT JOIN drivers d ON pr.assigned_driver_id = d.id
            LEFT JOIN ambulances a ON d.assigned_ambulance = a.ambulance_number
            LEFT JOIN hospitals h_forwarded ON pr.forwarded_from_hospital_id = h_forwarded.id
            WHERE pr.hospital_id = %s 
            AND MONTH(pr.timestamp) = %s 
            AND YEAR(pr.timestamp) = %s
            ORDER BY pr.timestamp DESC
        ''', (hospital_id, month, year))
        
        history_rows = cursor.fetchall()
        
        if not history_rows:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'message': 'No requests found for this period',
                'history': [],
                'summary': {
                    'total_requests': 0,
                    'accepted_count': 0,
                    'rejected_count': 0,
                    'completed_count': 0,
                    'avg_response_minutes': 0
                }
            }), 200
        
        # Build history list
        history = []
        total_completed = 0
        total_duration = 0
        
        for row in history_rows:
            was_forwarded = row['forwarded_from_hospital_id'] is not None
            status_val = row['status']
            
            # Count completion if status is completed and has duration
            if status_val == 'completed' and row['duration_minutes']:
                total_completed += 1
                total_duration += row['duration_minutes']
            
            history.append({
                'request_id': row['request_id'],
                'patient_name': row['patient_name'] or 'N/A',
                'patient_phone': row['patient_phone'] or 'N/A',
                'status': status_val,
                'driver_name': row['driver_name'] or 'N/A',
                'ambulance_number': row['ambulance_number'] or 'N/A',
                'timestamp': row['timestamp_pk'].isoformat() if hasattr(row['timestamp_pk'], 'isoformat') else str(row['timestamp_pk']),
                'completed_at': row['dispatch_updated_at_pk'].isoformat() if row['dispatch_updated_at_pk'] and hasattr(row['dispatch_updated_at_pk'], 'isoformat') else (str(row['dispatch_updated_at_pk']) if row['dispatch_updated_at_pk'] else None),
                'was_forwarded': was_forwarded,
                'forwarded_from': row['forwarded_from_hospital_name'] if was_forwarded else None,
                'duration_minutes': row['duration_minutes']
            })
        
        # Calculate summary stats
        accepted_count = sum(1 for r in history if r['status'] in ('accepted', 'assigned', 'en_route', 'picked_up', 'completed'))
        rejected_count = sum(1 for r in history if r['status'] in ('rejected', 'cancelled'))
        completed_count = sum(1 for r in history if r['status'] == 'completed')
        avg_response_minutes = round(total_duration / total_completed, 2) if total_completed > 0 else 0
        
        summary = {
            'total_requests': len(history),
            'accepted_count': accepted_count,
            'rejected_count': rejected_count,
            'completed_count': completed_count,
            'avg_response_minutes': avg_response_minutes
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'history': history,
            'summary': summary
        }), 200
    
    except Exception as e:
        print(f'[GET-HISTORY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== GET TODAY'S ACTIVITY ====================
@app.route('/get-today-activity', methods=['GET'])
def get_today_activity():
    """
    Get all requests that came to this hospital today only.
    Uses CURDATE() in MySQL to automatically reset each day.
    Requires hospital session.
    
    Returns:
    - activity: List of today's requests with all details
    - summary: Cards with total_today, completed_today, forwarded_today, active_now, avg_response_today
    
    Auto-refreshes every 15 seconds on the frontend.
    """
    if session.get('user_type') != 'hospital':
        return jsonify({'status': 'error', 'message': 'Hospital login required'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'status': 'error', 'message': 'Hospital ID not found'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get all requests for this hospital today
        cursor.execute('''
            SELECT 
                pr.request_id,
                pr.patient_name,
                pr.patient_phone,
                pr.status,
                pr.assigned_driver_id,
                pr.forwarded_from_hospital_id,
                pr.timestamp,
                CONVERT_TZ(pr.timestamp, '+00:00', '+05:00') as timestamp_pk,
                d.name as driver_name,
                a.ambulance_number,
                dsp.updated_at as dispatch_updated_at,
                CONVERT_TZ(dsp.updated_at, '+00:00', '+05:00') as dispatch_updated_at_pk,
                TIMESTAMPDIFF(MINUTE, pr.timestamp, dsp.updated_at) as duration_minutes,
                h_forwarded.name as forwarded_from_hospital_name
            FROM patient_requests pr
            LEFT JOIN dispatches dsp ON pr.request_id = dsp.request_id
            LEFT JOIN drivers d ON pr.assigned_driver_id = d.id
            LEFT JOIN ambulances a ON d.assigned_ambulance = a.ambulance_number
            LEFT JOIN hospitals h_forwarded ON pr.forwarded_from_hospital_id = h_forwarded.id
            WHERE pr.hospital_id = %s 
            AND DATE(pr.timestamp) = CURDATE()
            ORDER BY pr.timestamp DESC
        ''', (hospital_id,))
        
        today_rows = cursor.fetchall()
        
        if not today_rows:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'activity': [],
                'summary': {
                    'total_today': 0,
                    'completed_today': 0,
                    'forwarded_today': 0,
                    'active_now': 0,
                    'avg_response_today': 0
                }
            }), 200
        
        # Build activity list
        activity = []
        total_completed = 0
        total_duration = 0
        
        for row in today_rows:
            was_forwarded = row['forwarded_from_hospital_id'] is not None
            status_val = row['status']
            
            # Count completion if status is completed and has duration
            if status_val == 'completed' and row['duration_minutes']:
                total_completed += 1
                total_duration += row['duration_minutes']
            
            activity.append({
                'request_id': row['request_id'],
                'patient_name': row['patient_name'] or 'N/A',
                'patient_phone': row['patient_phone'] or 'N/A',
                'status': status_val,
                'driver_name': row['driver_name'] or 'N/A',
                'ambulance_number': row['ambulance_number'] or 'N/A',
                'timestamp': row['timestamp_pk'].isoformat() if hasattr(row['timestamp_pk'], 'isoformat') else str(row['timestamp_pk']),
                'completed_at': row['dispatch_updated_at_pk'].isoformat() if row['dispatch_updated_at_pk'] and hasattr(row['dispatch_updated_at_pk'], 'isoformat') else (str(row['dispatch_updated_at_pk']) if row['dispatch_updated_at_pk'] else None),
                'was_forwarded': was_forwarded,
                'forwarded_from': row['forwarded_from_hospital_name'] if was_forwarded else None,
                'duration_minutes': row['duration_minutes']
            })
        
        # Calculate today's summary stats
        completed_count = sum(1 for r in activity if r['status'] == 'completed')
        forwarded_count = sum(1 for r in activity if r['was_forwarded'])
        active_count = sum(1 for r in activity if r['status'] in ('pending', 'assigned', 'en_route', 'picked_up'))
        avg_response_today = round(total_duration / total_completed, 2) if total_completed > 0 else 0
        
        summary = {
            'total_today': len(activity),
            'completed_today': completed_count,
            'forwarded_today': forwarded_count,
            'active_now': active_count,
            'avg_response_today': avg_response_today
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'activity': activity,
            'summary': summary
        }), 200
    
    except Exception as e:
        print(f'[GET-TODAY-ACTIVITY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== DRIVER RESPOND TO ASSIGNMENT ====================
@app.route('/driver-respond', methods=['POST'])
def driver_respond():
    """
    Handle driver response to dispatch assignment:
    - action: 'accept' or 'reject'
    - dispatch_id: the dispatch to respond to
    
    If accept: status -> en_route, record in status_timeline
    If reject: auto-reject driver, reassign to next driver in hospital
    """
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        dispatch_id = data.get('dispatch_id')
        action = data.get('action', '').lower()
        
        if not dispatch_id:
            return jsonify({'status': 'error', 'message': 'dispatch_id required'}), 400
        
        if action not in ['accept', 'reject']:
            return jsonify({'status': 'error', 'message': 'action must be accept or reject'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get dispatch record
        cursor.execute('''
            SELECT d.*, pr.hospital_id FROM dispatches d
            JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.dispatch_id = %s AND d.driver_id = %s
        ''', (dispatch_id, driver_id))
        dispatch = cursor.fetchone()
        
        if not dispatch:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Dispatch not found'}), 404
        
        request_id = dispatch['request_id']
        hospital_id = dispatch['hospital_id']
        
        if action == 'accept':
            # Accept: update dispatch and patient_request to en_route
            cursor.execute('''
                UPDATE dispatches SET status = 'en_route' WHERE dispatch_id = %s
            ''', (dispatch_id,))
            
            cursor.execute('''
                UPDATE patient_requests SET status = 'en_route' WHERE request_id = %s
            ''', (request_id,))
            
            # Log to status_timeline
            cursor.execute('''
                INSERT INTO status_timeline 
                (request_id, dispatch_id, old_status, new_status, action_by, action_type, driver_id, driver_name, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_id, dispatch_id, 'dispatched', 'en_route',
                'driver', 'driver_accepted', driver_id, dispatch['driver_name'],
                'Driver accepted and is en route to pickup location'
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f'[DRIVER-ACCEPT] {request_id} accepted by driver {dispatch["driver_name"]}')
            
            return jsonify({
                'status': 'success',
                'message': 'Assignment accepted, en route',
                'dispatch_id': dispatch_id
            }), 200
        
        elif action == 'reject':
            # Reject: mark driver rejected, reassign to next driver
            print(f'[DRIVER-REJECT] {request_id} rejected by driver {dispatch["driver_name"]}')
            
            # Mark dispatch as driver_rejected
            cursor.execute('''
                UPDATE dispatches SET status = 'driver_rejected' WHERE dispatch_id = %s
            ''', (dispatch_id,))
            
            # Set driver last_rejected_at
            cursor.execute('''
                UPDATE drivers SET last_rejected_at = NOW() WHERE id = %s
            ''', (driver_id,))
            
            # Clear assigned_driver from patient_request, set status back to pending
            cursor.execute('''
                UPDATE patient_requests SET assigned_driver = NULL, assigned_driver_id = NULL, status = 'pending'
                WHERE request_id = %s
            ''', (request_id,))
            
            # Log to status_timeline
            cursor.execute('''
                INSERT INTO status_timeline 
                (request_id, dispatch_id, old_status, new_status, action_by, action_type, driver_id, driver_name, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_id, dispatch_id, 'dispatched', 'driver_rejected',
                'driver', 'driver_rejected', driver_id, dispatch['driver_name'],
                'Driver rejected the assignment'
            ))
            
            # Get patient_request details for reassignment
            cursor.execute('''
                SELECT * FROM patient_requests WHERE request_id = %s
            ''', (request_id,))
            req = cursor.fetchone()
            
            if req:
                # Find next available driver
                cursor.execute('''
                    SELECT * FROM drivers 
                    WHERE hospital_id = %s 
                    AND status = 'Available' 
                    AND assigned_ambulance IS NOT NULL
                    AND (last_rejected_at IS NULL OR TIMESTAMPDIFF(MINUTE, last_rejected_at, NOW()) >= 5)
                ''', (hospital_id,))
                available_drivers = cursor.fetchall()
                
                if available_drivers:
                    # Calculate distances and find nearest driver
                    patient_lat = float(req['latitude'])
                    patient_lng = float(req['longitude'])
                    
                    drivers_with_distance = []
                    for driver_rec in available_drivers:
                        # Get hospital location as proxy
                        cursor.execute('''
                            SELECT latitude, longitude FROM hospitals WHERE id = %s
                        ''', (hospital_id,))
                        hosp = cursor.fetchone()
                        if hosp:
                            driver_lat = float(hosp['latitude'])
                            driver_lng = float(hosp['longitude'])
                        else:
                            driver_lat = patient_lat
                            driver_lng = patient_lng
                        
                        distance_km = calculate_distance(driver_lat, driver_lng, patient_lat, patient_lng)
                        drivers_with_distance.append({
                            'driver': driver_rec,
                            'distance_km': distance_km
                        })
                    
                    # Sort by distance and assign to nearest
                    drivers_with_distance.sort(key=lambda x: x['distance_km'])
                    nearest_driver = drivers_with_distance[0]['driver']
                    
                    # Assign to nearest driver
                    cursor.execute('''
                        UPDATE patient_requests 
                        SET status = 'assigned', assigned_driver = %s, assigned_driver_id = %s
                        WHERE request_id = %s
                    ''', (nearest_driver['username'], nearest_driver['id'], request_id))
                    
                    cursor.execute('''
                        UPDATE drivers SET status = 'On Duty' WHERE id = %s
                    ''', (nearest_driver['id'],))
                    
                    cursor.execute('''
                        UPDATE ambulances SET status = 'On Duty' WHERE ambulance_number = %s
                    ''', (nearest_driver['assigned_ambulance'],))
                    
                    # Create new dispatch
                    new_dispatch_id = f"DSP-2026-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    cursor.execute('''
                        INSERT INTO dispatches 
                        (dispatch_id, request_id, patient_name, patient_phone, location, driver_id, driver_name, 
                         ambulance_id, hospital_id, status, priority)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        new_dispatch_id, request_id, req['patient_name'], req['patient_phone'], 
                        req['pickup_address'], nearest_driver['id'], nearest_driver['name'], 
                        nearest_driver['assigned_ambulance'], hospital_id, 'dispatched', req.get('priority', 'High')
                    ))
                    
                    print(f'[DRIVER-REJECT-REASSIGN] {request_id} reassigned to {nearest_driver["name"]}')
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'status': 'success',
                'message': 'Assignment rejected, reassigned to next driver'
            }), 200
    
    except Exception as e:
        print(f'[DRIVER-RESPOND ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== UPDATE DRIVER LOCATION (Background GPS Tracking) ====================
@app.route('/update-driver-location', methods=['POST'])
def update_driver_location():
    """
    Update driver's current GPS location in real-time.
    Called continuously by driver dashboard watchPosition when driver has active assignment.
    
    Request body:
    - latitude: current latitude
    - longitude: current longitude
    
    Updates drivers table:
    - current_latitude
    - current_longitude
    - location_updated_at = NOW() (database timestamp)
    """
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'status': 'error', 'message': 'latitude and longitude required'}), 400
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Invalid coordinates'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update driver's current location with database timestamp
        cursor.execute('''
            UPDATE drivers 
            SET current_latitude = %s, current_longitude = %s, location_updated_at = NOW()
            WHERE id = %s
        ''', (latitude, longitude, driver_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Location updated'
        }), 200
        
    except Exception as e:
        print(f'[UPDATE-DRIVER-LOCATION ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== GET LIVE TRACKING DATA ====================
@app.route('/get-live-tracking', methods=['GET'])
def get_live_tracking():
    """
    Get live tracking data for a request.
    Public endpoint - NO authentication required.
    
    Query parameter: request_id
    
    Returns:
    - Patient location (latitude, longitude)
    - Hospital info (name, latitude, longitude)
    - Driver info (name, current_latitude, current_longitude, location_updated_at)
    - Ambulance info
    - Dispatch status
    - driver_location_available: boolean (true if driver has recent location)
    """
    try:
        request_id = request.args.get('request_id', '').strip()
        
        if not request_id:
            return jsonify({
                'status': 'error',
                'message': 'request_id query parameter is required'
            }), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get patient request with hospital info
        cursor.execute('''
            SELECT pr.id, pr.request_id, pr.latitude, pr.longitude, 
                   pr.status, pr.assigned_driver_id,
                   h.name as hospital_name, h.latitude as hospital_lat, h.longitude as hospital_lng
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            WHERE pr.request_id = %s
        ''', (request_id,))
        
        patient_request = cursor.fetchone()
        
        if not patient_request:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'Request not found'
            }), 404
        
        # Get driver info with current location
        driver_info = None
        driver_location_available = False
        
        if patient_request['assigned_driver_id']:
            cursor.execute('''
                SELECT id, name, phone, current_latitude, current_longitude, location_updated_at
                FROM drivers
                WHERE id = %s
            ''', (patient_request['assigned_driver_id'],))
            
            driver = cursor.fetchone()
            if driver:
                # Only include latitude/longitude if they are not null
                driver_lat = float(driver['current_latitude']) if driver['current_latitude'] else None
                driver_lng = float(driver['current_longitude']) if driver['current_longitude'] else None
                
                driver_info = {
                    'id': driver['id'],
                    'name': driver['name'],
                    'phone': driver['phone'],
                    'latitude': driver_lat,
                    'longitude': driver_lng,
                    'location_updated_at': driver['location_updated_at'].isoformat() if driver['location_updated_at'] else None
                }
                
                # Check if location is fresh (within last 30 seconds) AND not null
                if driver['location_updated_at'] and driver_lat is not None and driver_lng is not None:
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    time_diff = (now - driver['location_updated_at']).total_seconds()
                    driver_location_available = time_diff <= 30
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'request_id': request_id,
            'dispatch_status': patient_request['status'],
            'patient_location': {
                'latitude': float(patient_request['latitude']),
                'longitude': float(patient_request['longitude'])
            },
            'hospital': {
                'name': patient_request['hospital_name'],
                'latitude': float(patient_request['hospital_lat']) if patient_request['hospital_lat'] else None,
                'longitude': float(patient_request['hospital_lng']) if patient_request['hospital_lng'] else None
            },
            'driver': driver_info,
            'driver_location_available': driver_location_available
        }), 200
        
    except Exception as e:
        print(f'[GET-LIVE-TRACKING ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== CANCEL REQUEST (Patient) ====================
@app.route('/cancel-request', methods=['POST'])
def cancel_request():
    """
    Cancel an active emergency request.
    Public endpoint - can be called by patient.
    
    Request body: request_id
    
    Updates:
    - patient_requests status to 'cancelled'
    - dispatches status to 'cancelled'
    - assigned driver status to 'Available'
    - assigned ambulance status to 'Available'
    """
    try:
        data = request.get_json()
        request_id = data.get('request_id', '').strip()
        
        if not request_id:
            return jsonify({'status': 'error', 'message': 'request_id required'}), 400
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get patient request info
        cursor.execute('''
            SELECT id, assigned_driver_id FROM patient_requests 
            WHERE request_id = %s
        ''', (request_id,))
        req = cursor.fetchone()
        
        if not req:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404
        
        # Update patient request status to cancelled
        cursor.execute('''
            UPDATE patient_requests SET status = 'cancelled' 
            WHERE request_id = %s
        ''', (request_id,))
        
        # Update dispatches status to cancelled
        cursor.execute('''
            UPDATE dispatches SET status = 'cancelled' 
            WHERE request_id = %s
        ''', (request_id,))
        
        # If driver was assigned, release driver and ambulance
        if req['assigned_driver_id']:
            driver_id = req['assigned_driver_id']
            
            # Get driver's assigned ambulance
            cursor.execute('''
                SELECT assigned_ambulance FROM drivers WHERE id = %s
            ''', (driver_id,))
            driver = cursor.fetchone()
            
            # Update driver status to Available
            cursor.execute('''
                UPDATE drivers SET status = 'Available' WHERE id = %s
            ''', (driver_id,))
            
            # Update ambulance status to Available
            if driver and driver['assigned_ambulance']:
                cursor.execute('''
                    UPDATE ambulances SET status = 'Available' 
                    WHERE ambulance_number = %s
                ''', (driver['assigned_ambulance'],))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[CANCEL-REQUEST] {request_id} cancelled')
        
        return jsonify({
            'status': 'success',
            'message': 'Request cancelled successfully'
        }), 200
        
    except Exception as e:
        print(f'[CANCEL-REQUEST ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== GET REQUEST STATUS (Public - No Auth Required) ====================
@app.route('/get-request-status', methods=['GET'])
def get_request_status():
    """
    Get real-time status of a patient request.
    Public endpoint - NO authentication required.
    
    Query parameter: request_id (e.g., /get-request-status?request_id=REQ-20260317120000)
    
    Returns:
    - Current status from patient_requests
    - Assigned driver info (name, phone) from drivers
    - Assigned ambulance number from dispatches
    - Hospital name from hospitals
    - Full status timeline from status_timeline (ordered chronologically)
    - Last updated timestamp from dispatches
    """
    try:
        # Get request_id from query parameter
        request_id = request.args.get('request_id', '').strip()
        
        if not request_id:
            return jsonify({
                'status': 'error',
                'message': 'request_id query parameter is required'
            }), 400
        
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get patient request
        cursor.execute('''
            SELECT * FROM patient_requests WHERE request_id = %s
        ''', (request_id,))
        patient_req = cursor.fetchone()
        
        if not patient_req:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'Request not found'
            }), 404
        
        # Get hospital info
        hospital_name = None
        if patient_req['hospital_id']:
            cursor.execute('''
                SELECT name FROM hospitals WHERE id = %s
            ''', (patient_req['hospital_id'],))
            hospital_row = cursor.fetchone()
            hospital_name = hospital_row['name'] if hospital_row else None
        
        # Get assigned driver info
        driver_name = None
        driver_phone = None
        if patient_req['assigned_driver_id']:
            cursor.execute('''
                SELECT name, phone FROM drivers WHERE id = %s
            ''', (patient_req['assigned_driver_id'],))
            driver_row = cursor.fetchone()
            if driver_row:
                driver_name = driver_row['name']
                driver_phone = driver_row['phone']
        
        # Get assigned ambulance and last updated time
        ambulance_number = None
        last_updated = None
        cursor.execute('''
            SELECT ambulance_id, updated_at FROM dispatches WHERE request_id = %s
            ORDER BY timestamp DESC LIMIT 1
        ''', (request_id,))
        dispatch_row = cursor.fetchone()
        if dispatch_row:
            ambulance_number = dispatch_row['ambulance_id']
            last_updated = dispatch_row['updated_at']
        
        # Get full status timeline - ordered by timestamp (oldest first)
        cursor.execute('''
            SELECT id, request_id, dispatch_id, old_status, new_status, action_by, 
                   action_type, driver_id, driver_name, notes, timestamp
            FROM status_timeline WHERE request_id = %s
            ORDER BY timestamp ASC
        ''', (request_id,))
        timeline_rows = cursor.fetchall()
        
        # Convert timeline to list of dictionaries
        status_timeline = []
        for row in timeline_rows:
            status_timeline.append({
                'id': row['id'],
                'old_status': row['old_status'],
                'new_status': row['new_status'],
                'action_by': row['action_by'],
                'action_type': row['action_type'],
                'driver_name': row['driver_name'],
                'notes': row['notes'],
                'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
            })
        
        cursor.close()
        conn.close()
        
        # Build response
        response = {
            'status': 'success',
            'request_id': request_id,
            'current_status': patient_req['status'],
            'patient_name': patient_req['patient_name'],
            'patient_phone': patient_req['patient_phone'],
            'patient_location': {
                'latitude': float(patient_req['latitude']) if patient_req['latitude'] else None,
                'longitude': float(patient_req['longitude']) if patient_req['longitude'] else None,
                'address': patient_req['pickup_address']
            },
            'hospital': {
                'name': hospital_name,
                'hospital_id': patient_req['hospital_id']
            },
            'assigned_driver': {
                'name': driver_name,
                'phone': driver_phone,
                'driver_id': patient_req['assigned_driver_id']
            },
            'ambulance': {
                'number': ambulance_number
            },
            'priority': patient_req['priority'],
            'request_timestamp': patient_req['timestamp'].isoformat() if hasattr(patient_req['timestamp'], 'isoformat') else str(patient_req['timestamp']),
            'last_updated': last_updated.isoformat() if last_updated and hasattr(last_updated, 'isoformat') else str(last_updated),
            'status_timeline': status_timeline,
            'timeline_count': len(status_timeline)
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print(f'[GET-REQUEST-STATUS ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== SUBMIT FEEDBACK ====================
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    """
    Submit patient feedback after ambulance service completion.
    Public endpoint - NO authentication required.
    
    Request body (JSON):
    {
        "request_id": "REQ-20260317120000",
        "on_time": "yes" or "no",
        "rating": 1-5,
        "driver_rating": 1-5,
        "comment": "optional feedback text"
    }
    
    Returns:
    - Success confirmation with feedback ID
    - Error if request_id doesn't exist
    """
    try:
        data = request.get_json() or {}
        
        request_id = data.get('request_id', '').strip()
        on_time = data.get('on_time')
        rating = data.get('rating')
        driver_rating = data.get('driver_rating')
        comment = data.get('comment', '').strip()
        
        if not request_id:
            return jsonify({
                'status': 'error',
                'message': 'request_id is required'
            }), 400
        
        # Validate ratings
        if rating is not None:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    rating = None
            except:
                rating = None
        
        if driver_rating is not None:
            try:
                driver_rating = int(driver_rating)
                if driver_rating < 1 or driver_rating > 5:
                    driver_rating = None
            except:
                driver_rating = None
        
        # Validate on_time
        if on_time not in ['yes', 'no']:
            on_time = None
        
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verify request exists and get patient info
        cursor.execute('''
            SELECT patient_name, patient_phone FROM patient_requests WHERE request_id = %s
        ''', (request_id,))
        patient_req = cursor.fetchone()
        
        if not patient_req:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'error',
                'message': 'Request not found'
            }), 404
        
        # Insert feedback
        cursor.execute('''
            INSERT INTO feedback (request_id, patient_name, patient_phone, on_time, rating, driver_rating, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (request_id, patient_req['patient_name'], patient_req['patient_phone'], 
              on_time, rating, driver_rating, comment))
        
        conn.commit()
        feedback_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        print(f'[FEEDBACK SAVED] Request: {request_id}, Rating: {rating}/5, Driver: {driver_rating}/5')
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback_id,
            'request_id': request_id
        }), 201
    
    except Exception as e:
        print(f'[SUBMIT-FEEDBACK ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== PATIENT HISTORY ====================
@app.route('/patient-history', methods=['GET'])
def patient_history():
    """
    Get patient's request history.
    Requires patient session (uses session.patient_phone to identify patient).
    Returns last 20 requests with full details and status timelines.
    
    Returns:
    - Hospital name, driver name, final status for each request
    - Full status_timeline entries for each request
    - Ordered by timestamp descending (newest first)
    """
    # Check for patient session
    if session.get('user_type') != 'patient':
        return jsonify({
            'status': 'error',
            'message': 'Patient login required'
        }), 401
    
    patient_phone = session.get('patient_phone')
    if not patient_phone:
        return jsonify({
            'status': 'error',
            'message': 'Patient phone not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get last 20 patient requests with hospital and driver info
        cursor.execute('''
            SELECT 
                pr.request_id,
                pr.patient_name,
                pr.patient_phone,
                pr.pickup_address,
                pr.status as final_status,
                pr.priority,
                pr.timestamp,
                pr.latitude,
                pr.longitude,
                h.name as hospital_name,
                h.id as hospital_id,
                d.name as driver_name,
                d.phone as driver_phone,
                d.id as driver_id,
                disp.dispatch_id,
                disp.ambulance_id,
                disp.updated_at
            FROM patient_requests pr
            LEFT JOIN hospitals h ON pr.hospital_id = h.id
            LEFT JOIN drivers d ON pr.assigned_driver_id = d.id
            LEFT JOIN dispatches disp ON pr.request_id = disp.request_id
            WHERE pr.patient_phone = %s
            ORDER BY pr.timestamp DESC
            LIMIT 20
        ''', (patient_phone,))
        
        requests = cursor.fetchall()
        
        if not requests:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'patient_phone': patient_phone,
                'requests': [],
                'request_count': 0
            }), 200
        
        # Build detailed response with timelines
        requests_list = []
        for req in requests:
            request_id = req['request_id']
            
            # Get status timeline for this request
            cursor.execute('''
                SELECT 
                    id, old_status, new_status, action_by, action_type, 
                    driver_name, notes, timestamp
                FROM status_timeline
                WHERE request_id = %s
                ORDER BY timestamp ASC
            ''', (request_id,))
            
            timeline_rows = cursor.fetchall()
            status_timeline = []
            for row in timeline_rows:
                status_timeline.append({
                    'old_status': row['old_status'],
                    'new_status': row['new_status'],
                    'action_by': row['action_by'],
                    'action_type': row['action_type'],
                    'driver_name': row['driver_name'],
                    'notes': row['notes'],
                    'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
                })
            
            # Add request to list
            requests_list.append({
                'request_id': request_id,
                'patient_name': req['patient_name'],
                'pickup_address': req['pickup_address'],
                'location': {
                    'latitude': float(req['latitude']) if req['latitude'] else None,
                    'longitude': float(req['longitude']) if req['longitude'] else None
                },
                'hospital': {
                    'name': req['hospital_name'],
                    'id': req['hospital_id']
                },
                'driver': {
                    'name': req['driver_name'],
                    'phone': req['driver_phone'],
                    'id': req['driver_id']
                },
                'ambulance': req['ambulance_id'],
                'priority': req['priority'],
                'final_status': req['final_status'],
                'request_timestamp': req['timestamp'].isoformat() if hasattr(req['timestamp'], 'isoformat') else str(req['timestamp']),
                'last_updated': req['updated_at'].isoformat() if req['updated_at'] and hasattr(req['updated_at'], 'isoformat') else str(req['updated_at']) if req['updated_at'] else None,
                'status_timeline': status_timeline,
                'timeline_count': len(status_timeline)
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'patient_phone': patient_phone,
            'requests': requests_list,
            'request_count': len(requests_list)
        }), 200
    
    except Exception as e:
        print(f'[PATIENT-HISTORY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== HOSPITAL HISTORY ====================
@app.route('/hospital-history', methods=['GET'])
def hospital_history():
    """
    Get hospital's dispatch history.
    Requires hospital session.
    Returns last 100 dispatches with full timelines.
    
    Calculates:
    - Average response time: TIMESTAMPDIFF between dispatch creation 
      and status_timeline entry where status = 'picked_up'
    - Uses real database calculation, not estimates
    """
    # Check for hospital session
    if session.get('user_type') != 'hospital':
        return jsonify({
            'status': 'error',
            'message': 'Hospital login required'
        }), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({
            'status': 'error',
            'message': 'Hospital ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get last 100 dispatches for this hospital
        cursor.execute('''
            SELECT 
                d.dispatch_id,
                d.request_id,
                d.patient_name,
                d.patient_phone,
                d.location,
                d.driver_id,
                d.driver_name,
                d.ambulance_id,
                d.status,
                d.priority,
                d.timestamp,
                d.updated_at,
                pr.latitude,
                pr.longitude
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.hospital_id = %s
            ORDER BY d.timestamp DESC
            LIMIT 100
        ''', (hospital_id,))
        
        dispatches = cursor.fetchall()
        
        if not dispatches:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'hospital_id': hospital_id,
                'dispatches': [],
                'dispatch_count': 0,
                'avg_response_minutes': None
            }), 200
        
        # Calculate average response time
        cursor.execute('''
            SELECT AVG(response_time) as avg_response
            FROM (
                SELECT d.dispatch_id,
                       TIMESTAMPDIFF(MINUTE, d.timestamp, st_pickup.timestamp) as response_time
                FROM dispatches d
                LEFT JOIN (
                    SELECT request_id, timestamp 
                    FROM status_timeline 
                    WHERE new_status = 'picked_up'
                ) st_pickup ON d.request_id = st_pickup.request_id
                WHERE d.hospital_id = %s AND st_pickup.timestamp IS NOT NULL
            ) AS response_times
        ''', (hospital_id,))
        
        avg_response_row = cursor.fetchone()
        avg_response_minutes = round(avg_response_row['avg_response'], 2) if avg_response_row and avg_response_row['avg_response'] else None
        
        # Build detailed response with timelines
        dispatches_list = []
        for dispatch in dispatches:
            dispatch_id = dispatch['dispatch_id']
            request_id = dispatch['request_id']
            
            # Get status timeline for this dispatch
            cursor.execute('''
                SELECT 
                    id, old_status, new_status, action_by, action_type, 
                    driver_name, notes, timestamp
                FROM status_timeline
                WHERE dispatch_id = %s OR request_id = %s
                ORDER BY timestamp ASC
            ''', (dispatch_id, request_id))
            
            timeline_rows = cursor.fetchall()
            status_timeline = []
            for row in timeline_rows:
                status_timeline.append({
                    'old_status': row['old_status'],
                    'new_status': row['new_status'],
                    'action_by': row['action_by'],
                    'action_type': row['action_type'],
                    'driver_name': row['driver_name'],
                    'notes': row['notes'],
                    'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
                })
            
            # Add dispatch to list
            dispatches_list.append({
                'dispatch_id': dispatch_id,
                'request_id': request_id,
                'patient_name': dispatch['patient_name'],
                'patient_phone': dispatch['patient_phone'],
                'location': dispatch['location'],
                'patient_coordinates': {
                    'latitude': float(dispatch['latitude']) if dispatch['latitude'] else None,
                    'longitude': float(dispatch['longitude']) if dispatch['longitude'] else None
                },
                'driver': {
                    'name': dispatch['driver_name'],
                    'id': dispatch['driver_id']
                },
                'ambulance': dispatch['ambulance_id'],
                'priority': dispatch['priority'],
                'status': dispatch['status'],
                'timestamp': dispatch['timestamp'].isoformat() if hasattr(dispatch['timestamp'], 'isoformat') else str(dispatch['timestamp']),
                'updated_at': dispatch['updated_at'].isoformat() if dispatch['updated_at'] and hasattr(dispatch['updated_at'], 'isoformat') else str(dispatch['updated_at']) if dispatch['updated_at'] else None,
                'status_timeline': status_timeline,
                'timeline_count': len(status_timeline)
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'hospital_id': hospital_id,
            'dispatches': dispatches_list,
            'dispatch_count': len(dispatches_list),
            'avg_response_minutes': avg_response_minutes
        }), 200
    
    except Exception as e:
        print(f'[HOSPITAL-HISTORY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== DRIVER HISTORY ====================
@app.route('/driver-history', methods=['GET'])
def driver_history():
    """
    Get driver's completed trips history.
    Requires driver session.
    Returns last 50 completed dispatches with full timelines.
    
    Includes:
    - Patient name, location, completion timestamp
    - Trip duration calculated from status_timeline:
      TIMESTAMPDIFF between 'dispatched' and 'completed' status changes
    """
    # Check for driver session
    if session.get('user_type') != 'driver':
        return jsonify({
            'status': 'error',
            'message': 'Driver login required'
        }), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({
            'status': 'error',
            'message': 'Driver ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get last 50 completed dispatches for this driver
        cursor.execute('''
            SELECT 
                d.dispatch_id,
                d.request_id,
                d.patient_name,
                d.patient_phone,
                d.location,
                d.status,
                d.priority,
                d.timestamp,
                d.updated_at,
                pr.latitude,
                pr.longitude,
                h.name as hospital_name,
                h.id as hospital_id
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.driver_id = %s AND d.status = 'completed'
            ORDER BY d.updated_at DESC
            LIMIT 50
        ''', (driver_id,))
        
        dispatches = cursor.fetchall()
        
        if not dispatches:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'success',
                'driver_id': driver_id,
                'trips': [],
                'trip_count': 0
            }), 200
        
        # Build detailed response with timelines and trip durations
        trips_list = []
        for dispatch in dispatches:
            dispatch_id = dispatch['dispatch_id']
            request_id = dispatch['request_id']
            
            # Get status timeline for this dispatch
            cursor.execute('''
                SELECT 
                    id, old_status, new_status, action_by, action_type, 
                    driver_name, notes, timestamp
                FROM status_timeline
                WHERE dispatch_id = %s OR request_id = %s
                ORDER BY timestamp ASC
            ''', (dispatch_id, request_id))
            
            timeline_rows = cursor.fetchall()
            status_timeline = []
            dispatched_timestamp = None
            completed_timestamp = None
            
            for row in timeline_rows:
                # Track timestamps for duration calculation
                if row['new_status'] == 'dispatched' or (row['old_status'] is None and row['new_status'] == 'assigned'):
                    if not dispatched_timestamp:
                        dispatched_timestamp = row['timestamp']
                if row['new_status'] == 'completed':
                    completed_timestamp = row['timestamp']
                
                status_timeline.append({
                    'old_status': row['old_status'],
                    'new_status': row['new_status'],
                    'action_by': row['action_by'],
                    'action_type': row['action_type'],
                    'driver_name': row['driver_name'],
                    'notes': row['notes'],
                    'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
                })
            
            # Calculate trip duration using database timestamps
            trip_duration_minutes = None
            if dispatched_timestamp and completed_timestamp:
                trip_duration_minutes = int((completed_timestamp - dispatched_timestamp).total_seconds() / 60)
            
            # Add trip to list
            trips_list.append({
                'dispatch_id': dispatch_id,
                'request_id': request_id,
                'patient_name': dispatch['patient_name'],
                'patient_phone': dispatch['patient_phone'],
                'location': dispatch['location'],
                'patient_coordinates': {
                    'latitude': float(dispatch['latitude']) if dispatch['latitude'] else None,
                    'longitude': float(dispatch['longitude']) if dispatch['longitude'] else None
                },
                'hospital': {
                    'name': dispatch['hospital_name'],
                    'id': dispatch['hospital_id']
                },
                'priority': dispatch['priority'],
                'status': dispatch['status'],
                'completion_timestamp': dispatch['updated_at'].isoformat() if dispatch['updated_at'] and hasattr(dispatch['updated_at'], 'isoformat') else str(dispatch['updated_at']) if dispatch['updated_at'] else None,
                'trip_duration_minutes': trip_duration_minutes,
                'status_timeline': status_timeline,
                'timeline_count': len(status_timeline)
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'driver_id': driver_id,
            'trips': trips_list,
            'trip_count': len(trips_list)
        }), 200
    
    except Exception as e:
        print(f'[DRIVER-HISTORY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/driver/day-wise-distance', methods=['GET'])
def driver_day_wise_distance():
    """
    Get driver's day-wise distance traveled grouped by date (last 30 days).
    Requires driver session.
    Returns list of dates with trip count and total distance (in km).
    
    Distance is calculated from pickup location to hospital using Haversine formula.
    Uses same calculation method as total-distance and distance-today routes.
    """
    # Check for driver session
    if session.get('user_type') != 'driver':
        return jsonify({
            'status': 'error',
            'message': 'Driver login required'
        }), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({
            'status': 'error',
            'message': 'Driver ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get all completed dispatches for this driver with location data (LAST 30 DAYS)
        # Group by date using same method as total-distance and distance-today
        query = '''
            SELECT 
                DATE(d.updated_at) as dispatch_date,
                COUNT(*) as trip_count,
                d.driver_id,
                d.request_id,
                d.updated_at,
                pr.latitude as pickup_lat,
                pr.longitude as pickup_lng,
                h.latitude as hospital_lat,
                h.longitude as hospital_lng
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.driver_id = %s AND d.status = 'completed' 
              AND DATE(d.updated_at) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY dispatch_date, d.request_id, d.dispatch_id
            ORDER BY d.updated_at DESC
        '''
        
        print(f'[DAY-WISE-DISTANCE] Query: {query} (driver_id={driver_id})')
        cursor.execute(query, (driver_id,))
        
        dispatches = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Calculate distance for each dispatch and group by date
        # Uses SAME Haversine calculation as total-distance and distance-today
        day_map = {}
        for dispatch in dispatches:
            distance_km = 0
            
            # SAME calculation as total-distance and distance-today
            if (dispatch['pickup_lat'] and dispatch['pickup_lng'] and 
                dispatch['hospital_lat'] and dispatch['hospital_lng']):
                distance_km = calculate_distance(
                    float(dispatch['pickup_lat']),
                    float(dispatch['pickup_lng']),
                    float(dispatch['hospital_lat']),
                    float(dispatch['hospital_lng'])
                )
            
            # Get dispatch date as string
            dispatch_date = str(dispatch['dispatch_date']) if dispatch['dispatch_date'] else 'Unknown'
            
            # Group by date
            if dispatch_date not in day_map:
                day_map[dispatch_date] = {
                    'count': 0,
                    'total_distance': 0.0
                }
            
            day_map[dispatch_date]['count'] += 1
            day_map[dispatch_date]['total_distance'] += distance_km
        
        # Convert to list format for JSON response
        result_list = []
        for date_str in sorted(day_map.keys(), reverse=True):
            result_list.append({
                'dispatch_date': date_str,
                'trip_count': day_map[date_str]['count'],
                'total_distance': round(day_map[date_str]['total_distance'], 2)
            })
        
        print(f'[DAY-WISE-DISTANCE] Found {len(result_list)} days of distance data for driver {driver_id}')
        return jsonify(result_list), 200
        
    except Exception as e:
        print(f'[DAY-WISE-DISTANCE ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/driver/total-distance', methods=['GET'])
def driver_total_distance():
    """
    Get driver's total distance traveled across all completed trips.
    Requires driver session.
    Returns total distance in km.
    
    Uses EXACT same calculation as day-wise-distance: Haversine formula from pickup to hospital.
    """
    # Check for driver session
    if session.get('user_type') != 'driver':
        return jsonify({
            'status': 'error',
            'message': 'Driver login required'
        }), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({
            'status': 'error',
            'message': 'Driver ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # SAME QUERY as day-wise-distance, just all data with no date grouping
        query = '''
            SELECT 
                d.dispatch_id,
                pr.latitude as pickup_lat,
                pr.longitude as pickup_lng,
                h.latitude as hospital_lat,
                h.longitude as hospital_lng
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.driver_id = %s AND d.status = 'completed'
            ORDER BY d.updated_at DESC
        '''
        
        print(f'[TOTAL-DISTANCE] Query: {query} (driver_id={driver_id})')
        cursor.execute(query, (driver_id,))
        
        dispatches = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Calculate total distance using SAME method as day-wise-distance
        total_distance_km = 0.0
        for dispatch in dispatches:
            distance_km = 0
            
            # SAME Haversine calculation as day-wise-distance
            if (dispatch['pickup_lat'] and dispatch['pickup_lng'] and 
                dispatch['hospital_lat'] and dispatch['hospital_lng']):
                distance_km = calculate_distance(
                    float(dispatch['pickup_lat']),
                    float(dispatch['pickup_lng']),
                    float(dispatch['hospital_lat']),
                    float(dispatch['hospital_lng'])
                )
            
            total_distance_km += distance_km
        
        total_distance_km = round(total_distance_km, 2)
        print(f'[TOTAL-DISTANCE] Driver {driver_id}: {total_distance_km} km across {len(dispatches)} trips')
        
        return jsonify({
            'status': 'success',
            'total_distance_km': total_distance_km,
            'trip_count': len(dispatches)
        }), 200
        
    except Exception as e:
        print(f'[TOTAL-DISTANCE ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/driver/distance-today', methods=['GET'])
def driver_distance_today():
    """
    Get driver's distance traveled today (CURDATE only).
    Requires driver session.
    Returns total distance in km for today.
    
    Uses EXACT same calculation as day-wise-distance: Haversine formula from pickup to hospital.
    """
    # Check for driver session
    if session.get('user_type') != 'driver':
        return jsonify({
            'status': 'error',
            'message': 'Driver login required'
        }), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({
            'status': 'error',
            'message': 'Driver ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # SAME QUERY as day-wise-distance but filtered to TODAY only
        query = '''
            SELECT 
                d.dispatch_id,
                pr.latitude as pickup_lat,
                pr.longitude as pickup_lng,
                h.latitude as hospital_lat,
                h.longitude as hospital_lng
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.driver_id = %s AND d.status = 'completed' AND DATE(d.updated_at) = CURDATE()
            ORDER BY d.updated_at DESC
        '''
        
        print(f'[DISTANCE-TODAY] Query: {query} (driver_id={driver_id})')
        cursor.execute(query, (driver_id,))
        
        dispatches = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Calculate today's distance using SAME method as day-wise-distance
        today_distance_km = 0.0
        for dispatch in dispatches:
            distance_km = 0
            
            # SAME Haversine calculation as day-wise-distance
            if (dispatch['pickup_lat'] and dispatch['pickup_lng'] and 
                dispatch['hospital_lat'] and dispatch['hospital_lng']):
                distance_km = calculate_distance(
                    float(dispatch['pickup_lat']),
                    float(dispatch['pickup_lng']),
                    float(dispatch['hospital_lat']),
                    float(dispatch['hospital_lng'])
                )
            
            today_distance_km += distance_km
        
        today_distance_km = round(today_distance_km, 2)
        print(f'[DISTANCE-TODAY] Driver {driver_id}: {today_distance_km} km across {len(dispatches)} trips')
        
        return jsonify({
            'status': 'success',
            'distance_today_km': today_distance_km,
            'trip_count': len(dispatches)
        }), 200
        
    except Exception as e:
        print(f'[DISTANCE-TODAY ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/driver/profile-stats', methods=['GET'])
def driver_profile_stats():
    """
    Get driver's profile stats: KM Today and This Month trips count.
    Requires driver session.
    Returns KM traveled today and number of completed trips this month.
    
    Filters:
    - KM Today: WHERE DATE(d.updated_at) = CURDATE() AND d.status = 'completed'
    - This Month: WHERE MONTH(d.updated_at) = MONTH(CURDATE()) 
                  AND YEAR(d.updated_at) = YEAR(CURDATE()) 
                  AND d.status = 'completed'
    """
    # Check for driver session
    if session.get('user_type') != 'driver':
        return jsonify({
            'status': 'error',
            'message': 'Driver login required'
        }), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({
            'status': 'error',
            'message': 'Driver ID not found in session'
        }), 400
    
    try:
        conn = get_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # ===== GET KM TODAY =====
        km_today_query = '''
            SELECT 
                d.dispatch_id,
                pr.latitude as pickup_lat,
                pr.longitude as pickup_lng,
                h.latitude as hospital_lat,
                h.longitude as hospital_lng
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            LEFT JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.driver_id = %s AND d.status = 'completed' AND DATE(d.updated_at) = CURDATE()
            ORDER BY d.updated_at DESC
        '''
        
        print(f'[PROFILE-STATS-TODAY] Query: {km_today_query} (driver_id={driver_id})')
        cursor.execute(km_today_query, (driver_id,))
        
        today_dispatches = cursor.fetchall()
        
        # Calculate today's distance using Haversine formula
        today_distance_km = 0.0
        for dispatch in today_dispatches:
            distance_km = 0
            
            if (dispatch['pickup_lat'] and dispatch['pickup_lng'] and 
                dispatch['hospital_lat'] and dispatch['hospital_lng']):
                distance_km = calculate_distance(
                    float(dispatch['pickup_lat']),
                    float(dispatch['pickup_lng']),
                    float(dispatch['hospital_lat']),
                    float(dispatch['hospital_lng'])
                )
            
            today_distance_km += distance_km
        
        today_distance_km = round(today_distance_km, 2)
        
        # ===== GET THIS MONTH TRIPS COUNT =====
        this_month_query = '''
            SELECT COUNT(*) as trip_count
            FROM dispatches d
            WHERE d.driver_id = %s 
              AND d.status = 'completed'
              AND MONTH(d.updated_at) = MONTH(CURDATE())
              AND YEAR(d.updated_at) = YEAR(CURDATE())
        '''
        
        print(f'[PROFILE-STATS-MONTH] Query: {this_month_query} (driver_id={driver_id})')
        cursor.execute(this_month_query, (driver_id,))
        
        month_result = cursor.fetchone()
        this_month_trips = month_result['trip_count'] if month_result else 0
        
        cursor.close()
        conn.close()
        
        print(f'[PROFILE-STATS] Driver {driver_id}: {today_distance_km} km today, {this_month_trips} trips this month')
        
        return jsonify({
            'status': 'success',
            'distance_today_km': today_distance_km,
            'trips_today_count': len(today_dispatches),
            'trips_this_month': this_month_trips
        }), 200
        
    except Exception as e:
        print(f'[PROFILE-STATS ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/driver/update-location', methods=['POST'])
def driver_update_location():
    """Save driver's current GPS location to database (from browser geolocation)"""
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Driver ID not found'}), 400
    
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'status': 'error', 'message': 'Latitude and longitude required'}), 400
        
        latitude = float(latitude)
        longitude = float(longitude)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update driver's current location in drivers table
        cursor.execute('''
            UPDATE drivers SET 
                current_latitude = %s, 
                current_longitude = %s, 
                location_updated_at = NOW()
            WHERE id = %s
        ''', (latitude, longitude, driver_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f'[GPS-UPDATE] Driver {driver_id}: Updated location to {latitude}, {longitude}')
        
        return jsonify({
            'status': 'success',
            'message': 'Location updated',
            'latitude': latitude,
            'longitude': longitude
        }), 200
        
    except Exception as e:
        print(f'[GPS-UPDATE ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/driver/get-location', methods=['GET'])
def driver_get_location():
    """Get driver's latest GPS location from database"""
    if session.get('user_type') != 'driver':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'status': 'error', 'message': 'Driver ID not found'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get driver's latest location
        cursor.execute('''
            SELECT current_latitude, current_longitude, location_updated_at, name 
            FROM drivers 
            WHERE id = %s
        ''', (driver_id,))
        
        driver = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not driver:
            return jsonify({'status': 'error', 'message': 'Driver not found'}), 404
        
        latitude = float(driver['current_latitude']) if driver['current_latitude'] else None
        longitude = float(driver['current_longitude']) if driver['current_longitude'] else None
        
        if latitude is None or longitude is None:
            return jsonify({
                'status': 'success',
                'latitude': None,
                'longitude': None,
                'name': driver['name'],
                'message': 'No location data yet'
            }), 200
        
        print(f'[GPS-GET] Driver {driver_id} ({driver["name"]}): {latitude}, {longitude}')
        
        return jsonify({
            'status': 'success',
            'latitude': latitude,
            'longitude': longitude,
            'name': driver['name'],
            'last_update': str(driver['location_updated_at']) if driver['location_updated_at'] else None
        }), 200
        
    except Exception as e:
        print(f'[GPS-GET ERROR] {str(e)}')
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get-driver-live-data', methods=['GET'])
def get_driver_live_data():
    """
    Get real live data for driver dashboard:
    - Current assignment
    - Completed trips today
    - All active assignments
    Requires driver login
    """
    if session.get('user_type') != 'driver':
        return jsonify({'error': 'Unauthorized'}), 401
    
    driver_id = session.get('driver_id')
    driver_username = session.get('driver_username') or session.get('username')
    
    if not driver_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get current active assignment
        cursor.execute('''
            SELECT d.*, pr.latitude, pr.longitude, pr.pickup_address
            FROM dispatches d
            JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.driver_id = %s AND d.status IN ('dispatched', 'en_route', 'picked_up')
            ORDER BY d.timestamp DESC
            LIMIT 1
        ''', (driver_id,))
        current_assignment = cursor.fetchone()
        
        # Get completed trips today
        cursor.execute('''
            SELECT d.*, pr.latitude, pr.longitude, pr.pickup_address
            FROM dispatches d
            LEFT JOIN patient_requests pr ON d.request_id = pr.request_id
            WHERE d.driver_id = %s AND d.status = 'completed'
            AND DATE(d.updated_at) = CURDATE()
            ORDER BY d.updated_at DESC
        ''', (driver_id,))
        completed_today = cursor.fetchall()
        
        # Get driver current status and info
        cursor.execute('''
            SELECT status, assigned_ambulance FROM drivers WHERE id = %s
        ''', (driver_id,))
        driver_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Prepare response
        response_data = {
            'status': 'success',
            'current_assignment': None,
            'completed_trips_today': [],
            'driver_status': driver_info['status'] if driver_info else 'Unknown',
            'ambulance': driver_info['assigned_ambulance'] if driver_info else None
        }
        
        # Add current assignment if exists
        if current_assignment:
            response_data['current_assignment'] = {
                'dispatch_id': current_assignment['dispatch_id'],
                'request_id': current_assignment['request_id'],
                'patient_name': current_assignment['patient_name'],
                'patient_phone': current_assignment['patient_phone'],
                'location': current_assignment['pickup_address'],
                'latitude': float(current_assignment['latitude']) if current_assignment['latitude'] else None,
                'longitude': float(current_assignment['longitude']) if current_assignment['longitude'] else None,
                'priority': current_assignment['priority'],
                'status': current_assignment['status'],
                'timestamp': current_assignment['timestamp'].isoformat() if hasattr(current_assignment['timestamp'], 'isoformat') else str(current_assignment['timestamp'])
            }
        
        # Add completed trips
        for trip in completed_today:
            response_data['completed_trips_today'].append({
                'dispatch_id': trip['dispatch_id'],
                'patient_name': trip['patient_name'],
                'patient_phone': trip['patient_phone'],
                'location': trip['pickup_address'],
                'status': trip['status'],
                'priority': trip['priority'],
                'completed_at': trip['updated_at'].isoformat() if hasattr(trip['updated_at'], 'isoformat') else str(trip['updated_at'])
            })
        
        return jsonify(response_data), 200
    
    except Exception as e:
        print(f'[GET-DRIVER-LIVE-DATA ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500

# ==================== GEOCODING HELPER FUNCTION ====================

def reverse_geocode(latitude, longitude):
    """
    Reverse geocode latitude/longitude to a human-readable place name.
    Uses Google Maps Geocoding API.
    Falls back to coordinates if API fails.
    """
    try:
        lat = float(latitude)
        lng = float(longitude)
        
        # Build geocoding API request
        api_key = GOOGLE_MAPS_API_KEY
        if not api_key:
            # Fallback if no API key
            return f'{lat:.4f}, {lng:.4f}'
        
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'latlng': f'{lat},{lng}',
            'key': api_key,
            'language': 'en'
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                # Return the formatted address (most general/readable)
                address = data['results'][0].get('formatted_address', f'{lat:.4f}, {lng:.4f}')
                return address
        
        # Fallback to coordinates if API fails or returns no results
        return f'{lat:.4f}, {lng:.4f}'
    
    except Exception as e:
        print(f'[GEOCODING ERROR] {str(e)}')
        try:
            return f'{float(latitude):.4f}, {float(longitude):.4f}'
        except:
            return 'Unknown Location'

# ==================== GEOCODING API ENDPOINT ====================

@app.route('/api/get-place-name', methods=['GET'])
def api_get_place_name():
    """
    Convert GPS coordinates to human-readable place name.
    Query params: lat (latitude), lng (longitude)
    Returns: {'status': 'success', 'place_name': '...'} or {'status': 'error', 'message': '...'}
    """
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        
        if lat is None or lng is None:
            return jsonify({'status': 'error', 'message': 'lat and lng parameters required'}), 400
        
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'lat and lng must be valid numbers'}), 400
        
        place_name = reverse_geocode(lat, lng)
        return jsonify({'status': 'success', 'place_name': place_name}), 200
    
    except Exception as e:
        print(f'[API GET PLACE NAME ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== HOSPITAL BED AVAILABILITY API ====================

@app.route('/api/hospital-beds', methods=['GET'])
def api_hospital_beds():
    """Get all hospitals with their bed availability and occupancy status (public endpoint)"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id, name, total_beds, available_beds
            FROM hospitals
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            AND COALESCE(status, 'approved') = 'approved'
            ORDER BY id ASC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        hospitals = []
        for row in rows:
            total_beds = row['total_beds'] or 0
            available_beds = row['available_beds'] or 0

            if available_beds == 0:
                bed_status = 'full'
            elif total_beds > 0 and (available_beds / total_beds) < 0.2:
                bed_status = 'near_full'
            else:
                bed_status = 'available'

            occupancy_percent = int((total_beds - available_beds) / total_beds * 100) if total_beds > 0 else 0

            hospitals.append({
                'id': row['id'],
                'name': row['name'],
                'total_beds': total_beds,
                'available_beds': available_beds,
                'occupancy_percent': occupancy_percent,
                'status': bed_status
            })

        return jsonify({'hospitals': hospitals}), 200

    except Exception as e:
        print(f'[API HOSPITAL BEDS ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/hospital-beds/update', methods=['POST'])
def api_hospital_beds_update():
    """Admin endpoint to update available beds for any hospital"""
    if not is_admin_logged_in():
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'JSON body required'}), 400

        hospital_id = data.get('hospital_id')
        available_beds = data.get('available_beds')

        if hospital_id is None or available_beds is None:
            return jsonify({'status': 'error', 'message': 'hospital_id and available_beds are required'}), 400

        try:
            hospital_id = int(hospital_id)
            available_beds = int(available_beds)
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'hospital_id and available_beds must be integers'}), 400

        if available_beds < 0:
            return jsonify({'status': 'error', 'message': 'available_beds cannot be negative'}), 400

        conn = get_db()
        if not conn:
            return jsonify({'status': 'error', 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, total_beds FROM hospitals WHERE id = %s', (hospital_id,))
        hospital = cursor.fetchone()

        if not hospital:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Hospital not found'}), 404

        total_beds = hospital['total_beds'] or 0
        if available_beds > total_beds:
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'error',
                'message': f'available_beds cannot exceed total_beds ({total_beds})'
            }), 400

        cursor.execute('UPDATE hospitals SET available_beds = %s WHERE id = %s', (available_beds, hospital_id))
        conn.commit()
        cursor.close()
        conn.close()

        occupancy_percent = int((total_beds - available_beds) / total_beds * 100) if total_beds > 0 else 0
        print(f'[ADMIN BED UPDATE] Hospital {hospital["name"]} (ID: {hospital_id}): available_beds={available_beds}')

        return jsonify({
            'status': 'success',
            'message': 'Beds updated successfully',
            'hospital_id': hospital_id,
            'hospital_name': hospital['name'],
            'total_beds': total_beds,
            'available_beds': available_beds,
            'occupied_beds': total_beds - available_beds,
            'occupancy_percent': occupancy_percent
        }), 200

    except Exception as e:
        print(f'[API HOSPITAL BEDS UPDATE ERROR] {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== BACKGROUND TASKS & SSE MANAGEMENT ====================

# Global SSE client management
_sse_clients = {}  # Format: {hospital_id: [client_queue1, client_queue2, ...]}
_sse_lock = threading.Lock()

def broadcast_to_hospital(hospital_id, event_type, data):
    """Send real-time event to all connected clients of a hospital."""
    with _sse_lock:
        if hospital_id in _sse_clients and _sse_clients[hospital_id]:
            # Create SSE message
            message = f"id: {datetime.now().timestamp()}\n"
            message += f"event: {event_type}\n"
            message += f"data: {json.dumps(data)}\n\n"
            
            # Send to all connected clients
            dead_clients = []
            for queue in _sse_clients[hospital_id]:
                try:
                    queue.put(message)
                except:
                    dead_clients.append(queue)
            
            # Remove dead clients
            for queue in dead_clients:
                _sse_clients[hospital_id].remove(queue)

def auto_forward_stale_requests():
    """
    Background thread: every 5 seconds checks for pending requests with
    available drivers and auto-assigns. Every 30 seconds also checks two
    stale cases:

    CASE 1 — Still 'pending' after 60s with no driver assigned:
      → Forward to next best hospital (AI-scored).

    CASE 2 — 'accepted'/'assigned' but driver hasn't moved to en_route in 2 minutes:
      → Try another available driver at SAME hospital first.
      → If no other driver available → forward to next best hospital.
    """
    _stale_check_counter = 0
    _cleanup_counter = 0
    while True:
        try:
            threading.Event().wait(5)  # check every 5 seconds
            _stale_check_counter += 1
            _cleanup_counter += 1

            conn = get_db()
            if not conn:
                print('[AUTO-FORWARD] DB connection failed, skipping')
                continue

            cursor = conn.cursor(dictionary=True)

            # ── AUTO-ACCEPT: pending requests with available driver ────────
            cursor.execute("""
                SELECT pr.request_id, pr.hospital_id, pr.latitude, pr.longitude,
                       pr.patient_name, pr.patient_phone, pr.rejected_by
                FROM patient_requests pr
                WHERE pr.status = 'pending'
                AND (pr.cancelled IS NULL OR pr.cancelled = 0)
                AND DATE(pr.timestamp) = CURDATE()
                LIMIT 20
            """)
            pending_requests = cursor.fetchall()

            for req in pending_requests:
                try:
                    hospital_id = req['hospital_id']

                    # Lock the driver row before assigning
                    cursor.execute("""
                        SELECT * FROM drivers
                        WHERE hospital_id = %s
                        AND status = 'Available'
                        AND assigned_ambulance IS NOT NULL
                        LIMIT 1
                        FOR UPDATE
                    """, (hospital_id,))
                    driver = cursor.fetchone()

                    if driver:
                        # Auto assign driver
                        cursor.execute("""
                            UPDATE patient_requests
                            SET status='assigned', assigned_driver=%s, assigned_driver_id=%s
                            WHERE request_id=%s
                        """, (driver['username'], driver['id'], req['request_id']))

                        cursor.execute("UPDATE drivers SET status='On Duty' WHERE id=%s", (driver['id'],))
                        cursor.execute("UPDATE ambulances SET status='On Duty' WHERE ambulance_number=%s",
                                       (driver['assigned_ambulance'],))

                        # Create dispatch
                        dispatch_id = f"DSP-{int(datetime.now().timestamp())}"
                        cursor.execute("""
                            INSERT INTO dispatches
                            (dispatch_id, request_id, patient_name, patient_phone, location,
                             driver_id, driver_name, ambulance_id, hospital_id, status, priority)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'dispatched','High')
                        """, (dispatch_id, req['request_id'], req['patient_name'], req['patient_phone'],
                              f"{req['latitude']},{req['longitude']}", driver['id'], driver['name'],
                              driver['assigned_ambulance'], hospital_id))

                        conn.commit()
                        print(f"[AUTO-ACCEPT] {req['request_id']} assigned to {driver['name']}")

                        broadcast_to_hospital(hospital_id, 'new_emergency', {
                            'request_id': req['request_id'],
                            'patient_name': req['patient_name'],
                            'message': 'Auto-assigned to driver'
                        })
                except Exception as e:
                    print(f'[AUTO-ACCEPT ERROR] {req["request_id"]}: {e}')
                    try: conn.rollback()
                    except: pass

            # Only run stale-forward checks every 6 iterations (every 30 seconds)
            if _stale_check_counter % 6 != 0:
                cursor.close()
                conn.close()
                continue

            # ── CASE 1: pending > 60s, no active dispatch ─────────────────
            cursor.execute('''
                SELECT pr.request_id, pr.hospital_id, pr.latitude, pr.longitude,
                       pr.patient_name, pr.patient_phone, pr.rejected_by, pr.timestamp
                FROM patient_requests pr
                WHERE pr.status = 'pending'
                  AND (pr.cancelled IS NULL OR pr.cancelled = 0)
                  AND pr.timestamp < DATE_SUB(NOW(), INTERVAL 60 SECOND)
                  AND pr.request_id NOT IN (
                      SELECT request_id FROM dispatches
                      WHERE status IN ('dispatched', 'accepted', 'picked_up')
                  )
                LIMIT 20
            ''')
            pending_stale = cursor.fetchall()

            # ── CASE 2: accepted/assigned > 2 min, driver still not en_route ─
            cursor.execute('''
                SELECT pr.request_id, pr.hospital_id, pr.latitude, pr.longitude,
                       pr.patient_name, pr.patient_phone, pr.rejected_by,
                       pr.assigned_driver_id, pr.timestamp
                FROM patient_requests pr
                WHERE pr.status IN ('accepted', 'assigned')
                  AND (pr.cancelled IS NULL OR pr.cancelled = 0)
                  AND pr.timestamp < DATE_SUB(NOW(), INTERVAL 60 SECOND)
                LIMIT 20
            ''')
            driver_stale = cursor.fetchall()

            if pending_stale:
                print(f'[AUTO-FORWARD] {len(pending_stale)} pending-stale requests')
            if driver_stale:
                print(f'[AUTO-FORWARD] {len(driver_stale)} driver-stale requests (no response in 2 min)')

            # ── Helper: forward to next best hospital ─────────────────────
            def forward_to_next_hospital(req, cursor, conn, reason='stale'):
                request_id       = req['request_id']
                current_hosp_id  = req['hospital_id']
                patient_lat      = float(req['latitude'])
                patient_lng      = float(req['longitude'])

                rejected_by = json.loads(req['rejected_by']) if req['rejected_by'] else []
                if current_hosp_id not in rejected_by:
                    rejected_by.append(current_hosp_id)

                # Score all remaining hospitals with AI
                cursor.execute('''
                    SELECT h.id, h.name, h.latitude, h.longitude,
                           h.available_beds, h.total_beds
                    FROM hospitals h
                    WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL
                      AND h.available_beds > 0
                      AND COALESCE(h.status, 'approved') = 'approved'
                ''')
                all_hospitals = cursor.fetchall()

                # Resolve current hospital name for logging
                hospital_name = next(
                    (h['name'] for h in all_hospitals if h['id'] == current_hosp_id),
                    f'Hospital #{current_hosp_id}'
                )

                candidates = []
                for h in all_hospitals:
                    dist = calculate_distance(patient_lat, patient_lng,
                                              float(h['latitude']), float(h['longitude']))
                    eta  = (dist / 40.0) * 60  # simple estimate in minutes
                    candidates.append({'id': h['id'], 'name': h['name'], 'eta': eta, 'dist': dist})

                # Only forward to nearby hospitals (within top 6 nearest)
                candidates.sort(key=lambda x: x['dist'])
                nearby_candidates = candidates[:6]  # Same pool as /nearest-hospitals

                # From nearby_candidates, exclude already rejected hospitals
                available = [h for h in nearby_candidates if h['id'] not in rejected_by]

                if not available:
                    # All nearby hospitals have been tried — cancel the request
                    cursor.execute("""
                        UPDATE patient_requests
                        SET status='cancelled', cancelled=1
                        WHERE request_id=%s
                    """, (request_id,))
                    conn.commit()
                    print(f'[CANCELLED] {request_id} — all nearby hospitals tried, no hospital available')
                    return

                next_h = available[0]

                cursor.execute('''
                    UPDATE patient_requests
                    SET hospital_id = %s,
                        rejected_by = %s,
                        status = 'pending',
                        assigned_driver_id = NULL,
                        assigned_driver = NULL,
                        reassignment_count = COALESCE(reassignment_count, 0) + 1,
                        forwarded_from_hospital_id = %s
                    WHERE request_id = %s
                ''', (next_h['id'], json.dumps(rejected_by), current_hosp_id, request_id))
                conn.commit()

                print(f'[AUTO-FORWARD] Forwarding {request_id} from {hospital_name} to next hospital')
                print(f'[AUTO-FORWARD] {request_id} ({reason}): hosp {current_hosp_id} → {next_h["name"]}')

                broadcast_to_hospital(next_h['id'], 'new_emergency', {
                    'request_id':   request_id,
                    'patient_name': req['patient_name'],
                    'patient_phone': req['patient_phone'],
                    'latitude':     float(req['latitude']),
                    'longitude':    float(req['longitude']),
                    'message':      f'Forwarded — previous hospital did not respond'
                })

            # ── Process CASE 1 ────────────────────────────────────────────
            for req in pending_stale:
                try:
                    forward_to_next_hospital(req, cursor, conn, reason='pending-timeout')
                except Exception as e:
                    print(f'[AUTO-FORWARD ERROR] {req["request_id"]}: {e}')
                    try: conn.rollback()
                    except: pass

            # ── Process CASE 2 ────────────────────────────────────────────
            for req in driver_stale:
                try:
                    request_id      = req['request_id']
                    current_hosp_id = req['hospital_id']

                    # Try another available driver at SAME hospital first
                    cursor.execute('''
                        SELECT d.id, d.name, d.username, d.assigned_ambulance
                        FROM drivers d
                        WHERE d.hospital_id = %s
                          AND d.status = 'Available'
                          AND d.assigned_ambulance IS NOT NULL
                          AND d.id != %s
                        LIMIT 1
                    ''', (current_hosp_id, req.get('assigned_driver_id') or 0))
                    alt_driver = cursor.fetchone()

                    if alt_driver:
                        # Reassign to another driver at same hospital
                        cursor.execute('''
                            UPDATE patient_requests
                            SET assigned_driver_id = %s,
                                assigned_driver = %s,
                                status = 'accepted',
                                reassignment_count = COALESCE(reassignment_count, 0) + 1
                            WHERE request_id = %s
                        ''', (alt_driver['id'], alt_driver['username'], request_id))
                        conn.commit()

                        print(f'[AUTO-REASSIGN] {request_id}: reassigned to driver {alt_driver["name"]} @ same hospital {current_hosp_id}')

                        broadcast_to_hospital(current_hosp_id, 'driver_reassigned', {
                            'request_id':  request_id,
                            'driver_name': alt_driver['name'],
                            'message':     f'Auto-reassigned to {alt_driver["name"]} (previous driver did not respond)'
                        })
                    else:
                        # No other driver at this hospital → forward to next hospital
                        forward_to_next_hospital(req, cursor, conn, reason='driver-no-response')

                except Exception as e:
                    print(f'[AUTO-FORWARD ERROR] {req["request_id"]}: {e}')
                    try: conn.rollback()
                    except: pass

            # ── AUTO-CLEANUP: run every 60 iterations (every 5 minutes) ──
            if _cleanup_counter % 60 == 0:
                try:
                    # RULE 1 — Auto-complete very old active trips (older than 3 hours)
                    cursor.execute("""
                        UPDATE patient_requests
                        SET status='completed'
                        WHERE status IN ('en_route', 'picked_up', 'assigned')
                        AND timestamp < DATE_SUB(NOW(), INTERVAL 3 HOUR)
                        AND (cancelled IS NULL OR cancelled = 0)
                    """)
                    completed_count = cursor.rowcount
                    if completed_count:
                        print(f'[AUTO-CLEANUP] Auto-completed {completed_count} stale active trip(s) (>3h old)')

                    # RULE 2 — Cancel pending requests older than 2 hours
                    cursor.execute("""
                        UPDATE patient_requests
                        SET status='cancelled', cancelled=1
                        WHERE status='pending'
                        AND timestamp < DATE_SUB(NOW(), INTERVAL 2 HOUR)
                        AND (cancelled IS NULL OR cancelled = 0)
                    """)
                    cancelled_count = cursor.rowcount
                    if cancelled_count:
                        print(f'[AUTO-CLEANUP] Auto-cancelled {cancelled_count} stale pending request(s) (>2h old)')

                    conn.commit()
                except Exception as e:
                    print(f'[AUTO-CLEANUP ERROR] {e}')
                    try: conn.rollback()
                    except: pass

            cursor.close()
            conn.close()

        except Exception as e:
            print(f'[AUTO-FORWARD THREAD ERROR] {e}')
            import traceback
            traceback.print_exc()

# ==================== SSE REAL-TIME ALERTS (HOSPITAL) ====================

@app.route('/hospital-sse-stream', methods=['GET'])
def hospital_sse_stream():
    """
    Server-Sent Events stream for hospital real-time alerts.
    Hospital dashboard connects here and receives instant notifications.
    
    Each client gets a unique queue for messages. When new emergencies arrive,
    we broadcast via this SSE connection (~100ms latency vs 15s polling).
    """
    if session.get('user_type') != 'hospital':
        return jsonify({'error': 'Unauthorized'}), 401
    
    hospital_id = session.get('hospital_id')
    if not hospital_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        from queue import Queue
        client_queue = Queue()
        
        # Register this client
        with _sse_lock:
            if hospital_id not in _sse_clients:
                _sse_clients[hospital_id] = []
            _sse_clients[hospital_id].append(client_queue)
        
        print(f'[SSE] Hospital {hospital_id} connected ({len(_sse_clients.get(hospital_id, []))} clients)')
        
        # Generator function for SSE stream
        def generate():
            heartbeat_count = 0
            try:
                while True:
                    try:
                        # Get message from queue with timeout
                        message = client_queue.get(timeout=30)
                        yield message
                    except:
                        # Send heartbeat every 30 seconds to keep connection alive
                        heartbeat_count += 1
                        yield f'id: heartbeat-{heartbeat_count}\ndata: ping\n\n'
            finally:
                # Unregister client on disconnect
                with _sse_lock:
                    if hospital_id in _sse_clients and client_queue in _sse_clients[hospital_id]:
                        _sse_clients[hospital_id].remove(client_queue)
                        print(f'[SSE] Hospital {hospital_id} disconnected ({len(_sse_clients.get(hospital_id, []))} clients remaining)')
        
        return Response(generate(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Nginx: don't buffer
        })
    
    except Exception as e:
        print(f'[SSE ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500

# ==================== MODIFY /DISPATCH TO BROADCAST EMERGENCIES ====================

def _broadcast_new_emergency(hospital_id, request_id, patient_data):
    """Helper to broadcast new emergency to hospital via SSE."""
    broadcast_to_hospital(hospital_id, 'new_emergency', {
        'request_id': request_id,
        'patient_name': patient_data.get('patient_name', 'Unknown'),
        'patient_phone': patient_data.get('patient_phone', ''),
        'latitude': patient_data.get('latitude'),
        'longitude': patient_data.get('longitude'),
        'status': 'new_request',
        'message': 'New emergency request arrived'
    })

# Start auto-forward background thread
def start_background_tasks():
    """Start background threads on app startup."""
    auto_forward_thread = threading.Thread(target=auto_forward_stale_requests, daemon=True)
    auto_forward_thread.start()
    print('[BACKGROUND] Auto-forward thread started');


if __name__ == '__main__':
    start_background_tasks()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
