# IPOUtility Application - Professional Developer Documentation

This technical document provides a comprehensive, production-grade breakdown of the IPOUtility application. It is structured to enable any developer to fully understand, replicate, and enhance the application's design and implementation.

## Overview
IPOUtility is a secure, self-updating desktop application built using Python. It launches a Django web interface through an embedded browser using pywebview. The app emphasizes:
- USB-bound execution security.
- Auto-updating mechanisms for executable, database, and certificates.
- Daily backups and disaster recovery.
- Local Django server instance with database binding via environment variable.

## Workflow Summary
A complete operational flow from launch to shutdown:

**1. Initialization**
- Display splash screen.
- Check for updates to the app and database.
- Validate authorized USB drive.

**2. System Setup**
- Restore database from backup or copy from default.
- Set Django DB path via environment variable.
- Update local PEM certificate files from remote server.

**3. Server Startup**
- Find a free port in range 8000–8010.
- Launch Django backend using manage.exe.

**4. GUI Launch**
- Close splash screen.
- Open main GUI window with embedded Django frontend using webview.

**5. Runtime Monitoring**
- Monitor USB connection in background.
- Handle runtime events and user interactions.

**6. Shutdown**
- Backup database.
- Terminate Django and child processes.
- Perform cleanup operations.

---

## Configuration Constants
Key global settings:

```python
USE_USB_LOCK = True
USER_DB_NAME = "db.sqlite3"              # encrypted database - working copy
DEFAULT_DB_NAME = "IPOUtility_data.sqlite3"  # template/backup database
MANAGE_EXE = "manage.exe"
SERVER_BASE_URL = "http://46.202.162.106:8080"
UPDATE_VERSION_URL = f"{SERVER_BASE_URL}/latest_version.txt"
```

> **Note to Developer:** `db.sqlite3` acts as the active, encrypted database where user data is written. `IPOUtility_data.sqlite3` acts as the read-only template that is bundled with the executable. If the working copy goes missing, the system will attempt to restore from backups or fallback to copying this template.

These control critical behavior like locking, file locations, and update endpoints.

---

## Backup & Restore System
**Purpose:**
To prevent data loss by backing up the local DB daily and enabling restoration if needed.

**Functions:**
- `get_backup_folder()` – Returns the OS-specific backup path.
- `backup_db_to_local(path)` – Copies DB to backup folder.
- `restore_latest_db_to_usb(dest)` – Restores the latest backup to USB.
- `cleanup_old_backups(days=7)` – Deletes outdated backups.

**Code Example:**
```python
def backup_db_to_local(db_path):
    backup_path = get_today_backup_path()
    shutil.copy2(db_path, backup_path)
```

---

## Database Versioning & Replacement
**Purpose:**
Prevent schema mismatches during update.

**Key Logic:**
1. Fetch version from the `schema_version` table.
2. Compare local vs. updated DB version.
3. Replace if the updated version is newer.

**Code Snippet:**
```python
def get_db_version(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_version")
    return cur.fetchone()[0]
```

---

## Application Update Mechanism
**Purpose:**
Enable the app to auto-update both its binary and data layers.

**Core Steps:**
1. Fetch latest version.
2. Download new `.exe`, `.sqlite3`, and PEM files.
3. Compare DB versions and prompt replacement.
4. Restart app with updated executable.

**Code Snippet:**
```python
if latest_version != LOCAL_VERSION:
    download_file(UPDATE_EXE_URL, NEW_EXE_PATH)
    download_file(DB_DOWNLOAD_URL, NEW_DB_PATH)
    replace_and_restart()
```

---

## USB Lock & Authorization System
**Purpose:**
Restrict app usage to an authorized USB drive using serial verification and encrypted keys.

**Functions:**
- `get_usb_serial()` – Extracts USB serial.
- `decrypt_serial_from_json()` – Decrypts expected serial.
- `check_usb_lock()` – Validates runtime USB.

**Code Snippet:**
```python
if get_usb_serial() != decrypt_serial_from_json():
    messagebox.showerror("USB Lock", "Unauthorized USB.")
    sys.exit(1)
```

---

## PEM File Management
**Purpose:**
Ensure the application fetches secure certificate files on each launch.

**Code Snippet:**
```python
for link in soup.find_all('a'):
    if link.get('href').endswith('.pem'):
        file_url = urljoin(PEM_FOLDER_URL + '/', href)
        download_file(file_url, local_path)
```

---

## Resource Management
**Purpose:**
Handle relative paths for both development and PyInstaller builds.

**Code Snippet:**
```python
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)
```

---

## Django Integration
**Purpose:**
Launch Django server locally on an available port with isolated DB path.

**Key Components:**
- Port scanning: `is_port_available()`
- Launch server: `run_django(port)`
- Set DB path: `write_django_db_path(db_path)`

**Code Snippet:**
```python
def run_django(port):
    subprocess.Popen([
        resource_path(MANAGE_EXE), 'runserver', f'127.0.0.1:{port}'
    ], creationflags=..., ...)
```

---

## Splash Screen
**Purpose:**
Enhance user experience during boot-up.

**Code Snippet:**
```python
splash = tk.Tk()
splash.title("IPO Utility")
label = tk.Label(splash, text="Loading...")
label.pack()
```

---

## Main Application Window
**Purpose:**
Launch the final interface as a web application within a native window using webview.

**Code Snippet:**
```python
webview.create_window("IPO Utility", f"http://127.0.0.1:{port}", width=1024, height=768)
```

---

## Graceful Shutdown & Cleanup
**Purpose:**
Terminate child processes, backup DB, and prevent zombie instances.

**Code Snippet:**
```python
def on_close():
    backup_db_to_local(db_path)
    if django_process:
        django_process.terminate()
    os._exit(0)
```

---

## Final Notes
This documentation is a complete technical and step-by-step user/developer guide. Anyone following this guide can:
- Build the IPOUtility app from scratch
- Understand every system used
- Maintain and extend the system

Always keep your `db.sqlite3`, `pemfile/`, and `.json` config files secure and properly bundled during builds.
