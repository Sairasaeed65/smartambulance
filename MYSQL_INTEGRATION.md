# 🗄️ MySQL Database Integration - SmartAmbulance

## Overview

The SmartAmbulance Flask application has been **fully integrated with MySQL database** for persistent data storage. All in-memory Python dictionaries have been replaced with MySQL queries.

## 📋 What Changed

### Removed (Dictionary-based)
- ❌ DRIVERS dictionary
- ❌ HOSPITALS dictionary  
- ❌ AMBULANCES dictionary
- ❌ PATIENT_REQUESTS dictionary
- ❌ DISPATCHES dictionary
- ❌ USERS dictionary

### Added (Database-based)
- ✅ MySQL database: `smartambulance`
- ✅ 7 tables: hospitals, ambulances, drivers, patient_requests, dispatches, users, patient_users
- ✅ Automatic database initialization on first startup
- ✅ Demo data seeding with hospitals, drivers, ambulances, and users
- ✅ All routes now use MySQL queries instead of in-memory dicts

## 🚀 Quick Start

### Prerequisites
1. **MySQL Server** installed and running (any version 5.7+)
2. **Python 3.8+** with Flask and mysql-connector-python

### Installation

```bash
# 1. Install required packages (already done)
pip install flask
pip install mysql-connector-python

# 2. Verify MySQL is running
mysql --version
mysql -u root -p -e "SELECT 1"

# 3. Navigate to project directory
cd "c:\Users\zohai\OneDrive\Desktop\smart ambulance"

# 4. Run the Flask application
python app.py
```

When Flask starts, it will **automatically**:
1. ✓ Create the database `smartambulance`
2. ✓ Create all required tables
3. ✓ Seed demo data (hospitals, drivers, ambulances, users)
4. ✓ Print initialization status to console

### Access the Application

```
http://localhost:5000
```

## 🔐 Demo Login Credentials

After startup, use these credentials to test the system:

### Hospital Logins
```
Hospital 1:
  Username: hospital1
  Password: pass123
  Name: City General Hospital
  
Hospital 2:
  Username: hospital2
  Password: pass123
  Name: Metro Medical Center
```

### Driver Logins
```
DRV-001: Ahmed Al-Mansouri (pass123)
DRV-002: Fatima Al-Zaabi (pass123)
DRV-003: Mohammed Al-Ketbi (pass123)
DRV-004: Sara Johnson (pass123)
```

### User Logins
```
user1: Ahmed Hassan (pass123)
user2: Sarah Johnson (pass123)
```

## 🗄️ Database Schema

### hospitals table
```sql
id (PK), username (UNIQUE), password, name, address, phone, email,
total_beds, available_beds, latitude, longitude, specialties (JSON),
website, created_at
```

### ambulances table
```sql
id (PK), ambulance_number (UNIQUE), type, status, hospital_id (FK),
equipment (JSON), last_service, created_at
```

### drivers table
```sql
id (PK), username (UNIQUE), password, name, phone, cnic, experience,
shift, assigned_ambulance (FK), status, hospital_id (FK),
certifications (JSON), license, created_at
```

### patient_requests table
```sql
id (PK), request_id (UNIQUE), patient_name, patient_phone,
pickup_address, hospital_id (FK), reason, priority, status,
assigned_driver_id (FK), rejected_by (JSON), locked, locked_by,
locked_at, cancelled, reassignment_count, latitude, longitude,
age, symptoms, timestamp
```

### dispatches table  
```sql
id (PK), dispatch_id (UNIQUE), request_id, patient_name,
patient_phone, location, driver_id (FK), driver_name,
ambulance_id (FK), hospital_id (FK), status, priority,
timestamp, updated_at
```

### users table
```sql
id (PK), username (UNIQUE), password, name, email, phone,
address, blood_type, medical_history, emergency_contacts (JSON),
created_at
```

## ⚙️ Database Configuration

Edit `app.py` to change MySQL connection details:

```python
# Database Configuration (lines 15-19)
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'root'  # Change if different
DB_NAME = 'smartambulance'
```

