"""
================================================
  SmartAmbulance - Automatic Database Setup
================================================
Run this script ONCE before starting the app.

Usage:
    python setup_db.py

What it does:
    1. Reads DB credentials from .env (falls back to defaults)
    2. Creates the 'smartambulance' database if it doesn't exist
    3. Creates all required tables
    4. Seeds demo hospitals, ambulances, drivers, users & admin
    5. Prints login credentials for every demo account

After running this script, start the app with:
    python app.py
"""

import sys
import os

# ── Load .env before anything else ────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[ENV] Loaded .env file")
except ImportError:
    print("[ENV] python-dotenv not installed — run: pip install python-dotenv")
    sys.exit(1)

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("[ERROR] mysql-connector-python not installed — run: pip install mysql-connector-python")
    sys.exit(1)

# ── Credentials (from .env, with sensible defaults) ───────────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_PORT     = int(os.environ.get("DB_PORT", "3306"))
DB_USER     = os.environ.get("DB_USER",     "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME",     "smartambulance")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — Create database
# ══════════════════════════════════════════════════════════════════════════════
def create_database(cursor):
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{DB_NAME}`")
    print(f"[DB] Database '{DB_NAME}' ready")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — Create all tables
# ══════════════════════════════════════════════════════════════════════════════
def create_tables(cursor, conn):
    # ── hospitals ──────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id                     INT AUTO_INCREMENT PRIMARY KEY,
            username               VARCHAR(50)  UNIQUE NOT NULL,
            password               VARCHAR(255) NOT NULL,
            name                   VARCHAR(100) NOT NULL,
            address                VARCHAR(255),
            phone                  VARCHAR(20),
            email                  VARCHAR(100),
            total_beds             INT          DEFAULT 150,
            available_beds         INT          DEFAULT 150,
            latitude               DECIMAL(10,8),
            longitude              DECIMAL(11,8),
            specialties            JSON,
            website                VARCHAR(100),
            performance_score      INT          DEFAULT 75,
            whatsapp               VARCHAR(20),
            hospital_type          VARCHAR(50)  DEFAULT 'Private',
            gps_latitude           DECIMAL(10,8),
            gps_longitude          DECIMAL(11,8),
            general_beds           INT          DEFAULT 0,
            icu_beds               INT          DEFAULT 0,
            emergency_beds         INT          DEFAULT 0,
            doctors_count          INT          DEFAULT 0,
            nurses_count           INT          DEFAULT 0,
            operating_hours        JSON,
            cover_photo            VARCHAR(255),
            logo_photo             VARCHAR(255),
            registration_certificate VARCHAR(255),
            is_verified            BOOLEAN      DEFAULT FALSE,
            status                 ENUM('pending','approved','rejected') DEFAULT 'approved',
            rejection_reason       VARCHAR(255),
            registration_number    VARCHAR(100),
            contact_name           VARCHAR(100),
            is_locked              TINYINT(1)   NOT NULL DEFAULT 0,
            created_at             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[DB] ✓ hospitals table")

    # ── ambulances ─────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ambulances (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            ambulance_number VARCHAR(20)  UNIQUE NOT NULL,
            type             VARCHAR(50),
            status           VARCHAR(50)  DEFAULT 'Available',
            hospital_id      INT,
            equipment        JSON,
            last_service     DATE,
            created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
        )
    """)
    print("[DB] ✓ ambulances table")

    # ── drivers ────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            username            VARCHAR(20)  UNIQUE NOT NULL,
            password            VARCHAR(255) NOT NULL,
            name                VARCHAR(100) NOT NULL,
            phone               VARCHAR(20),
            cnic                VARCHAR(20),
            experience          INT,
            shift               VARCHAR(50),
            assigned_ambulance  VARCHAR(20),
            status              VARCHAR(50)  DEFAULT 'Available',
            hospital_id         INT,
            hospital_username   VARCHAR(50),
            certifications      JSON,
            license             VARCHAR(50),
            profile_pic         VARCHAR(255),
            last_rejected_at    TIMESTAMP    NULL DEFAULT NULL,
            current_latitude    DECIMAL(10,8) NULL,
            current_longitude   DECIMAL(11,8) NULL,
            location_updated_at TIMESTAMP    NULL,
            created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
        )
    """)
    print("[DB] ✓ drivers table")

    # ── patient_requests ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_requests (
            id                       INT AUTO_INCREMENT PRIMARY KEY,
            request_id               VARCHAR(20)  UNIQUE NOT NULL,
            patient_name             VARCHAR(100),
            patient_phone            VARCHAR(20),
            pickup_address           VARCHAR(255),
            hospital_id              INT,
            reason                   VARCHAR(255),
            priority                 VARCHAR(20),
            status                   VARCHAR(50)  DEFAULT 'pending',
            assigned_driver_id       INT,
            assigned_driver          VARCHAR(20),
            rejected_by              JSON,
            locked                   BOOLEAN      DEFAULT FALSE,
            locked_by                INT,
            locked_at                TIMESTAMP    NULL,
            cancelled                BOOLEAN      DEFAULT FALSE,
            reassignment_count       INT          DEFAULT 0,
            latitude                 DECIMAL(10,8),
            longitude                DECIMAL(11,8),
            age                      INT,
            symptoms                 TEXT,
            ip_address               VARCHAR(45)  NULL,
            auto_processed           BOOLEAN      DEFAULT FALSE,
            auto_processed_at        TIMESTAMP    NULL DEFAULT NULL,
            forwarded_from_hospital_id INT        NULL DEFAULT NULL,
            timestamp                TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id)        REFERENCES hospitals(id) ON DELETE SET NULL,
            FOREIGN KEY (assigned_driver_id) REFERENCES drivers(id)  ON DELETE SET NULL
        )
    """)
    print("[DB] ✓ patient_requests table")

    # ── dispatches ─────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispatches (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            dispatch_id  VARCHAR(30)  UNIQUE NOT NULL,
            request_id   VARCHAR(20),
            patient_name VARCHAR(100),
            patient_phone VARCHAR(20),
            location     VARCHAR(255),
            driver_id    INT,
            driver_name  VARCHAR(100),
            ambulance_id VARCHAR(20),
            hospital_id  INT,
            status       VARCHAR(50),
            priority     VARCHAR(20),
            timestamp    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id)   REFERENCES drivers(id)             ON DELETE SET NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)           ON DELETE SET NULL,
            FOREIGN KEY (ambulance_id) REFERENCES ambulances(ambulance_number) ON DELETE SET NULL
        )
    """)
    print("[DB] ✓ dispatches table")

    # ── status_timeline ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_timeline (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            request_id  VARCHAR(20)  NOT NULL,
            dispatch_id VARCHAR(30),
            old_status  VARCHAR(50),
            new_status  VARCHAR(50),
            action_by   VARCHAR(50),
            action_type VARCHAR(50),
            driver_id   INT,
            driver_name VARCHAR(100),
            notes       TEXT,
            timestamp   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES patient_requests(request_id) ON DELETE CASCADE,
            FOREIGN KEY (driver_id)  REFERENCES drivers(id) ON DELETE SET NULL
        )
    """)
    print("[DB] ✓ status_timeline table")

    # ── users (public patients) ────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                 INT AUTO_INCREMENT PRIMARY KEY,
            username           VARCHAR(50)  UNIQUE,
            password           VARCHAR(255),
            name               VARCHAR(100),
            email              VARCHAR(100),
            phone              VARCHAR(20)  UNIQUE,
            address            VARCHAR(255),
            blood_type         VARCHAR(10),
            medical_history    TEXT,
            emergency_contacts JSON,
            cnic               VARCHAR(20)  UNIQUE,
            full_name          VARCHAR(100),
            user_type          VARCHAR(50),
            created_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    print("[DB] ✓ users table")

    # ── admins ─────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(50)  UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[DB] ✓ admins table")

    # ── attendance_records ─────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            driver_id    INT          NOT NULL,
            date         DATE         NOT NULL,
            status       VARCHAR(50)  NOT NULL DEFAULT 'Present',
            admin_status VARCHAR(50)  NOT NULL DEFAULT 'pending',
            leave_reason TEXT,
            admin_id     INT,
            approved_at  TIMESTAMP    NULL,
            created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_attendance (driver_id, date),
            FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id)  REFERENCES users(id)   ON DELETE SET NULL
        )
    """)
    print("[DB] ✓ attendance_records table")

    # ── feedback ───────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            request_id     VARCHAR(50),
            patient_name   VARCHAR(100),
            patient_phone  VARCHAR(20),
            on_time        ENUM('yes','no'),
            rating         INT CHECK (rating >= 1 AND rating <= 5),
            driver_rating  INT CHECK (driver_rating >= 1 AND driver_rating <= 5),
            comment        LONGTEXT,
            created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES patient_requests(request_id) ON DELETE SET NULL,
            INDEX idx_request_id (request_id),
            INDEX idx_created_at (created_at)
        )
    """)
    print("[DB] ✓ feedback table")

    # ── blacklist ──────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            phone      VARCHAR(20)  UNIQUE NOT NULL,
            reason     VARCHAR(255),
            blocked_by VARCHAR(50),
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[DB] ✓ blacklist table")

    # ── system_settings ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            setting_key   VARCHAR(50)  UNIQUE,
            setting_value VARCHAR(255),
            updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT IGNORE INTO system_settings (setting_key, setting_value) VALUES
            ('emergency_timeout', '10'),
            ('max_distance', '50')
    """)
    print("[DB] ✓ system_settings table")

    conn.commit()
    print("[DB] All tables created successfully.\n")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Seed demo data
# ══════════════════════════════════════════════════════════════════════════════
def seed_data(cursor, conn):
    # ── Guard: skip if already seeded ─────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    if cursor.fetchone()[0] > 0:
        print("[DB] Demo data already present — skipping seed.\n")
        return

    print("[DB] Seeding demo data...")

    # ── Hospitals ──────────────────────────────────────────────────────────────
    hospitals = [
        (
            "hospital1", "pass123",
            "City General Hospital",
            "123 GT Road, Gujrat, Punjab, Pakistan",
            "+92-53-1234567", "emergency@citygen.pk",
            150, 120,
            32.5741, 74.0789,
            '["Emergency Medicine","Trauma Care","Cardiology"]',
            "www.citygenhospital.pk"
        ),
        (
            "hospital2", "pass123",
            "Metro Medical Center",
            "456 Jinnah Road, Gujrat, Punjab, Pakistan",
            "+92-53-9876543", "emergency@metromedical.pk",
            200, 175,
            32.5613, 74.0721,
            '["General Medicine","Orthopedics","Pediatrics"]',
            "www.metromedical.pk"
        ),
    ]

    hospital_ids = {}
    for h in hospitals:
        cursor.execute("""
            INSERT INTO hospitals
                (username, password, name, address, phone, email,
                 total_beds, available_beds, latitude, longitude, specialties, website)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, h)
        hospital_ids[h[0]] = cursor.lastrowid
    conn.commit()
    print(f"[DB]   ✓ {len(hospitals)} hospitals")

    # ── Ambulances ─────────────────────────────────────────────────────────────
    ambulances = [
        ("SA-001", "Advanced Life Support", "Available", hospital_ids["hospital1"],
         '["Defibrillator","Oxygen Tank","Emergency Stretcher"]'),
        ("SA-002", "Advanced Life Support", "Available", hospital_ids["hospital1"],
         '["Defibrillator","Oxygen Tank","Emergency Stretcher"]'),
        ("SA-003", "Basic Life Support",    "Available", hospital_ids["hospital2"],
         '["Oxygen Tank","Emergency Stretcher","First Aid Kit"]'),
        ("SA-004", "Advanced Life Support", "Available", hospital_ids["hospital2"],
         '["Defibrillator","Oxygen Tank","Emergency Stretcher","Portable Monitor"]'),
    ]

    for amb in ambulances:
        cursor.execute("""
            INSERT INTO ambulances (ambulance_number, type, status, hospital_id, equipment)
            VALUES (%s,%s,%s,%s,%s)
        """, amb)
    conn.commit()
    print(f"[DB]   ✓ {len(ambulances)} ambulances")

    # ── Drivers ────────────────────────────────────────────────────────────────
    drivers = [
        ("DRV-001", "pass123", "Ahmed Al-Mansouri", "+92-301-1234567",
         "12345-1234567-1", 8, "Morning", "SA-001", "Available",
         hospital_ids["hospital1"], "hospital1",
         '["EMT-P","BLS","ACLS","PALS"]', "DRV-LIC-2026-001"),
        ("DRV-002", "pass123", "Fatima Al-Zaabi", "+92-301-9876543",
         "98765-7654321-9", 5, "Night", "SA-002", "Available",
         hospital_ids["hospital1"], "hospital1",
         '["EMT-P","BLS","ACLS"]', "DRV-LIC-2026-002"),
        ("DRV-003", "pass123", "Mohammed Al-Ketbi", "+92-301-5555555",
         "55555-5555555-5", 3, "Morning", "SA-003", "Available",
         hospital_ids["hospital2"], "hospital2",
         '["EMT-B","BLS","First Aid"]', "DRV-LIC-2026-003"),
        ("DRV-004", "pass123", "Sara Johnson", "+92-301-7777777",
         "77777-7777777-7", 6, "Night", "SA-004", "Available",
         hospital_ids["hospital2"], "hospital2",
         '["EMT-P","BLS","ACLS","PALS"]', "DRV-LIC-2026-004"),
    ]

    for drv in drivers:
        cursor.execute("""
            INSERT INTO drivers
                (username, password, name, phone, cnic, experience, shift,
                 assigned_ambulance, status, hospital_id, hospital_username,
                 certifications, license)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, drv)
    conn.commit()
    print(f"[DB]   ✓ {len(drivers)} drivers")

    # ── Public users ───────────────────────────────────────────────────────────
    users = [
        ("user1", "pass123", "Ahmed Hassan",
         "ahmed@gmail.com", "+92-301-1111111",
         "Gujrat, Punjab", "O+", "Type 2 Diabetes", "[]"),
        ("user2", "pass123", "Sarah Johnson",
         "sarah@gmail.com", "+92-301-3333333",
         "Rawalpindi, Punjab", "A+", "Hypertension", "[]"),
    ]

    for usr in users:
        cursor.execute("""
            INSERT INTO users
                (username, password, name, email, phone,
                 address, blood_type, medical_history, emergency_contacts)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, usr)
    conn.commit()
    print(f"[DB]   ✓ {len(users)} public users")

    # ── Admin account ──────────────────────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES ('admin', 'admin123')"
        )
        conn.commit()
        print("[DB]   ✓ Default admin account (admin / admin123)")

    print("[DB] Seeding complete.\n")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    banner = "=" * 58
    print(banner)
    print("  SmartAmbulance — Automatic Database Setup")
    print(banner)
    print(f"  Host     : {DB_HOST}:{DB_PORT}")
    print(f"  User     : {DB_USER}")
    print(f"  Database : {DB_NAME}")
    print(banner + "\n")

    # ── Connect to MySQL (no database selected yet) ────────────────────────────
    try:
        print("[DB] Connecting to MySQL server...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connection_timeout=10,
        )
        cursor = conn.cursor()
        print("[DB] Connected successfully.\n")
    except Error as e:
        print(f"\n[ERROR] Cannot connect to MySQL: {e}")
        print("\nTroubleshooting checklist:")
        print("  1. Is MySQL / XAMPP running?")
        print("  2. Are the credentials in .env correct?")
        print(f"     DB_HOST={DB_HOST}, DB_USER={DB_USER}, DB_PORT={DB_PORT}")
        print("  3. Copy .env.example to .env and fill in your values.\n")
        sys.exit(1)

    # ── Run setup steps ────────────────────────────────────────────────────────
    try:
        create_database(cursor)
        create_tables(cursor, conn)
        seed_data(cursor, conn)
    except Error as e:
        print(f"\n[ERROR] Setup failed: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.close()
    conn.close()

    # ── Success summary ────────────────────────────────────────────────────────
    print(banner)
    print("  Setup Complete!")
    print(banner)
    print("\n  Demo Login Credentials")
    print("  " + "-" * 40)
    print("  Hospitals")
    print("    hospital1 / pass123   (City General Hospital)")
    print("    hospital2 / pass123   (Metro Medical Center)")
    print("  Drivers")
    print("    DRV-001 to DRV-004 / pass123")
    print("  Public Users")
    print("    user1 / pass123")
    print("    user2 / pass123")
    print("  Admin Panel")
    print("    admin / admin123")
    print("\n  Next step:")
    print("    python app.py")
    print(f"    Open: http://localhost:5000\n")


if __name__ == "__main__":
    main()
