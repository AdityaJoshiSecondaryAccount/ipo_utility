# launcher.py
import os
import sys

# On Linux, allow access to system GTK / WebKit2 packages for pywebview
if sys.platform != "win32":
    for p in ["/usr/lib/python3.14/site-packages", "/usr/local/lib/python3.14/site-packages"]:
        if os.path.exists(p) and p not in sys.path:
            sys.path.append(p)
import shutil
import json
import time
import tempfile
import tkinter as tk
from tkinter import messagebox
import webview
import subprocess
import socket
from threading import Thread
import urllib.request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sqlite3
import re
import psutil
import platform
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import atexit
try:
    from sqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    try:
        from pysqlcipher3 import dbapi2 as sqlcipher
    except ImportError:
        sqlcipher = None
import webview.menu as wm
import traceback
from tkinter import ttk

log_file = open("launcher_log.txt", "w")

def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=log_file)
    log_file.flush()

sys.excepthook = log_unhandled_exception

# --- CONFIGURATION ---
USE_USB_LOCK = True
OFFLINE_HTML_PATH = os.path.join("templates", "index.html")
MANAGE_EXE = "manage.exe" if platform.system() == "Windows" else "manage" # expect manage.exe to be next to this launcher EXE
# USER_DB_NAME = "IPOUtility_data.sqlite3"
# DEFAULT_DB_NAME = "db.sqlite3"  
# # this should be a template DB bundled as resource (read-only)
USER_DB_NAME = "db.sqlite3"              # encrypted database - working copy
DEFAULT_DB_NAME = "IPOUtility_data.sqlite3"  # template/backup database
PEM_FOLDER_NAME = "pemfile"
PORT_RANGE_START = 8000
PORT_RANGE_END = 8010
SYS_USB_FILE = "sys_usb.json"
PUBLIC_EXPONENT = 12113
MODULUS = 17947
SERVER_BASE_URL = "http://46.202.162.106:8080"
UPDATE_VERSION_URL = f"{SERVER_BASE_URL}/latest_version.txt"
UPDATE_EXE_URL = f"{SERVER_BASE_URL}/IPOUtility.exe"
PEM_FOLDER_URL = f"{SERVER_BASE_URL}/pemfile"
DB_VERSION_URL = f"{SERVER_BASE_URL}/db_version.txt"
LOCAL_VERSION = "1.0.8"
LOCAL_DB_VERSION = 2                   # Increment when Django models/migrations change
django_process = None

# Temporary folder for downloads/updates (writable)
TEMP_FOLDER = os.path.join(tempfile.gettempdir(), "ipo_update")
NEW_EXE_PATH = os.path.join(TEMP_FOLDER, "IPOUtility_updated.exe")

# --- Helpers for paths when frozen (PyInstaller) ---
def resource_path(relative_path):
    """
    When running as a bundle, files are extracted to sys._MEIPASS.
    Use resource_path to locate bundled files (templates/static/logo etc).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_real_app_dir():
    """
    Returns directory where the launcher EXE lives (or source folder when not frozen).
    This is the preferred location for a writable DB file next to the EXE.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- Backup & Restore ---
def get_backup_folder():
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", get_real_app_dir()), "IPOUtilityBackup")
    else:
        return os.path.expanduser("~/.IPOUtilityBackup")

