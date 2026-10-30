# Application Update & Release Runbook

This document defines the official standard operating procedure (SOP) for preparing, compiling, testing, and deploying updates for **IPO Utility Desktop**.

---

## 1. Architecture Overview

The desktop software operates using a two-stage executable architecture:

1. **`manage.exe` (Django Engine)**:
   * Compiled via `manage.spec`.
   * Bundles Python runtime, Django, database backend, models, views, and migrations.
   * Runs as a headless local background subprocess listening on an internal port (`127.0.0.1:800X`).

2. **`IPOUtility.exe` (Desktop GUI & Launcher)**:
   * Compiled via `IPOUtility.spec`.
   * Bundles `Setup.py`, HTML templates, static files, USB hardware authentication, and `manage.exe`.
   * Displays the PyWebView desktop window, checks for remote updates, manages database migrations, and coordinates backups.

### Remote Server Infrastructure:
* **Update Server**: `http://46.202.162.106:8080`
  * Hosts `latest_version.txt`, `IPOUtility.exe`, and `/pemfile/`.
* **Database Backup Server**: `http://46.202.162.106:8000/api/IPOUtility_backup/backup-database`
  * Receives encrypted pre-migration and launch database backups.

---

## 2. Step-by-Step Update Checklist

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        UPDATE RELEASE PIPELINE                         │
  ├────────────────────────────────────────────────────────────────────────┤
  │ 1. Code & Migration Prep  ──>  2. Update Template DB (db.sqlite3)      │
  │ 3. Version Increments     ──>  4. Compile Binaries (manage & launcher) │
  │ 5. Local QA Verification  ──>  6. Deploy to Update Server (EXE & Ver)  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

### Step 1: Code & Database Migration Preparation

1. **Implement & test code changes** in models, views, or templates.
2. **If database models were modified**:
   * Generate migration files:
     ```bash
     python manage.py makemigrations
     ```
   * Dry-run check for graph integrity:
     ```bash
     python manage.py makemigrations --dry-run
     ```
   * **Increment `LOCAL_DB_VERSION`** in `Setup.py`:
     ```python
     # File: Setup.py (Line ~71)
     LOCAL_DB_VERSION = 3   # Increment whenever models/migrations change (e.g., 2 -> 3)
     ```
     > **Why?** Existing user machines compare their local `schema_version` with `LOCAL_DB_VERSION`. Incrementing this number triggers automatic database backups and runs `manage.exe migrate --noinput` on startup.

---

### Step 2: Update the Bundled Template Database (`db.sqlite3`)

> [!IMPORTANT]
> Because `IPOUtility.spec` bundles `db.sqlite3` into the final executable as the template for new installations, **you must apply the new migrations and update `schema_version` in `db.sqlite3` before compiling!**

Run these two commands in your terminal:
```bash
# 1. Apply the new migration to the bundled template DB
python manage.py migrate

# 2. Stamp the new schema version into the encrypted SQLCipher db.sqlite3
python -c "
from Setup import get_sqlcipher_connection, get_db_version

db_version_no = 3  # <-- Set your new schema version number here (matching LOCAL_DB_VERSION)

conn = get_sqlcipher_connection('db.sqlite3')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER);')
cur.execute('UPDATE schema_version SET version = ? WHERE id = 1;', (db_version_no,))
conn.commit()
conn.close()
print(f'Encrypted db.sqlite3 successfully updated to schema_version: {get_db_version(\"db.sqlite3\")}')
"

# 3. Verify current version numbers at a glance (checks encrypted DB with key automatically):
python -c "from Setup import get_db_version, LOCAL_DB_VERSION, LOCAL_VERSION; print(f'App Version: {LOCAL_VERSION} | Target DB Version: {LOCAL_DB_VERSION} | Encrypted db.sqlite3 Version: {get_db_version(\"db.sqlite3\")}')"
```

---

### Step 3: Version Number Increments

Update the version number in **two places**:

1. **In `Setup.py`**:
   ```python
   # File: Setup.py (Line ~70)
   LOCAL_VERSION = "1.0.8"   # Set new version
   ```
2. **In `latest_version.txt`**:
   ```text
   1.0.8
   ```

---

