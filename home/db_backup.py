import os
import requests
import threading
from django.conf import settings

def is_internet_available():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except (requests.ConnectionError, requests.Timeout, requests.RequestException):
        return False

def upload_db_to_server(username):
    url = "http://46.202.162.106:8000/api/IPOUtility_backup/backup-database"
    db_path = getattr(settings, 'DATABASES', {}).get('default', {}).get('NAME') or os.path.join(settings.BASE_DIR, 'db.sqlite3')
    data = {
        "username": str(username)
    }
    try:
        if not is_internet_available():
            print("Internet not available. Skipping DB upload.")
            return
        if not os.path.exists(str(db_path)):
            print(f"DB file not found at {db_path}")
            return
        with open(str(db_path), "rb") as f:
            files = {"file": f}
            response = requests.post(url, data=data, files=files, timeout=30)
        print(f"DB upload response: {response.text}")
    except Exception as e:
        print(f"Error uploading DB: {e}")

def trigger_background_db_upload(username):
    if username and str(username) != "AnonymousUser":
        threading.Thread(target=upload_db_to_server, args=(str(username),), daemon=True).start()