def get_today_backup_path():
    backup_folder = get_backup_folder()
    os.makedirs(backup_folder, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    # return os.path.join(backup_folder, f"IPOUtility_data_{today_str}.sqlite3")
    return os.path.join(backup_folder, f"db_{today_str}.sqlite3")

def backup_db_to_local(db_path):
    backup_path = get_today_backup_path()
    try:
        shutil.copy2(db_path, backup_path)
    except Exception as e:
        print(f"Backup failed: {e}")

def restore_latest_db_to_usb(usb_db_path):
    backup_folder = get_backup_folder()
    if not os.path.exists(backup_folder):
        return False
    backups = [f for f in os.listdir(backup_folder) if f.startswith("db_") and f.endswith(".sqlite3")]
    if not backups:
        return False
    backups.sort(reverse=True)
    latest_backup = os.path.join(backup_folder, backups[0])
    try:
        shutil.copy2(latest_backup, usb_db_path)
        print(f"Restored DB from backup: {latest_backup}")
        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

def cleanup_old_backups(days=7):
    backup_folder = get_backup_folder()
    if not os.path.exists(backup_folder):
        return
    now = datetime.now()
    for f in os.listdir(backup_folder):
        # if f.startswith("IPOUtility_data_") and f.endswith(".sqlite3"):
        if f.startswith("db_") and f.endswith(".sqlite3"):
            path = os.path.join(backup_folder, f)
            try:
                date_str = f.replace("db_", "").replace(".sqlite3", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if now - file_date > timedelta(days=days):
                    os.remove(path)
            except Exception as e:
                print(f"Failed to remove old backup {f}: {e}")

# --- Server DB Backup ---
BACKUP_SERVER_URL = "http://46.202.162.106:8000/api/IPOUtility_backup/backup-database"

def is_internet_available():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False

def get_primary_username(db_path):
    try:
        password = 'Devam123321!'
        conn = sqlcipher.connect(db_path)
        conn.execute(f"PRAGMA key = '{password}';")
        cur = conn.cursor()
        cur.execute("SELECT username FROM home_customuser ORDER BY id ASC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "unknown_user"
    except Exception:
        return "unknown_user"

def upload_db_to_server_on_launch(db_path):
    try:
        if not is_internet_available():
            print("Internet not available. Skipping server backup.")
            return
        username = get_primary_username(db_path)
        data = {"username": str(username)}
        with open(db_path, "rb") as f:
            files = {"file": f}
            response = requests.post(BACKUP_SERVER_URL, data=data, files=files, timeout=20)
        print(f"Server DB backup on launch: {response.text}")
    except Exception as e:
        print(f"Server DB backup on launch error: {e}")

# --- Get & Set DB Schema Version ---
def get_db_version(db_path):
    try:
        password = 'Devam123321!'
        conn_target = sqlcipher.connect(db_path)
        conn_target.execute(f"PRAGMA key = '{password}';")
        cur = conn_target.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER)")
        conn_target.commit()
        cur.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        conn_target.close()
        return row[0] if row and row[0] is not None else 0
    except Exception:
        return 0

def set_db_version(db_path, new_version):
    try:
        password = 'Devam123321!'
        conn_target = sqlcipher.connect(db_path)
        conn_target.execute(f"PRAGMA key = '{password}';")
        cur = conn_target.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER)")
        cur.execute("SELECT id FROM schema_version LIMIT 1")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO schema_version (id, version) VALUES (1, ?)", (new_version,))
        else:
            cur.execute("UPDATE schema_version SET version = ? WHERE id = ?", (new_version, row[0]))
        conn_target.commit()
        conn_target.close()
        return True
    except Exception as e:
        print(f"Error updating schema_version: {e}")
        return False

# --- Schema Update Backup & In-Place Migration ---
SCHEMA_BACKUP_FOLDER_NAME = "DB_Schema_Backups"

def backup_db_for_schema_update(db_path, old_version):
    """
    Backs up the current db.sqlite3 into a dedicated 'DB_Schema_Backups' folder 
    in the user PC's backup directory (APPDATA) before making schema migrations.
    """
    try:
        backup_dir = os.path.join(get_backup_folder(), SCHEMA_BACKUP_FOLDER_NAME)
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file_name = f"db_backup_v{old_version}_{timestamp}.sqlite3"
        backup_dest = os.path.join(backup_dir, backup_file_name)
        shutil.copy2(db_path, backup_dest)
        print(f"Schema update backup created at: {backup_dest}")
        return backup_dest
    except Exception as e:
        print(f"Schema backup failed: {e}")
        return None

def get_sqlcipher_connection(db_path):
    password = 'Devam123321!'
    if sqlcipher:
        conn = sqlcipher.connect(db_path)
        conn.execute(f"PRAGMA key = '{password}';")
        return conn
    else:
        return sqlite3.connect(db_path)

def get_baseline_replaces():
    """
    Dynamically extracts the 'replaces' list from home/migrations/0001_baseline.py
    without hardcoding migration names or requiring full Django initialization.
    """
    import ast
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    possible_paths = [
        resource_path(os.path.join("home", "migrations", "0001_baseline.py")),
        os.path.join(base_dir, "home", "migrations", "0001_baseline.py"),
        os.path.join(os.getcwd(), "home", "migrations", "0001_baseline.py"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == "Migration":
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id == "replaces":
                                        return ast.literal_eval(item.value)
            except Exception as e:
                print(f"Error parsing {path}: {e}")

    try:
        import importlib
        mod = importlib.import_module("home.migrations.0001_baseline")
        migration_cls = getattr(mod, "Migration", None)
        if migration_cls and hasattr(migration_cls, "replaces"):
            return list(migration_cls.replaces)
    except Exception:
        pass

    return []

def ensure_baseline_migration_recorded(db_path):
    """
    Ensures existing user databases transition cleanly into the squashed 0001_baseline migration.
    If the database is an existing production DB (contains home_customuser), satisfies the legacy
    replaced keys in django_migrations dynamically from Migration.replaces so Django treats
    0001_baseline as fully satisfied.
    """
    try:
        conn = get_sqlcipher_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='home_customuser'")
        if cur.fetchone():
            replaces = get_baseline_replaces()
            for app, name in replaces:
                cur.execute(
                    "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES (?, ?, datetime('now'))",
                    (app, name)
                )
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"ensure_baseline_migration_recorded warning: {e}")

def run_django_migrations(db_path):
    """
    Executes standard native 'manage.exe migrate --noinput'.
    Django automatically detects any unapplied migrations and applies them sequentially.
    """
    try:
        manage_path = resource_path(MANAGE_EXE)
        if not os.path.exists(manage_path):
            return False, f"{MANAGE_EXE} not found at {manage_path}"

        env = os.environ.copy()
        env['DJANGO_DB_PATH'] = db_path
        env['DB_ENGINE'] = 'sqlite'
        env['IS_EXE'] = 'true'

        # Ensure legacy databases transition smoothly to squashed baseline
        ensure_baseline_migration_recorded(db_path)

        proc = subprocess.run(
            [manage_path, 'migrate', '--noinput'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
            text=True
        )

        with open("migration_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- Migration Run at {datetime.now()} ---\n")
            f.write(f"Return code: {proc.returncode}\n")
            f.write(f"STDOUT:\n{proc.stdout}\n")
            f.write(f"STDERR:\n{proc.stderr}\n")

        if proc.returncode == 0:
            return True, proc.stdout
        else:
            return False, proc.stderr or proc.stdout

    except Exception as e:
        return False, str(e)

def check_and_apply_db_migrations(db_path):
    """
    Checks if the local DB schema version is older than the application's LOCAL_DB_VERSION.
    If an upgrade is needed:
      1. Backs up the database to DB_Schema_Backups/ locally.
      2. Uploads pre-migration database snapshot to the server IP if online.
      3. Runs standard 'manage.exe migrate --noinput'.
      4. Updates schema_version on success.
    """
    try:
        current_db_ver = get_db_version(db_path)
        if LOCAL_DB_VERSION > current_db_ver:
            print(f"Database schema update required: v{current_db_ver} -> v{LOCAL_DB_VERSION}")
            backup_file = backup_db_for_schema_update(db_path, current_db_ver)
            
            # Upload untouched pre-migration copy to server before executing migrations
            try:
                target_backup = backup_file if backup_file and os.path.exists(backup_file) else db_path
                upload_db_to_server_on_launch(target_backup)
            except Exception as e:
                print(f"Pre-migration server upload warning: {e}")

            migration_ok, migration_msg = run_django_migrations(db_path)
            if migration_ok:
                set_db_version(db_path, LOCAL_DB_VERSION)
                print(f"Database successfully updated to schema v{LOCAL_DB_VERSION}.")
                return True
            else:
                print(f"[Migration Warning] Database update issue:\n{migration_msg}")
                set_db_version(db_path, LOCAL_DB_VERSION)
                return True
        return True
    except Exception as e:
        print(f"check_and_apply_db_migrations error: {e}")
        return False

# --- Replace and Restart with New EXE ---
def replace_and_restart():
    try:
        current_exe = sys.executable
        new_exe = NEW_EXE_PATH
        backup = current_exe + ".bak"
        # rename current exe to backup (if possible)
        try:
            os.replace(current_exe, backup)
        except Exception:
            pass
            # # fallback: attempt rename
            # try:
            #     os.rename(current_exe, backup)
            # except Exception as e:
            #     print("Could not backup current exe:", e)
        shutil.copyfile(NEW_EXE_PATH, current_exe)
        # start new exe
        time.sleep(0.7)

        # Start new exe with correct working directory
        subprocess.Popen([current_exe], cwd=os.path.dirname(current_exe))

        # Force exit to avoid Tkinter DLL error
        os._exit(0)
    except Exception as e:
        messagebox.showerror("EXE Replace Failed", str(e))

# --- Download file ---
def download_file(url, dest):
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        messagebox.showerror("Download Error", str(e))

# --- Download file with Visual Progress Bar ---
def download_file_with_progress(url, dest, file_label_text, progress_window, progress_bar, status_label):
    """
    Downloads a file while updating a shared Tkinter progress bar setup.
    """
    try:
        status_label.config(text=f"Downloading {file_label_text}...")
        progress_bar['value'] = 0
        progress_window.update()

        # Send a head request first to get total file size
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if total_size > 0:
                        downloaded_size += len(chunk)
                        # Calculate percent percentage
                        percent = int((downloaded_size / total_size) * 100)
                        progress_bar['value'] = percent
                        status_label.config(text=f"Downloading {file_label_text}: {percent}%")
                        progress_window.update()
                        
        progress_bar['value'] = 100
        progress_window.update()
    except Exception as e:
        raise Exception(f"Failed to download {file_label_text}: {str(e)}")


# --- Update PEM Files ---
def update_pem_files_with_status(status_label, progress_window):
    """
    Updates PEM files and informs the user via the progress status label.
    """
    try:
        status_label.config(text="Updating PEM certificates...")
        progress_window.update()
        
        pem_dir = os.path.join(get_real_app_dir(), PEM_FOLDER_NAME)
        os.makedirs(pem_dir, exist_ok=True)
        
        soup = BeautifulSoup(requests.get(PEM_FOLDER_URL, timeout=10).text, 'html.parser')
        pem_links = [link.get('href') for link in soup.find_all('a') if link.get('href') and link.get('href').endswith('.pem')]
        
        total_pems = len(pem_links)
        for idx, href in enumerate(pem_links, start=1):
            status_label.config(text=f"Updating PEM certificates ({idx}/{total_pems})...")
            progress_window.update()
            
            file_url = urljoin(PEM_FOLDER_URL + '/', href)
            with open(os.path.join(pem_dir, os.path.basename(href)), 'wb') as f:
                f.write(requests.get(file_url, timeout=10).content)
    except Exception as e:
        print(f"PEM update error (non-critical): {e}")

# --- Check for Updates ---
def check_for_updates():
    try:
        response = requests.get(UPDATE_VERSION_URL, timeout=5)
        response.raise_for_status()
        latest_version = response.text.strip()
        
        if latest_version != LOCAL_VERSION:
            if messagebox.askyesno("Update Available", f"Version {latest_version} is available. Update now?"):
                os.makedirs(TEMP_FOLDER, exist_ok=True)
                
                # --- Create Tkinter Progress Window UI ---
                progress_window = tk.Toplevel()
                progress_window.title("Downloading Updates")
                progress_window.geometry("400x130")
                progress_window.resizable(False, False)
                progress_window.attributes("-topmost", True)  # Keep window on top
                
                # Center window on screen
                screen_width = progress_window.winfo_screenwidth()
                screen_height = progress_window.winfo_screenheight()
                x = (screen_width // 2) - (400 // 2)
                y = (screen_height // 2) - (130 // 2)
                progress_window.geometry(f"400x130+{x}+{y}")

                # UI Elements
                lbl_title = tk.Label(progress_window, text="Application Update in Progress", font=("Helvetica", 11, "bold"))
                lbl_title.pack(pady=10)

                lbl_status = tk.Label(progress_window, text="Preparing downloads...", font=("Helvetica", 9))
                lbl_status.pack(pady=2)

                progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=320, mode="determinate")
                progress_bar.pack(pady=10)
                
                progress_window.update()

                try:
                    # 1. Download updated executable
                    download_file_with_progress(UPDATE_EXE_URL, NEW_EXE_PATH, "Executable (Application)", progress_window, progress_bar, lbl_status)
                    # 2. Process PEM background modifications
                    update_pem_files_with_status(lbl_status, progress_window)

                except Exception as update_err:
                    progress_window.destroy()
                    messagebox.showerror("Update Interrupted", str(update_err))
                    return

                # Close progress pop up when done
                progress_window.destroy()

                messagebox.showinfo("Update Complete", "App will now restart with the new version.")
                replace_and_restart()
    except Exception as e:
        print(f"Update check failed: {e}")

# --- USB Serial Functions (Windows only) ---
def get_drive_volume_serial(drive_path):
    """
    Retrieves Volume Serial Number using native Win32 API (kernel32.GetVolumeInformationW).
    Completely eliminates deprecated WMIC dependency. Fully compatible with Windows 10, 11 (24H2+), and future versions.
    Returns an 8-character uppercase hex string (e.g. '2CEDEA20').
    """
    # Primary: Direct Win32 API (In-process, sub-millisecond, native C call)
    try:
        import ctypes
        drive_root = drive_path.rstrip('\\') + '\\'
        serial_number = ctypes.c_ulong(0)
        res = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive_root),
            None, 0,
            ctypes.byref(serial_number),
            None, None, None, 0
        )
        if res and serial_number.value:
            return f"{serial_number.value:08X}"
    except Exception as e:
        print(f"Win32 API GetVolumeInformationW failed for {drive_path}: {e}")

    # Secondary Fallback: PowerShell Get-CimInstance (Microsoft's official modern replacement for WMIC)
    try:
        usb_letter = drive_path.rstrip('\\')
        cmd = f'powershell -NoProfile -Command "(Get-CimInstance Win32_LogicalDisk -Filter \\"DeviceID=\'{usb_letter}\'\\").VolumeSerialNumber"'
        output = subprocess.check_output(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        serial = output.decode(errors='ignore').strip().replace("-", "")
        if len(serial) >= 4:
            return serial.upper()
    except Exception as e:
        print(f"PowerShell CIM fallback failed for {drive_path}: {e}")

    return None

def get_usb_serial():
    try:
        decrypt_serial = decrypt_serial_from_json()
        if not decrypt_serial:
            return None

        # --- Windows Detection ---
        if platform.system() == "Windows":
            import ctypes, string
            from ctypes import windll
            drives = [l + ':\\' for i, l in enumerate(string.ascii_uppercase) if ctypes.windll.kernel32.GetLogicalDrives() & (1 << i)]
            for drive in drives:
                if windll.kernel32.GetDriveTypeW(drive) >= 2:
                    serial = get_drive_volume_serial(drive)
                    if serial and serial.upper() == decrypt_serial.upper():
                        return serial

        # --- Linux Detection ---
        else:
            out = subprocess.check_output(['lsblk', '-J', '-o', 'NAME,UUID,MOUNTPOINT,TRAN']).decode()
            data = json.loads(out)
            def scan_devs(devs):
                for d in devs:
                    if d.get('uuid'):
                        uuid_clean = d['uuid'].replace('-', '').upper()
                        if uuid_clean == decrypt_serial.upper():
                            return uuid_clean
                    if 'children' in d:
                        res = scan_devs(d['children'])
                        if res:
                            return res
                return None
            return scan_devs(data.get('blockdevices', []))

    except Exception as e:
        print(f"USB serial error: {e}")
    return None

def decrypt_serial_from_json():
    try:
        # Use resource_path to find the bundled sys_usb.json
        sys_usb_filepath = os.path.join(get_real_app_dir(), SYS_USB_FILE)
        with open(sys_usb_filepath ,"r") as f:
            encrypted_chars = json.load(f)["encrypted_serial"]
        return ''.join([chr(pow(c, PUBLIC_EXPONENT, MODULUS)) for c in encrypted_chars])
    except Exception as e:
        traceback.print_exc()
        print(f"Decrypt error: {e}")
        return None

def check_usb_lock():
    if not USE_USB_LOCK:
        return True
    current, expected = get_usb_serial(), decrypt_serial_from_json()
    print(f"Detected USB: {current}, Expected USB: {expected}")
    return current is not None and expected is not None and current.upper() == expected.upper()

def is_running_from_usb():
    if not USE_USB_LOCK:
        return True
    try:
        expected_serial = decrypt_serial_from_json()
        if not expected_serial:
            return False

        if platform.system() == "Windows":
            exe_path = os.path.abspath(sys.argv[0])
            exe_drive = os.path.splitdrive(exe_path)[0].upper() + "\\"  # e.g., 'E:\\'
            current_serial = get_drive_volume_serial(exe_drive)
            print(f"is_running_from_usb: exe_drive={exe_drive}, current_serial={current_serial}, expected_serial={expected_serial}")
            return bool(current_serial and current_serial.upper() == expected_serial.upper())
        else:
            # On Linux, verify that the expected partition is currently mounted and active
            detected = get_usb_serial()
            print(f"is_running_from_usb (Linux): detected={detected}, expected_serial={expected_serial}")
            return bool(detected and detected.upper() == expected_serial.upper())
    except Exception as e:
        print(f"is_running_from_usb error: {e}")
    return False

def monitor_usb():
    initial = get_usb_serial()
    while True:
        time.sleep(5)
        current = get_usb_serial()
        if current != initial:
            tk.Tk().withdraw()
            messagebox.showerror("USB Removed", "USB drive removed. Closing app.")
            on_close(force=True)
            break

# --- Other Functions ---
def release_sqlite_locks(db_path):
    try:
        password = 'Devam123321!'
        conn_target = sqlcipher.connect(db_path)
        conn_target.execute(f"PRAGMA key = '{password}';")
        conn_target.execute("PRAGMA wal_checkpoint(FULL);")
        conn_target.commit()
        conn_target.close()
    except Exception as e:
        print(f"release_sqlite_locks error (non-critical): {e}")

def copy_db_if_needed():
    """
    Ensure a writable DB exists next to the EXE (app_dir/USER_DB_NAME).
    If not present, try to restore from backup folder; otherwise copy a default DB bundled as resource.
    DO NOT bundle the real working db inside the exe - only a template DEFAULT_DB_NAME should be bundled.
    """
    # base_dir = get_real_app_dir()
    db_dest = os.path.join(os.path.dirname(sys.argv[0]), USER_DB_NAME)
    if not os.path.exists(db_dest):
        if not restore_latest_db_to_usb(db_dest):
            # copy a default template DB from resources (resource_path handles _MEIPASS)
            # Ensure we look for the bundled 'db.sqlite3' which is what we will bundle in spec
            shutil.copyfile(resource_path(USER_DB_NAME), db_dest)
    return db_dest

def write_django_db_path(db_path):
    # Set env var for manage.exe / Django to pick up
    os.environ['DJANGO_DB_PATH'] = db_path

def is_port_available(port):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', port)) != 0

def run_django(port, db_path):
    """
    Launch manage with DJANGO_DB_PATH in env so Django uses external DB.
    """
    global django_process
    try:
        manage_path = resource_path(MANAGE_EXE)
        if not os.path.exists(manage_path):
            messagebox.showerror("File Missing", f"{MANAGE_EXE} not found next to launcher: {manage_path}")
            sys.exit(1)

        env = os.environ.copy()
        env['DJANGO_DB_PATH'] = db_path

        popen_kwargs = {
            'stdout': open("manage_log.txt", "w"),
            'stderr': open("manage_err.txt", "w"),
            'env': env,
        }
        if platform.system() == "Windows":
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

        django_process = subprocess.Popen([
            manage_path, 'runserver', f'127.0.0.1:{port}', '--noreload'
        ], **popen_kwargs)
        
    except FileNotFoundError as e:
        messagebox.showerror("File Missing", f"{MANAGE_EXE} not found: {e}")
        sys.exit(1)
    except Exception as e:
        messagebox.showerror("Could not start Django", str(e))
        sys.exit(1)

def scan_pem_files():
    pem_dir = os.path.join(os.path.dirname(sys.argv[0]), PEM_FOLDER_NAME)
    with open("pem_files.json", "w") as f:
        json.dump([f for f in os.listdir(pem_dir) if f.endswith('.pem')], f)

def show_splash_screen():
    splash = tk.Tk()
    splash.geometry("350x200")
    splash.title("IPO Utility")
    try:
        logo_img = Image.open(resource_path("logo.png"))
        resample_filter = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS', getattr(Image, 'ANTIALIAS', 1))
        logo_img = logo_img.resize((64, 64), resample_filter)
        logo = ImageTk.PhotoImage(logo_img)
        label_logo = tk.Label(splash, image=logo)
        label_logo.image = logo
        label_logo.pack(pady=10)
    except Exception as e:
        print(f"Logo load error: {e}")
    tk.Label(splash, text="Loading IPO Utility...", font=("Helvetica", 14)).pack(expand=True)
    splash.update()
    return splash

def on_close(force=False):
    global django_process, db_path
    try:
        if django_process and django_process.poll() is None:
            try:
                parent = psutil.Process(django_process.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
                try:
                    parent.kill()
                except Exception:
                    pass
            except Exception:
                try:
                    django_process.terminate()
                    django_process.wait(timeout=5)
                except Exception:
                    pass
    except Exception:
        pass
    if not force:
        try:
            window.destroy()
        except Exception:
            pass
    os._exit(0)

atexit.register(on_close, force=True)


def reload_page():
    # Forces the window to reload the current URL
    # Useful if the server started late and the page is blank
    window.load_url(window.get_current_url())

def go_home():
    # Redirects back to the main local server URL
    # We use the global 'port' variable
    window.load_url(f"http://127.0.0.1:{port}")

def go_back():
    # Uses Javascript to go back in history
    window.evaluate_js("history.back()")

# --- Main Entry ---
if __name__ == "__main__":
    # 1) USB lock checks (if enabled)
    if not check_usb_lock():
        tk.Tk().withdraw()
        messagebox.showerror("USB Lock", "Invalid USB drive detected.")
        sys.exit(1)
    if not is_running_from_usb():
        tk.Tk().withdraw()
        messagebox.showerror("USB Lock", "Please run the application from the authorized USB drive.")
        sys.exit(1)
    if USE_USB_LOCK:
        Thread(target=monitor_usb, daemon=True).start()

    # 2) Check updates (optional)
    try:
        check_for_updates()
    except Exception:
        pass

    # 3) Show splash screen while initializing
    splash = show_splash_screen()

    # Ensure database exists next to EXE and is writable
    db_path = copy_db_if_needed()
    # release any sqlite locks and set env var
    release_sqlite_locks(db_path)
    write_django_db_path(db_path)
    scan_pem_files()

    # Check and apply migrations silently in background while splash is shown
    check_and_apply_db_migrations(db_path)

    # Upload backup to server on launch if internet is available (after migrations)
    Thread(target=upload_db_to_server_on_launch, args=(db_path,), daemon=True).start()

    # 4) Find available port and start Django server

    # find available port
    port = next((p for p in range(PORT_RANGE_START, PORT_RANGE_END + 1) if is_port_available(p)), None)
    if not port:
        tk.Tk().withdraw()
        messagebox.showerror("Port Error", "No available port found.")
        sys.exit(1)

    # run manage.exe in background thread
    Thread(target=run_django, args=(port,db_path,), daemon=True).start()

    # wait until local server responds
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    splash.destroy()

    # setup GUI window with webview
    webview.settings['ALLOW_DOWNLOADS'] = True

    window = tk.Tk()
    window.title("IPO Utility")
    try:
        window.iconphoto(True, ImageTk.PhotoImage(Image.open(resource_path("logo.png"))))
    except Exception:
        pass
    window.protocol("WM_DELETE_WINDOW", on_close)
    
    menu_items = [
        wm.Menu(
            'Navigation',
            [
                wm.MenuAction('Home', go_home),       # Changed from MenuItem to MenuAction
                wm.MenuAction('Refresh', reload_page), # Changed from MenuItem to MenuAction
                wm.MenuAction('Back', go_back),       # Changed from MenuItem to MenuAction
            ]
        ),
        wm.Menu(
            'Exit',
            [
                wm.MenuAction('Exit', on_close)       # Changed from MenuItem to MenuAction
            ]
        )
    ]

    # create and start webview app
    window = webview.create_window("IPO Utility", f"http://127.0.0.1:{port}", x=0, y=0, width=1024, height=768 ,menu=menu_items)
    webview.start(gui='tk')

    # final cleanup if webview exits
    on_close()
