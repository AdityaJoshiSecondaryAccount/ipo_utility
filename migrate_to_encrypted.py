
import os
import sys
import sqlite3
# Try to import pysqlcipher3 or sqlcipher3
try:
    from pysqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    try:
        import sqlcipher3 as sqlcipher
    except ImportError:
        print("Error: SQLCipher library (pysqlcipher3 or sqlcipher3) not found.")
        sys.exit(1)

def migrate_db(source_db, target_db, password):
    if not os.path.exists(source_db):
        print(f"Source database '{source_db}' not found.")
        return

    if os.path.exists(target_db):
        print(f"Target database '{target_db}' already exists. Please remove it first or use a different name.")
        # return # Optional: force overwrite? Better to warn.
        # For now, let's remove it to be safe if user re-runs?
        # os.remove(target_db)
        pass

    print(f"Migrating from {source_db} to {target_db}...")

    # Connect to the source database (standard sqlite3)
    conn_src = sqlite3.connect(source_db)
    
    # Connect to the target database (sqlcipher)
    conn_target = sqlcipher.connect(target_db)
    # Set the key immediately
    conn_target.execute(f"PRAGMA key = '{password}';")
    
    # We can use the backup API if compatible or copy via script
    # SQLCipher `backup` might fail if not unlocked, but we unlocked it.
    # However, copying from Plain -> Encrypted is often done via ATTACH or raw SQL dump.
    # ATTACH approach:
    # 1. Open Encrypted DB. 2. Attach Plain DB (KEY ''). 3. Copy.
    
    # Let's try the sqlcipher 'sqlcipher_export' function if available (commonly used).
    # Or just 'ATTACH DATABASE ...'
    
    # Strategy: Open encrypted DB (target). Attach plain DB (source).
    # Note: When using sqlcipher, attaching a standard DB generally works with empty key or just standard attach?
    # Actually, standard sqlite3 attached to sqlcipher works fine.
    
    try:
        # Using the sqlcipher connection to attach the plain database
        # We need to supply KEY for the attached database if it was encrypted, but it's not.
        # So we just attach it.
        
        # Absolute paths are safer
        abs_source = os.path.abspath(source_db)
        
        # ATTACH 'path/to/source.db' AS source_db KEY '';
        # KEY '' usually indicates plain text in some sqlcipher versions, or just omit KEY.
        conn_target.execute(f"ATTACH DATABASE '{abs_source}' AS source_db KEY '';")
        
        # Get list of tables
        cursor = conn_target.cursor()
        cursor.execute("SELECT name FROM source_db.sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table_name in tables:
            name = table_name[0]
            if name.startswith('sqlite_'):
                continue
            
            print(f"Copying table {name}...")
            
            # Step 1: Clear existing data in target table (from migrate)
            # This ensures we don't have conflicts, and we replace default data (like contenttypes)
            # with the IDs from the source DB to maintain FK integrity.
            conn_target.execute(f"DELETE FROM main.{name}")
            
            # Step 2: Insert data from source
            # We use explicit column names to be safe, or just SELECT * if schemas match 1:1.
            # Since migrations are identical, matching * should work and is robust for column order if consistent.
            # But let's check columns to be safe? 
            # Actually, "INSERT INTO main.X SELECT * FROM source_db.X" relies on column order.
            # Django migrations ensure deterministic column order.
            
            cursor.execute(f"INSERT INTO main.{name} SELECT * FROM source_db.{name}")
            
        conn_target.commit()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        # Fallback: using sqlcipher_export if available or manual dump
        # But ATTACH is standard.
    finally:
        conn_src.close()
        conn_target.close()

if __name__ == "__main__":
    # Settings
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SOURCE_DB = os.path.join(BASE_DIR, 'db.sqlite3')
    TARGET_DB = os.path.join(BASE_DIR, 'bd.sqlite3')
    PASSWORD = 'Devam123321!'
    
    migrate_db(SOURCE_DB, TARGET_DB, PASSWORD)
