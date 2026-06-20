"""
Setup script to add hospital bed tracking data to MySQL database
Inserts realistic Pakistani hospital bed counts
"""

import mysql.connector
from mysql.connector import Error

# Database configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'smartambulance'
DB_PORT = 3306

def add_hospital_beds_tracking():
    """Add/update hospital bed availability data"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # First, verify the columns exist
        print('[DB] Verifying bed availability columns...')
        try:
            cursor.execute('''
                ALTER TABLE hospitals ADD COLUMN total_beds INT DEFAULT 50
            ''')
            print('[DB] Added total_beds column')
        except Error:
            print('[DB] total_beds column already exists')
        
        try:
            cursor.execute('''
                ALTER TABLE hospitals ADD COLUMN available_beds INT DEFAULT 30
            ''')
            print('[DB] Added available_beds column')
        except Error:
            print('[DB] available_beds column already exists')
        
        conn.commit()
        
        # Check if hospitals exist
        cursor.execute('SELECT COUNT(*) FROM hospitals')
        hospital_count = cursor.fetchone()[0]
        
        if hospital_count == 0:
            print('[DB] No hospitals found, inserting Pakistani hospital data...')
            
            hospitals = [
                ('hospital_gujrat', 'password123', 'DHQ Hospital Gujrat', 
                 'Gujrat, Punjab, Pakistan', '+92-541-3220000', 'info@dhqgujrat.pk', 
                 120, 45, 32.1814, 74.0809, '["Emergency", "Surgery", "Cardiology"]', 'www.dhqgujrat.pk'),
                
                ('cmh_gujrat', 'password123', 'CMH Gujrat', 
                 'Cantonment Road, Gujrat, Punjab', '+92-541-2620000', 'info@cmhgujrat.pk', 
                 80, 60, 32.1750, 74.0850, '["Military Hospital", "Emergency", "General"]', 'www.cmhgujrat.pk'),
                
                ('al_shifa', 'password123', 'Al-Shifa Hospital', 
                 'Main Bazaar, Gujrat', '+92-541-5666000', 'info@alshifa.pk', 
                 40, 12, 32.1900, 74.0900, '["Emergency", "Pediatrics", "Maternity"]', 'www.alshifa.pk'),
                
                ('gondal_hospital', 'password123', 'Gondal Hospital', 
                 'Gondal Village, Gujrat', '+92-541-9990000', 'info@gondal.pk', 
                 30, 25, 32.2000, 74.1000, '["Emergency", "General"]', 'www.gondal.pk'),
            ]
            
            for hospital in hospitals:
                cursor.execute('''
                    INSERT INTO hospitals 
                    (username, password, name, address, phone, email, total_beds, available_beds, 
                     latitude, longitude, specialties, website)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', hospital)
                print(f'[DB] Inserted: {hospital[2]} (Total: {hospital[6]}, Available: {hospital[7]})')
            
            conn.commit()
            print('[DB] Hospital data insertion completed')
        
        else:
            print(f'[DB] Found {hospital_count} existing hospitals. Updating bed counts...')
            
            # Update existing hospitals with new bed counts
            updates = [
                (120, 45, 'DHQ Hospital Gujrat'),
                (80, 60, 'CMH Gujrat'),
                (40, 12, 'Al-Shifa Hospital'),
                (30, 25, 'Gondal Hospital'),
            ]
            
            for total_beds, available_beds, name in updates:
                cursor.execute('''
                    UPDATE hospitals 
                    SET total_beds = %s, available_beds = %s 
                    WHERE name = %s
                ''', (total_beds, available_beds, name))
                print(f'[DB] Updated: {name} (Total: {total_beds}, Available: {available_beds})')
            
            conn.commit()
            print('[DB] Hospital bed counts updated')
        
        # Show the complete updated schema
        print('\n' + '='*80)
        print('COMPLETE UPDATED HOSPITALS TABLE SCHEMA')
        print('='*80 + '\n')
        
        cursor.execute('DESCRIBE hospitals')
        schema = cursor.fetchall()
        
        print(f"{'Field':<25} {'Type':<30} {'Null':<6} {'Key':<6} {'Default':<15}")
        print('-' * 82)
        for field in schema:
            print(f"{field[0]:<25} {field[1]:<30} {str(field[2]):<6} {str(field[3] or ''):<6} {str(field[5] or ''):<15}")
        
        print('\n' + '='*80)
        print('HOSPITAL DATA WITH BED AVAILABILITY')
        print('='*80 + '\n')
        
        cursor.execute('''
            SELECT id, name, total_beds, available_beds 
            FROM hospitals 
            ORDER BY id
        ''')
        
        hospitals_list = cursor.fetchall()
        print(f"{'ID':<5} {'Hospital Name':<30} {'Total Beds':<15} {'Available Beds':<15}")
        print('-' * 65)
        for hospital in hospitals_list:
            print(f"{hospital[0]:<5} {hospital[1]:<30} {hospital[2]:<15} {hospital[3]:<15}")
        
        cursor.close()
        conn.close()
        
        print('\n[SUCCESS] Hospital bed tracking setup completed!')
        return True
        
    except Error as e:
        print(f'[ERROR] Database operation failed: {e}')
        return False

if __name__ == '__main__':
    add_hospital_beds_tracking()
