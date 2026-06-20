# SmartAmbulance - Database Configuration

## Current Configuration

The application is configured to use the following database settings:

```
Host:     localhost
User:     root
Password: (empty)
Database: smartambulance
```

## How to Change Configuration

### Edit Database Credentials

Open `app.py` and find these lines (around line 35-38):

```python
# ==================== DATABASE CONFIGURATION ====================
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''  # Set to empty string if no password is configured, or set your MySQL root password
DB_NAME = 'smartambulance'
```

### If MySQL Root Has a Password

If your MySQL 'root' user has a password:

1. Open `app.py`
2. Edit line 37: Change `DB_PASSWORD = ''` to `DB_PASSWORD = 'your_password'`
3. Save the file
4. Restart Flask: `python app.py`

Example:
```python
DB_PASSWORD = 'MySecurePassword123'
```

### If MySQL is on a Different Host

If MySQL is running on a different machine (not localhost):

1. Open `app.py`
2. Edit line 35: Change `DB_HOST = 'localhost'` to `DB_HOST = '192.168.1.100'` (or your server IP)
3. Save the file
4. Restart Flask: `python app.py`

Example:
```python
DB_HOST = '192.168.1.100'
```

### If Using a Different Database User

If you want to use a different MySQL user account:

1. Open `app.py`
2. Edit line 36: Change `DB_USER = 'root'` to `DB_USER = 'smartambulance_user'`
3. Edit line 37: Set the corresponding password
4. Save the file
5. Restart Flask: `python app.py`

Example:
```python
DB_USER = 'smartambulance_user'
DB_PASSWORD = 'user_password_here'
```

### If Using a Different Database Name

If you want to use a different database name:

1. Open `app.py`
2. Edit line 38: Change `DB_NAME = 'smartambulance'` to `DB_NAME = 'my_database_name'`
3. Save the file
4. Restart Flask: `python app.py`

Note: The database will be created automatically if it doesn't exist.

Example:
```python
DB_NAME = 'ambulance_system_prod'
```

## Testing Configuration

After making changes, verify the configuration works:

```bash
python test_mysql.py
```

This will test:
1. MySQL server connection
2. Database creation
3. Table creation
4. Data persistence

## Configuration Templates

### Development (Default)
```python
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'smartambulance'
```

### Development with Password
```python
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'dev_password'
DB_NAME = 'smartambulance'
```

### Production (Remote Server)
```python
DB_HOST = 'prod.db.server.com'
DB_USER = 'smartambulance_prod'
DB_PASSWORD = 'strong_production_password_here'
DB_NAME = 'smartambulance_production'
```

### Testing (Separate Database)
```python
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'smartambulance_test'
```

## Verifying MySQL is Running

### Windows
```bash
# Check if MySQL service is running
sc query MySQL80

# Or via Services.msc - Look for MySQL80 (should be Running)
```

### macOS
```bash
# Check if MySQL is running
brew services list

# Start MySQL if not running
brew services start mysql
```

### Linux
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Start MySQL if not running
sudo systemctl start mysql
```

## Finding MySQL Credentials

### Windows
1. Open MySQL Command Line Client
2. Enter password if prompted
3. If successful, MySQL is running with that password

### macOS
```bash
# MySQL installed via Homebrew usually has no password
mysql -u root

# If you set a password, use:
mysql -u root -p
```

### Linux
```bash
# Check MySQL installation directory
which mysql

# Connect to verify credentials
mysql -u root -p
```

## Common Issues

### Issue: "Access denied for user 'root'@'localhost'"
- MySQL root password is not empty
- Update `DB_PASSWORD` to your password
- Or reset MySQL root password (see MySQL docs)

### Issue: "Can't connect to MySQL server on 'localhost:3306'"
- MySQL server is not running
- Start MySQL service as shown above
- Or MySQL is not installed (install from mysql.com)

### Issue: "Unknown database 'smartambulance'"
- This is OK! Flask will create it automatically
- If not created, run: `python db_setup.py`

### Issue: "Lost connection to MySQL server"
- Network connection interrupted
- Verify MySQL server is still running
- Check database connection settings

## After Configuration Changes

1. Save your changes to `app.py`
2. Stop Flask (Ctrl+C if running)
3. Test connection: `python test_mysql.py`
4. Start Flask: `python app.py`
5. Verify login still works with demo credentials

## Reset Database to Factory Settings

To delete all data and reset to demo state:

1. Stop Flask (Ctrl+C)
2. Run: `python db_setup.py`
3. This will reset with fresh demo data
4. Start Flask: `python app.py`

## Multiple Instances

To run multiple instances with different databases:

1. Copy `app.py` to `app_instance2.py`
2. Edit database configuration in `app_instance2.py`
3. Change `DB_NAME` to different value
4. Change Flask port in `if __name__ == '__main__'`: `port=5001`
5. Run: `python app.py` and `python app_instance2.py`

## Security Best Practices

1. **Never commit passwords to version control**
2. **Use environment variables for production**
3. **Enable MySQL user permission restrictions**
4. **Use strong passwords (16+ characters)**
5. **Enable SSL connections to MySQL**
6. **Regular database backups**
7. **Monitor database access logs**

### Using Environment Variables (Recommended)

Edit app.py:
```python
import os

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'smartambulance')
```

Then set environment variables:
```bash
# Linux/Mac
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=
export DB_NAME=smartambulance
python app.py

# Windows
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=
set DB_NAME=smartambulance
python app.py
```

## Need Help?

1. Check MYSQL_INTEGRATION.md for complete guide
2. Check INTEGRATION_SUMMARY.md for overview
3. Run `python test_mysql.py` to diagnose issues
4. Review Flask console output for error messages
5. Check MySQL logs for database errors

## Quick Reference

| Setting | Location | Default | Example |
|---------|----------|---------|---------|
| Host | app.py L35 | localhost | 192.168.1.100 |
| User | app.py L36 | root | smartambulance_user |
| Password | app.py L37 | (empty) | MyPassword123 |
| Database | app.py L38 | smartambulance | ambulance_prod |

---

Last Updated: March 7, 2026  
Configuration Version: 1.0