### Step 4: Compile Binaries (PyInstaller)

Always build in this exact sequence:

#### A. Build the Django Engine (`dist/manage.exe`):
```bash
pyinstaller manage.spec --clean
```
* **Output**: `dist/manage.exe` (or `dist/manage` on Linux).
* Contains the updated Python bytecode, Django models, views, and migrations.

#### B. Build the Desktop Launcher (`dist/IPOUtility.exe`):
```bash
pyinstaller IPOUtility.spec --clean
```
* **Output**: `dist/IPOUtility.exe` (or `dist/IPOUtility` on Linux).
* Bundles `dist/manage.exe`, `Setup.py`, templates, static assets, and the template `db.sqlite3`.

---

### Step 5: Quality Assurance & Pre-Flight Verification

Before pushing the build to the live server, test `dist/IPOUtility.exe` locally with a copy of an existing user database:

1. **Backup Verification**: Verify that a pre-migration database snapshot was created in:
   * Windows: `%APPDATA%\IPOUtilityBackup\DB_Schema_Backups\`
   * Linux: `~/.IPOUtilityBackup/DB_Schema_Backups/`
2. **Server Upload**: Verify that `migration_log.txt` shows the pre-migration upload succeeded.
3. **Migration Exit Code**: Confirm `migration_log.txt` outputs `Return code: 0`.
4. **App Launch**: Verify that the PyWebView window opens cleanly and user login functions as expected.

---

### Step 6: Deploy to Update Server (`http://46.202.162.106:8080`)

Upload the release files to the update server in this **strict sequence**:

1. **Upload Executable First**:
   Upload `dist/IPOUtility.exe` to:
   ```text
   http://46.202.162.106:8080/IPOUtility.exe
   ```

2. **Upload New PEM Certificates (if any were added)**:
   Place any updated `.pem` files into:
   ```text
   http://46.202.162.106:8080/pemfile/
   ```

3. **Publish `latest_version.txt` LAST**:
   Upload `latest_version.txt` (containing `1.0.8`) to:
   ```text
   http://46.202.162.106:8080/latest_version.txt
   ```
   > [!IMPORTANT]
   > **Always upload `latest_version.txt` last.** The moment this file is updated on the server, all active client machines will detect the version difference and immediately begin downloading `IPOUtility.exe`.

---

## 3. What Happens Automatically on Client Machines

When a user opens the application after an update is published:

1. **Update Detection**:
   * `Setup.py` queries `http://46.202.162.106:8080/latest_version.txt`.
   * Detects `latest_version ("1.0.8") != LOCAL_VERSION ("1.0.7")`.
   * Prompts user: *"Version 1.0.8 is available. Update now?"*

2. **Download & Swap**:
   * Displays a visual progress bar.
   * Downloads the new binary to `%TEMP%\ipo_update\IPOUtility_updated.exe`.
   * Synchronizes any new PEM files.
   * Backs up the running EXE as `IPOUtility.exe.bak`.
   * Replaces `IPOUtility.exe` with the new file and restarts.

3. **Database Migration & Disaster Recovery**:
   * Reads `current_db_ver` from `schema_version`.
   * If `LOCAL_DB_VERSION > current_db_ver`:
     1. Creates a local backup in `DB_Schema_Backups/`.
     2. Uploads the pre-migration snapshot to the backup server (`46.202.162.106:8000`).
     3. Runs `manage.exe migrate --noinput` silently in the background.
     4. Updates `schema_version` to the new version upon success.

4. **Launch**:
   * Pings `127.0.0.1:{port}` until Django responds with HTTP 200.
   * Closes the splash screen and opens the native GUI window.

---

## 4. Emergency Rollback Procedure

If an update causes an issue on client machines:

1. Revert `latest_version.txt` on the update server back to the previous stable version (e.g. `1.0.7`).
2. Replace `http://46.202.162.106:8080/IPOUtility.exe` with the previous stable executable.
3. If a client's database was altered, restore the pre-migration database snapshot from their local folder:
   ```text
   %APPDATA%\IPOUtilityBackup\DB_Schema_Backups\db_backup_v<old_version>_<timestamp>.sqlite3
   ```
   or retrieve the uploaded snapshot from the backup server.
