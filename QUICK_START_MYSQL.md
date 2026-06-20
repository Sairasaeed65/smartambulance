# ⚡ SmartAmbulance MySQL - Quick Start Guide

## 🚀 Start Here

### Step 1: Verify MySQL is Running (30 seconds)
```bash
python test_mysql.py
```

**Expected output:**
```
✓ Connected to MySQL 10.4.32
✓ Database smartambulance is ready
```

If you see an error, see **Troubleshooting** section below.

### Step 2: Start Flask Application (30 seconds)
```bash
python app.py
```

**Expected output:**
```
[DB] Creating database...
[DB] Seeded 2 hospitals
[DB] Seeded 4 drivers
[DB] Database initialized successfully
Running on http://127.0.0.1:5000
```

### Step 3: Open Browser (10 seconds)
```
http://localhost:5000
```

### Step 4: Login with Demo Credentials (1 minute)

**Hospital Admin Login:**
```
Username: hospital1
Password: pass123
```

**Driver Login:**
```
Username: DRV-001
Password: pass123
```

**Public User Login:**
```
Username: user1
Password: pass123
```

## 📋 Available Demo Accounts

### 🏥 Hospitals
| Username | Password | Hospital Name |
|----------|----------|---------------|
| hospital1 | pass123 | City General Hospital |
| hospital2 | pass123 | Metro Medical Center |

### 🚑 Drivers
| Username | Password | Name |
|----------|----------|------|
| DRV-001 | pass123 | Ahmed Al-Mansouri |
| DRV-002 | pass123 | Fatima Al-Zaabi |
| DRV-003 | pass123 | Mohammed Al-Ketbi |
| DRV-004 | pass123 | Sara Johnson |

### 👤 Users
| Username | Password | Name |
|----------|----------|------|
| user1 | pass123 | Ahmed Hassan |
| user2 | pass123 | Sarah Johnson |

## 🔄 Typical Workflow

### 1. Hospital Admin Dashboard
```
1. Login with hospital1 / pass123
2. View incoming patient requests
3. Accept or reject requests
4. Manage ambulances and drivers
5. Update available beds
6. View dispatch status
```

### 2. Driver Dashboard
```
1. Login with DRV-001 / pass123
2. View available patient requests
3. Accept a request
4. Update status: "On My Way" → "Patient Picked Up" → "Arrived at Hospital"
5. View trip history
5. Change password if needed
```

### 3. Public User
```
1. Login with user1 / pass123
2. Access user dashboard
3. View emergency history
4. Update profile information
```

### 4. Emergency Dispatch
```
1. Click "Emergency Help" on landing page
2. Grant location permission
3. Select hospital
4. System assigns nearest ambulance
5. Track ambulance in real-time
```

## 🔄 Database Features

✓ **Persistent Data**
- All data saved to MySQL database
- Data survives Flask app restart
- Multi-user concurrent access

✓ **Automatic Setup**
- Database created automatically
- Tables created automatically
- Demo data seeded automatically
- No manual SQL commands needed

✓ **Transaction Safety**
- Request locking is atomic
- Multi-step operations are consistent  
- No data corruption possible

✓ **Real-time Statistics**
- Hospital bed availability
- Driver status
- Active emergencies
- Dispatch history

## 🔧 Configuration

To use different MySQL credentials, edit `app.py` line 35-38:

```python
DB_HOST = 'localhost'       # MySQL server address
DB_USER = 'root'            # MySQL username
DB_PASSWORD = ''            # MySQL password (often empty)
DB_NAME = 'smartambulance'  # Database name
```

Then restart Flask.

See CONFIGURATION.md for detailed options.

## 🐛 Troubleshooting

### Problem: "Access denied for user 'root'@'localhost'"

**Solution**: MySQL has a password set.
1. Update `DB_PASSWORD` in app.py to your MySQL root password
2. Or reset MySQL root password

### Problem: "Can't connect to MySQL server on 'localhost'"

**Solution**: MySQL not running.
- Windows: Start MySQL80 service
- Mac: `brew services start mysql`
- Linux: `sudo systemctl start mysql`

### Problem: "Database already exists"

**Solution**: This is OK! It means:
- Database was created on first run
- Data will persist from previous sessions
- This is the intended behavior

### Problem: "Table already exists"

**Solution**: Also OK! Tables are created IF NOT EXISTS.
- Safe to restart Flask multiple times
- No data loss occurs

### Problem: Flask shows "Database initialization failed"

**Solution**: Check MySQL connection.
1. Verify MySQL is running
2. Verify DB_HOST, DB_USER, DB_PASSWORD are correct
3. Run `python test_mysql.py` to diagnose
4. Check MySQL permissions for your user

## 📊 Check Database Status

### Verify Tables Were Created
```bash
mysql -u root -e "USE smartambulance; SHOW TABLES;"
```

