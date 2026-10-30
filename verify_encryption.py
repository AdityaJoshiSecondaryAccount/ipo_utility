
import sqlite3
import sys

def check_encrypted(db_path):
    print(f"Checking if {db_path} is encrypted...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("FAIL: Opened successfully with standard sqlite3. Tables found: " + str(tables))
        conn.close()
    except sqlite3.DatabaseError as e:
        print("SUCCESS: Failed to open with standard sqlite3: " + str(e))
    except Exception as e:
        print("SUCCESS: Failed with error: " + str(e))

if __name__ == "__main__":
    check_encrypted("bd.sqlite3")