### If Using Different MySQL Credentials:
1. Open `app.py`
2. Find lines 15-19 (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
3. Update the values to match your MySQL setup
4. Save and restart Flask

## 📝 Manual Database Setup (Optional)

If you need to reset the database or set it up manually:

```bash
# Run the standalone setup script
python db_setup.py
```

This will:
- Create the database if it doesn't exist
- Create all tables
- Seed demo data
- Print status messages

## 🔄 Data Flow Changes

### Before (Dictionary-based)
```
POST /driver-login 
  → Check DRIVERS['username']
  → In-memory lookup
  → Data lost on restart
```

### After (Database-based)
```
POST /driver-login
  → Query: SELECT * FROM drivers WHERE username = ?
  → MySQL lookup
  → Data persists forever
```

## ✨ Features

### Automatic Database Initialization
- First time you start Flask, it creates the database automatically
- No manual SQL commands needed
- Demo data automatically seeded

### Persistent Data Storage
- All data now persists in MySQL
- Survives Flask restarts
- Centralized data management

### Transaction Support
- Multi-step operations are atomic
- Request locking uses database transactions
- ACID compliance for data integrity

### Foreign Keys
- Hospital → Ambulances (1-to-many)
- Hospital → Drivers (1-to-many)
- Driver → Patient Requests (1-to-many)
- Cascade delete for referential integrity

## 🔍 Verification

After starting Flask, verify everything worked:

```bash
# Check database was created
mysql -u root -p -e "SHOW DATABASES;" | grep smartambulance

# Check tables were created
mysql -u root -p smartambulance -e "SHOW TABLES;"

# Check demo data was seeded
mysql -u root -p smartambulance -e "SELECT COUNT(*) as hospitals FROM hospitals;"
mysql -u root -p smartambulance -e "SELECT COUNT(*) as drivers FROM drivers;"
```

## 🐛 Troubleshooting

### "Access denied for user 'root'@'localhost'"
- MySQL username/password is incorrect
- Update DB_USER and DB_PASSWORD in app.py (lines 16-17)

### "Can't connect to MySQL server"
- MySQL server is not running
- On Windows: Check Services (mysql80 should be running)
- On Mac: `brew services start mysql`
- On Linux: `sudo systemctl start mysql`

### "Database 'smartambulance' already exists"
- This is normal on restart, database is reused
- Data persists across sessions

### "Syntax error in SQL statement"
- May indicate MySQL version incompatibility
- Ensure MySQL 5.7 or higher

## 📂 File Structure

```
smart ambulance/
├── app.py                 ← Main Flask app (MySQL version)
├── app_backup_dict.py     ← Old dictionary-based version (backup)
├── db_setup.py            ← Standalone database setup script
├── MYSQL_INTEGRATION.md   ← This file
├── templates/             ← HTML templates (unchanged)
├── static/                ← CSS/JS files (unchanged)
└── __pycache__/           ← Python cache
```

## 🔐 Security Notes

### Current Setup (Development)
- Passwords stored in **plain text** (not recommended for production)
- Default MySQL user 'root' with no password
- Suitable for FYP/Development only

### Production Recommendations
1. Hash passwords using bcrypt or werkzeug.security
2. Use strong MySQL passwords
3. Restrict database permissions
4. Use prepared statements (already implemented)
5. Enable SSL for MySQL connections
6. Regular database backups

## 📊 Performance Notes

### Query Optimization
- All queries use indexed fields (PK, FK, UNIQUE)
- Foreign key relationships properly defined
- Database handles concurrency atomically

### Connection Pooling (Future)
- Can add connection pooling for high traffic
- Currently creates new connection per request
- Sufficient for FYP scope

## 🔄 Migration Path

### Rolling Back to Dictionary Version
If you need to revert to the old in-memory version:

```bash
# Restore backup
mv app.py app_mysql.py
mv app_backup_dict.py app.py
python app.py
```

## 📚 Additional Resources

- [MySQL Connector Python Docs](https://dev.mysql.com/doc/connector-python/en/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [MySQL Database Design](https://dev.mysql.com/doc/)

## ✅ Verification Checklist

After setup, verify:
- [ ] Flask starts without errors
- [ ] `smartambulance` database exists
- [ ] All 6 tables created
- [ ] Demo data populated (hospitals, drivers, users)
- [ ] Hospital login works (hospital1/pass123)
- [ ] Driver login works (DRV-001/pass123)
- [ ] Data persists after Flask restart
- [ ] API endpoints return data from database

## 📞 Support

For issues:

1. Check Flask console output for SQL errors
2. Verify MySQL connection: `mysql -u root -p -e "SELECT 1"`
3. Check database existence: `mysql -u root -p -e "USE smartambulance; SHOW TABLES;"`
4. Review app.py lines 1-25 for connection settings
5. Run `db_setup.py` to reset database if corrupted

---
**MySQL Integration Completed** ✓  
All data is now persistent in MySQL database!  
All in-memory dictionaries have been replaced with database queries.