### Verify Demo Data Was Seeded
```bash
mysql -u root smartambulance -e "SELECT COUNT(*) as hospitals FROM hospitals;"
mysql -u root smartambulance -e "SELECT COUNT(*) as drivers FROM drivers;"
```

### View Hospital Information
```bash
mysql -u root smartambulance -e "SELECT username, name FROM hospitals;"
```

### View Driver Information
```bash
mysql -u root smartambulance -e "SELECT username, name FROM drivers;"
```

## 🔄 Resetting Database (Wipe & Start Fresh)

If you want to delete all user data and reset to demo state:

```bash
python db_setup.py
```

This will:
1. Delete all current data
2. Recreate tables
3. Reseed demo data

**Warning**: This is destructive! Use only on development.

## 📱 Testing the Application

### Test Hospital Workflow
```
1. Open http://localhost:5000/hospital-login
2. Login with hospital1/pass123
3. View incoming requests page
4. Add a new driver
5. Update available beds
6. View ambulances
```

### Test Driver Workflow
```
1. Open http://localhost:5000/driver-login
2. Login with DRV-001/pass123
3. View available requests
4. Request a patient pickup
5. Update delivery status
6. Change password
```

### Test Emergency System
```
1. Open http://localhost:5000
2. Click "Emergency Help"
3. Grant location permission (or use default)
4. Select a hospital
5. System creates dispatch
```

## 🔐 Security Notes

⚠️ **Current Status**: Development mode
- Passwords are stored in plain text (not secure)
- Demo credentials are known
- Suitable for FYP and testing only

✅ **For Production** (See MYSQL_INTEGRATION.md):
- Hash passwords with bcrypt
- Use strong credentials
- Enable SSL for MySQL
- Restrict database permissions
- Enable audit logging
- Regular backups

## 📝 File Structure

```
smart ambulance/
├── app.py                    ← Main Flask app (MySQL version)
├── app_backup_dict.py        ← Backup of original version
├── db_setup.py              ← Database setup script
├── test_mysql.py            ← MySQL connection test
├── templates/               ← HTML templates
├── static/                  ← CSS/JavaScript files
├── MYSQL_INTEGRATION.md     ← Comprehensive guide
├── CONFIGURATION.md         ← Configuration reference
├── COMPLETION_REPORT.md     ← Project completion summary
└── QUICK_START.md           ← This file
```

## 🎓 What's Different?

### Before (Dictionary Version)
```python
DRIVERS = {
    'driver1': {'name': 'Ahmed', ...}
}
# Data lost when Flask restarts
```

### After (MySQL Version)
```sql
SELECT * FROM drivers WHERE username = 'DRV-001'
-- Data persists in database forever
```

## 🚀 Next Steps

1. ✓ Verify MySQL connection: `python test_mysql.py`
2. ✓ Start Flask: `python app.py`
3. ✓ Test login with demo credentials
4. ✓ Review MYSQL_INTEGRATION.md for complete guide
5. ✓ Read CONFIGURATION.md if using different setup
6. ✓ Check COMPLETION_REPORT.md for full project details

## 💡 Tips & Tricks

### Running Multiple Instances
```bash
# Terminal 1
python app.py                           # Port 5000

# Terminal 2 - Edit app.py to change:
# - DB_NAME = 'smartambulance_test'
# - port=5001 in if __name__
python app.py                           # Port 5001
```

### Backup Database
```bash
mysqldump -u root smartambulance > backup.sql
```

### Restore Database
```bash
mysql -u root smartambulance < backup.sql
```

### Check Database Size
```bash
mysql -u root smartambulance -e "SELECT table_name, round(((data_length + index_length) / 1024 / 1024), 2) AS size_mb FROM information_schema.TABLES WHERE table_schema = 'smartambulance';"
```

### Monitor Active Connections
```bash
mysql -u root -e "SHOW PROCESSLIST;"
```

## 📞 Quick Help

| Issue | Solution |
|-------|----------|
| MySQL not connecting | Run `python test_mysql.py` |
| Database not created | Check MySQL is running and accepting connections |
| Demo data not seeding | Run `python db_setup.py` to manually seed |
| Wrong password error | Update DB_PASSWORD in app.py line 37 |
| Port 5000 already in use | Change `port=5001` in app.py last line |
| Want to reset data | Run `python db_setup.py` (destructive!) |

## 📚 Related Documentation

- **MYSQL_INTEGRATION.md** - Full integration guide (recommended reading)
- **CONFIGURATION.md** - Configuration options and security
- **COMPLETION_REPORT.md** - Complete project summary
- **README.md** - General project information

## ✨ Summary

You now have a **professional MySQL-backed emergency ambulance system** with:
- ✓ Persistent data storage
- ✓ Real-time multi-user support
- ✓ Fast performance with indexing
- ✓ Atomic transaction safety
- ✓ Easy configuration options
- ✓ Comprehensive documentation

**Ready to use!** 🚀

---

**Quick Start Guide v1.0**  
MySQL Integration Complete  
March 7, 2026
