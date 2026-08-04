import os
import sys
from dotenv import load_dotenv

# Ensure stdout handles UTF-8 on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def check_db():
    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "sql@000")
    db_name = os.environ.get("DB_NAME", "event_db2")
    port = int(os.environ.get("DB_PORT", 3306))

    print("=========================================")
    print("      DATABASE CONNECTION CHECK          ")
    print("=========================================")
    print(f"Host     : {host}")
    print(f"Port     : {port}")
    print(f"User     : {user}")
    print(f"Database : {db_name}")
    print("-----------------------------------------")

    # Step 1: Connect to MySQL Server
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        print("[OK] Connected to MySQL server successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MySQL server: {e}")
        return False

    cursor = conn.cursor()

    # Step 2: Check Server Version
    try:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"[OK] MySQL Version: {version}")
    except Exception as e:
        print(f"[WARN] Could not get server version: {e}")

    # Step 3: Check if target database exists
    try:
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        if cursor.fetchone():
            print(f"[OK] Database '{db_name}' exists.")
        else:
            print(f"[WARN] Database '{db_name}' DOES NOT exist.")
            print(f"Attempting to create database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            print(f"[OK] Database '{db_name}' created.")
    except Exception as e:
        print(f"[ERROR] Error checking/creating database '{db_name}': {e}")
        cursor.close()
        conn.close()
        return False

    cursor.close()
    conn.close()

    # Step 4: Connect to specific database
    try:
        db_conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name,
            port=port
        )
        print(f"[OK] Successfully connected to database '{db_name}'.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database '{db_name}': {e}")
        return False

    db_cursor = db_conn.cursor()

    # Step 5: Check tables
    try:
        db_cursor.execute("SHOW TABLES")
        tables = [table[0] for table in db_cursor.fetchall()]
        print(f"[OK] Tables found ({len(tables)}): {', '.join(tables) if tables else 'None'}")
        
        expected_tables = ['users', 'categories', 'events', 'event_gallery', 'bookings', 'wishlist', 'notifications']
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            print(f"[WARN] Missing expected tables: {', '.join(missing_tables)}")
            print("       You may want to initialize the database using schema.sql.")
        else:
            print("[OK] All expected tables are present in the schema.")
            
        # Count records in key tables
        if 'users' in tables:
            db_cursor.execute("SELECT COUNT(*) FROM users")
            user_count = db_cursor.fetchone()[0]
            print(f"  - Users count: {user_count}")
        if 'events' in tables:
            db_cursor.execute("SELECT COUNT(*) FROM events")
            event_count = db_cursor.fetchone()[0]
            print(f"  - Events count: {event_count}")

    except Exception as e:
        print(f"[WARN] Error querying tables: {e}")
    finally:
        db_cursor.close()
        db_conn.close()

    print("=========================================")
    print("STATUS: DATABASE CONNECTION IS HEALTHY!")
    print("=========================================")
    return True

if __name__ == "__main__":
    success = check_db()
    sys.exit(0 if success else 1)
