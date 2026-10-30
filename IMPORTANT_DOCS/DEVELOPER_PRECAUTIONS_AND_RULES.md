# Developer Precautions & Engineering Rules

This document outlines the essential engineering rules, precautions, and architectural constraints that every developer must adhere to when modifying, adding features to, or compiling **IPO Utility Desktop**.

---

## 1. Architectural Context

IPO Utility operates in a **hybrid desktop/web environment**:
* **Desktop Application (`IS_EXE = True`)**: Standalone, frozen PyInstaller package with local AES-256 SQLCipher encryption, USB hardware locking, desktop PyWebView UI, and automated auto-updater.
* **Centralized Web Server (`IS_WEB = True`)**: Standard Django web server hosted in the cloud connecting to a centralized MySQL database.

Because of this dual architecture, **writing code without following these rules will cause executable crashes, user database lockouts, or failed updates on client PCs.**

---

## 2. Database & Migration Precautions (Top Priority)

### Rule 2.1: Always Increment `LOCAL_DB_VERSION` in `Setup.py`
Whenever you alter a model in `home/models.py` and generate a migration:
1. Open `Setup.py` (around line 71).
2. Increment `LOCAL_DB_VERSION` (e.g. from `2` &rarr; `3`).

> **Why this is critical:**  
> For instant performance, `Setup.py` compares the local user database's `schema_version` with `LOCAL_DB_VERSION`. If they match, `Setup.py` **skips migration execution entirely**.  
> If you create a new migration but forget to bump `LOCAL_DB_VERSION`, existing users will **never run the migration**, and the app will crash with `OperationalError: no such column / table`!

---

### Rule 2.2: The Baseline Migration (`0001_baseline.py`) is Immutable
* The 21 tangled historical migrations have been consolidated into `home/migrations/0001_baseline.py`.
* **NEVER modify or re-squash `0001_baseline.py`**.
* All future schema modifications must be created as standard sequential forward migrations:
  ```bash
  python manage.py makemigrations
  ```
  This creates clean, forward-only files (e.g., `0003_...`, `0004_...`).

---

### Rule 2.3: Always Update the Bundled `db.sqlite3` Before Compiling
Because `IPOUtility.spec` bundles `db.sqlite3` as the fallback template for new installations, you must apply the new migrations and stamp `schema_version` inside the bundled database before running PyInstaller:

```bash
# 1. Apply new migrations to template db.sqlite3
python manage.py migrate

# 2. Stamp new version into encrypted SQLCipher db.sqlite3
python -c "
from Setup import get_sqlcipher_connection, get_db_version

db_version_no = 3  # <-- Match your new LOCAL_DB_VERSION

conn = get_sqlcipher_connection('db.sqlite3')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER);')
cur.execute('UPDATE schema_version SET version = ? WHERE id = 1;', (db_version_no,))
conn.commit()
conn.close()
print(f'Encrypted db.sqlite3 stamped to schema_version: {get_db_version(\"db.sqlite3\")}')
"
```

---

### Rule 2.4: Use Callable Defaults in Models (Never Static Expressions)
When defining date/time defaults in `home/models.py`:
* **CORRECT**: Pass the callable function name:
  ```python
  def get_default_expiry_date():
      return (now() + timedelta(days=365)).date()

  class CustomUser(AbstractUser):
      Expiry_Date = models.DateField(default=get_default_expiry_date)
  ```
* **FATAL ERROR**: Calling the function or calculating directly:
  ```python
  # DO NOT DO THIS:
  Expiry_Date = models.DateField(default=now() + timedelta(days=365))
  ```
  *Why?* Static expressions evaluate once when Django boots. Django serializes that exact fixed timestamp into the migration file, causing broken migrations, timezone mismatch warnings, and Git merge conflicts.

---

## 3. PyInstaller Packaging Precautions

### Rule 3.1: Strict Two-Stage Build Order (`manage.spec` FIRST, then `IPOUtility.spec`)
The build process **MUST** follow this exact sequence:

```
 Step 1: pyinstaller manage.spec --clean      ──> Produces dist/manage.exe
                           │
                           ▼
 Step 2: pyinstaller IPOUtility.spec --clean  ──> Copies dist/manage.exe into dist/IPOUtility.exe
```

> **Why?**  
> `IPOUtility.spec` takes `dist/manage.exe` as an input binary dependency. If you build `IPOUtility.spec` first (or build them out of order), `IPOUtility.exe` will package an **old, stale version of `manage.exe`**, and your latest Python/Django code changes will not be included in the release!

