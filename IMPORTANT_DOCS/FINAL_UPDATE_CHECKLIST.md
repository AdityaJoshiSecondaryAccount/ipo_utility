# Pre-Release & Update Execution Checklist (Master TODO)

> **Release Version**: `v_____` &nbsp;|&nbsp; **Target DB Version**: `v_____` &nbsp;|&nbsp; **Date**: `YYYY-MM-DD` &nbsp;|&nbsp; **Developer**: `__________`

*Use this master checklist as the mandatory sequential pre-flight gate before releasing any application update to production. Every item must be executed and checked off in order.*

---

## Phase 1: Code & Database (Development Environment)

- [ ] **1.1. Model Changes & Sequential Migration Generation**
  * Did you add or modify any models in `home/models.py`?
  * If **YES**, generate the migration:
    ```bash
    python manage.py makemigrations
    ```
  * **Verification**: Confirm a clean, sequential forward migration file was generated (e.g. `0003_...`). *Never edit or delete `0001_baseline.py`.*

- [ ] **1.2. Migration Graph & Dry-Run Integrity Check**
  * Check that no pending schema differences remain:
    ```bash
    python manage.py makemigrations --dry-run
    ```
  * **Verification**: Must return `"No changes detected"`.

- [ ] **1.3. Bump `LOCAL_DB_VERSION` in `Setup.py`**
  * File: `Setup.py` (around line 71)
  * Action: If models or migrations changed, increment `LOCAL_DB_VERSION` (e.g., `2` &rarr; `3`).
  * *Failure to increment will cause client desktop databases to skip the migration and crash.*

- [ ] **1.4. Apply Migrations to Template Database (`db.sqlite3`)**
  * Apply pending schema changes to the local development database:
    ```bash
    python manage.py migrate
    ```
  * **Verification**: Confirm output shows `Applying home.XXXX... OK`.

- [ ] **1.5. Stamp Schema Version in Encrypted SQLCipher `db.sqlite3`**
  * Ensure the bundled template database has its internal `schema_version` matching the new `LOCAL_DB_VERSION`:
    ```bash
    python -c "
    from Setup import get_sqlcipher_connection, get_db_version
    db_version_no = 3  # <-- Match your new LOCAL_DB_VERSION
    conn = get_sqlcipher_connection('db.sqlite3')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER);')
    cur.execute('UPDATE schema_version SET version = ? WHERE id = 1;', (db_version_no,))
    conn.commit()
    conn.close()
    print('Stamped schema_version:', get_db_version('db.sqlite3'))
    "
    ```
  * **Verification**: Terminal prints the updated `schema_version` number.

- [ ] **1.6. Verify Version Alignment at a Glance**
  * Run the one-line cross-check:
    ```bash
    python -c "from Setup import get_db_version, LOCAL_DB_VERSION, LOCAL_VERSION; print(f'App Version: {LOCAL_VERSION} | Target DB: {LOCAL_DB_VERSION} | Stamped DB: {get_db_version(\"db.sqlite3\")}')"
    ```
  * **Verification**: Confirm `Target DB` strictly matches `Stamped DB`.

---

## Phase 2: Application Versioning

- [ ] **2.1. Update `LOCAL_VERSION` in `Setup.py`**
  * File: `Setup.py` (around line 70)
  * Action: Set the new release version string (e.g. `LOCAL_VERSION = "1.0.8"`).

- [ ] **2.2. Update `latest_version.txt`**
  * File: `latest_version.txt` (line 1)
  * Action: Set the exact same version string (e.g. `1.0.8`).

---

## Phase 3: Dependencies & Clean Build

- [ ] **3.1. Audit `hiddenimports` in `manage.spec`**
  * Action: If any new third-party `pip` packages were installed during development, verify they are explicitly declared under `hiddenimports` in `manage.spec`.

- [ ] **3.2. Clear Old Build Cache & Artifacts**
  * Clean previous compilation directories:
    ```bash
    rm -rf build/ dist/
    ```

---

## Phase 4: Two-Stage PyInstaller Compilation (Strict Order)

- [ ] **4.1. Stage 1 — Compile Django Backend Engine (`manage.spec`) FIRST**
  * Command:
    ```bash
    pyinstaller manage.spec --clean
    ```
  * **Verification**: Confirm `dist/manage.exe` (or `dist/manage`) was created without build errors.

- [ ] **4.2. Stage 2 — Compile Desktop GUI Launcher (`IPOUtility.spec`) SECOND**
  * Command:
    ```bash
    pyinstaller IPOUtility.spec --clean
    ```
  * **Verification**: Confirm `dist/IPOUtility.exe` exists and has bundled `dist/manage.exe` (~300+ MB).

---

## Phase 5: Local QA Smoke Testing

Test `dist/IPOUtility.exe` locally prior to server deployment:

- [ ] **5.1. Test Existing User DB Migration & Backup**
  * Action: Place a test user database (e.g., version 2) next to `dist/IPOUtility.exe` and launch it.
  * **Verification**:
    * Pre-migration backup created in:
      * Windows: `%APPDATA%\IPOUtilityBackup\DB_Schema_Backups\`
      * Linux: `~/.IPOUtilityBackup/DB_Schema_Backups/`
    * `migration_log.txt` outputs `Return code: 0`.
    * User successfully logs in with past orders, clients, and accounting intact.

- [ ] **5.2. Test Clean Installation (Missing DB Fallback)**
  * Action: Delete or move `db.sqlite3` out of the test folder and launch.
  * **Verification**: Bundled template `db.sqlite3` is copied automatically and the app opens cleanly.

---

## Phase 6: Update Server Deployment (`http://46.202.162.106:8080`)

Deploy assets to the distribution server in this **strict chronological sequence**:

- [ ] **6.1. Upload `dist/IPOUtility.exe` (FIRST)**
  * Destination: `http://46.202.162.106:8080/IPOUtility.exe`
  * Action: Upload the binary and wait until the upload reaches 100%.

- [ ] **6.2. Upload Updated PEM Certificates (if any)**
  * Destination: `http://46.202.162.106:8080/pemfile/`
  * Action: Upload any updated registrar SSL `.pem` files.

- [ ] **6.3. Upload `latest_version.txt` (LAST — Triggers Client Updates)**
  * Destination: `http://46.202.162.106:8080/latest_version.txt`
  * Action: Upload the version file last.
  * *WARNING: Never upload this file first! Client apps poll this file on launch. Uploading it last guarantees clients only download a fully uploaded executable.*

---

## Phase 7: Live Post-Deployment Sanity Verification

- [ ] **7.1. Live Client Auto-Update Verification**
  * Action: Launch the application on a client computer running the older version.
  * **Verification**:
    * Update prompt displays: *"Version X.X.X is available. Update now?"*.
    * Click **Yes** and observe the progress bar downloads to 100%.
    * App replaces executable, restarts, executes database migrations silently, and loads the main dashboard.