---

### Rule 3.2: Register All New Pip Libraries in `hiddenimports`
PyInstaller parses imports via static analysis. However, Django views, database backends, and dynamic libraries are loaded at runtime through strings.
Whenever you add a new third-party Python library (e.g. `pandas`, `xlsxwriter`, `reportlab`, `qrcode`, `cryptography`):
1. Add it to `hiddenimports` in `manage.spec`.
2. If the library is also accessed by the launcher (`Setup.py`), add it to `hiddenimports` in `IPOUtility.spec`.

*Failure to do this will cause the compiled executable to immediately crash on client machines with `ModuleNotFoundError`.*

---

## 4. File System & Path Precautions (Frozen vs Development)

### Rule 4.1: Read-Only Bundled Files vs Writable Runtime Files
PyInstaller extracts bundled assets into a temporary directory at runtime (`sys._MEIPASS`).
* **Bundled Assets (Read-Only)**: Templates, icons, static CSS/JS, and baseline resources.
  * Access using: `resource_path("logo.png")` or `resource_path("templates/index.html")`.
  * **Never attempt to write or save changes to `resource_path()`**, as changes will be destroyed on application exit.
* **Persistent User Data (Writable)**: The database (`db.sqlite3`), PEM files, and backups.
  * Access using: `os.path.join(get_real_app_dir(), "db.sqlite3")` or `%APPDATA%\IPOUtilityBackup\`.

---

### Rule 4.2: Prevent SQLite File Locks
SQLite/SQLCipher only supports a single active writer at a time:
* When using direct database connections (outside Django ORM), always use `with conn:` or explicitly call `conn.close()`.
* Avoid leaving hanging transactions open, as this creates `-wal` (Write-Ahead Log) and `-shm` (Shared Memory) locks that prevent `Setup.py` from backing up or replacing the database.

---

## 5. Dual-Mode Code Compatibility (`IS_EXE` vs `IS_WEB`)

### Rule 5.1: Guard Desktop-Only Tasks in Views
Do not execute desktop-specific actions on the web server, and vice versa. Always check `settings.IS_EXE`:
```python
from django.conf import settings

# Example in home/views.py:
if getattr(settings, 'IS_EXE', False) and request.user.is_authenticated:
    trigger_background_db_upload(request.user.username)
```

### Rule 5.2: Conditional UI Elements in Templates
When designing HTML templates:
* Hide cloud-only web features from desktop users:
  ```html
  <div {% if IS_EXE %}style="display: none;"{% endif %}>
      <!-- Web-only button / subscription link -->
  </div>
  ```
* **Do NOT use Progressive Web App (PWA) tags** in templates (`{% load pwa %}` or `<link rel="manifest">`). Desktop WebKit/Edge WebView does not support service workers and will raise `TemplateSyntaxError`.

---

## 6. Authentication & 2FA Governance

### Rule 6.1: Admins Can ONLY Disable 2FA (Never Enable)
In `home/admin.py`:
* Enabling 2FA requires the end-user to scan a secret QR code with their mobile device (Google Authenticator / Authy) and submit a valid 6-digit TOTP token.
* **Admins must never be allowed to check `two_factor_enabled = True` in Django Admin.** If an admin forces 2FA on, the user will have no secret key on their phone and will be permanently locked out of their account.
* Django Admin includes strict form validation (`CustomUserChangeForm`) blocking admins from turning 2FA ON, while allowing them to turn 2FA OFF to rescue locked-out users.

### Rule 6.2: Always Sanitize Secrets When Disabling 2FA
When an admin disables 2FA for a user:
* `two_factor_enabled` &rarr; `False`
* `two_factor_secret` &rarr; `None`
* `backup_codes` &rarr; `[]`
* *Why?* This ensures that any compromised or lost authenticator secrets are permanently revoked. When the user enables 2FA again, Django generates a clean, secure new QR code.

---

## 7. Deployment Protocol: The `latest_version.txt` Rule

### Rule 7.1: Always Upload `latest_version.txt` Last
When deploying a release to the update server (`http://46.202.162.106:8080`):
1. **Upload `IPOUtility.exe` first**.
2. **Upload updated PEM certificates second**.
3. **Upload `latest_version.txt` LAST**.

> **The Reason:**  
> Client machines check `latest_version.txt` immediately on startup. If you upload `latest_version.txt` before `IPOUtility.exe` finishes transferring, client PCs will detect an available update and attempt to download an incomplete, corrupt, or half-uploaded binary file.

