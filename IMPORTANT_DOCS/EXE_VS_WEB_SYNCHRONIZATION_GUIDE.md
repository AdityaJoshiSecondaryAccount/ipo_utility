# EXE vs Web VPS: File Classification & Synchronization Guide

This guide establishes the strict operational boundaries and file classification rules between the **Desktop EXE Application** and the **Web VPS Production Application**.

Whenever you update files on the VPS server or in the desktop repository, consult this document to know:
1. Which files belong **strictly to the Web VPS**.
2. Which files belong **strictly to the Desktop EXE**.
3. Which files are **Common/Shared**, and the exact precautions required before synchronizing them.

---

## 1. Golden Classification Matrix

| Category | Definition | Deployment Rule |
|---|---|---|
| **Category A: Web VPS Only** | Server configuration, WSGI adapters, PWA manifests, and server-side testing suites. | **DO NOT** package into PyInstaller / Desktop EXE. |
| **Category B: Desktop EXE Only** | PyInstaller build specs, USB dongle encryption keys, updater scripts (`Setup.py`), SQLCipher backend, and Windows binaries. | **NEVER** upload or deploy to the VPS server. |
| **Category C: Common / Shared** | Django core business logic (`models.py`, `views.py`, `urls.py`, `admin.py`, templates, static assets, and SSL certificates). | **MUST BE COMPATIBLE** with both environments using the `IS_EXE` / `IS_WEB` execution flag. |

---

## 2. Comprehensive File Catalog by Category

### Category A: Web VPS Only (Never Package into EXE)

These files exist specifically to run, serve, or verify the web application on cloud infrastructure (Linux VPS / cPanel / Passenger / Gunicorn / Nginx):

| Path / File | Purpose on VPS | Why Excluded from EXE |
|---|---|---|
| `passenger_wsgi.py` | Entry point for cPanel / Phusion Passenger server. | Desktop uses local PyWebView / waitress / local HTTP server. |
| `Procfile` | Gunicorn process launcher for PaaS / container deployments. | Desktop runs as an independent Windows executable (`.exe`). |
| `runtime.txt` | Defines cloud Python environment (`python-3.9.12`). | Desktop runtime is embedded inside the PyInstaller bundle. |
| `staticfiles.json` | WhiteNoise static assets manifest for cache busting. | Desktop serves static files directly from local disk. |
| `playwright_testing/` | Automated E2E verification test suite and benchmark fixtures. | Testing harness not required in end-user installation. |
| `package.json` | Node packages for frontend build or headless browser tests. | Desktop dependencies are Python-only. |
| `uploads/` | Server file uploads, historical view snapshots, and changelogs. | User data and media directory on VPS server. |

---

### Category B: Desktop EXE Only (Never Deploy to VPS)

These files must remain strictly within the local build machine / Desktop distribution:

| Path / File | Purpose in Desktop EXE | Why Excluded from Web VPS |
|---|---|---|
| `Setup.py` | Desktop installer, auto-updater, and SQLite migration manager. | VPS uses Git/CI-CD deployments and standard Django migrations. |
| `IPOUtility.spec` | PyInstaller packaging specification for the main GUI app. | VPS does not run PyInstaller executables. |
| `manage.spec` | PyInstaller packaging specification for the CLI utility. | VPS uses standard `python manage.py` directly. |
| `userproject/db_backend/` | Custom SQLite database engine enforcing SQLCipher AES-256 encryption. | Web VPS uses MySQL (`pymysql`) or standard relational database. |
| `sys_usb.json` | Hardware dongle serial bindings for offline license checks. | Web application uses web login authentication and DB sessions. |
| `RSA.py` | Hardware key validation routines for USB encryption. | Web server authentication uses standard Django password hashers. |
| `pem_files.json` | Manifest of certificate files for installer bundling. | Web VPS has certificates placed directly in `pemfile/`. |
| `wkhtmltoimage.exe`, `wkhtmltox.dll`, `wkhtmltopdf.exe` | Windows native binaries for image/PDF conversion. | Web VPS is a Linux server (requires Linux `wkhtmltox` package). |
| `latest_version.txt` | Version indicator queried by desktop auto-updater. | Web version is governed by the server code deployment. |
| `EXE_Instructions.md` | Internal release notes and packaging instructions. | Build artifact documentation. |

---

### Category C: Common / Shared Files (Shared Across Both)

These files contain the operational business logic and UI shared between both platforms. Any edit to these files must preserve dual compatibility:

| Path / File | Shared Purpose | Compatibility Status |
|---|---|---|
| `userproject/settings.py` | Global Django configuration. | **HIGH CAUTION**: Contains conditional blocks for DB, PWA, WhiteNoise, and Hosts. |
| `userproject/urls.py` | Top-level routing. | **SAFE**: Routes to admin and `home.urls`. |
| `userproject/wsgi.py` | Standard WSGI application interface. | **SAFE**: Standard Django WSGI callable. |
| `home/models.py` | ORM database schema definitions. | **STRICT PARITY**: Schema must remain identical on both platforms. |
| `home/admin.py` | Django admin customization and 2FA reset actions. | **CAUTION**: Check conditional admin registrations (`RateList`). |
| `home/views.py` | Business logic, calculations, and scrapers. | **CAUTION**: Guard any desktop-only triggers with `if settings.IS_EXE:`. |
| `home/urls.py` | Application endpoints. | **SAFE**: Routes must match on both platforms. |
| `home/migrations/` | Database schema migrations. | **EXTREME CAUTION**: Do NOT overwrite VPS migrations with Desktop migrations! |
| `templates/` | HTML templates and modals. | **CAUTION**: Guard Web-only components (PWA banners) with `{% if IS_WEB %}`. |
| `static/` | CSS, JS, fonts, and images. | **SAFE**: Static assets can be copied directly; run `collectstatic` on VPS. |
| `pemfile/` | SSL certificates for registrar scrapers. | **SAFE**: Certificates are identical on both platforms. |
| `requirements.txt` | Python library dependencies. | **CAUTION**: Environment-specific packages differ (see Section 3.7). |

---

## 3. Detailed Guide for Common / Shared Files

### 3.1. `userproject/settings.py`

`settings.py` is the central brain of the project. It uses the `IS_EXE` flag to automatically adapt between Desktop and Web modes:

```python
# Execution mode detection
IS_EXE = getattr(sys, 'frozen', False) or os.getenv('IS_EXE', '').strip().lower() in ('true', '1')
IS_WEB = not IS_EXE
```

#### Key Differences Handled Conditionally:
1. **Database Backend**:
   - **Desktop (`IS_EXE = True`)**:
     Uses `userproject.db_backend` connecting to encrypted local `db.sqlite3` with password `'Devam123321!'`.
   - **Web VPS (`IS_WEB = True`)**:
     Connects to MySQL database (`46.202.162.106:3306`, user `hostingerdb`) via `pymysql` (or local SQLite fallback).
2. **Static Asset Serving**:
   - **Desktop**: Django serves local static files directly.
   - **Web VPS**: Uses `whitenoise.middleware.WhiteNoiseMiddleware` and `CompressedManifestStaticFilesStorage`.
3. **PWA (Progressive Web App)**:
   - **Desktop**: PWA is not loaded (`pwa` is excluded from `INSTALLED_APPS`).
   - **Web VPS**: `pwa` is appended to `INSTALLED_APPS` and configured with manifest and icons.
4. **Security & Trusted Origins**:
   - **Desktop**: `CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1", "http://localhost"]`.
   - **Web VPS**: `CSRF_TRUSTED_ORIGINS = ["https://ipoutility.in", "https://www.ipoutility.in"]`.
5. **Context Processor**:
   Both environments register `userproject.settings.app_mode_processor` so every template has access to `IS_EXE` and `IS_WEB`.

> [!WARNING]
> When uploading `userproject/settings.py` to the VPS:
> - Never hardcode `IS_EXE = True` on the VPS.
> - Ensure MySQL connection credentials remain valid.
> - Ensure `DEBUG = False` and `ALLOWED_HOSTS` includes production domains on the live web server.

---

### 3.2. `home/admin.py`

`home/admin.py` controls the Django Admin portal.

#### Golden Rules for `admin.py`:
1. **2FA Safety Rules**:
   - The `CustomUserChangeForm` enforces that administrators can **only turn OFF 2FA** to recover locked-out users. Admins can never force-enable 2FA manually (users must scan their own TOTP QR code).
   - This rule applies equally to both Web VPS and Desktop.
2. **Conditional Model Registrations**:
   - In some deployments, certain models are only managed via admin on the web platform:
     ```python
     if settings.IS_WEB:
         admin.site.register(RateList)
     ```
   - Do not remove this conditional check unless you intend to register `RateList` across all platforms.

---

### 3.3. `home/models.py`

`home/models.py` defines the database tables.

#### Golden Rules for `models.py`:
1. **Strict Parity**:
   The Python model definitions in `home/models.py` **must remain 100% identical** in both the Desktop repository and the Web VPS repository.
2. **No Backend-Specific Types**:
   Never use database-specific field types that only work on MySQL or only on SQLite. Always use standard Django ORM fields (`models.CharField`, `models.IntegerField`, `models.JSONField`, `models.DateTimeField`).
3. **Default Values**:
   Any new field added to an existing model must specify either `null=True, blank=True` or a sensible `default=...` so existing rows on both SQLite and MySQL do not trigger integrity errors during migration.

---

### 3.4. `home/migrations/` (Database Migrations)

> [!CAUTION]
> **DO NOT blindly copy the `home/migrations/` folder between Desktop and Web VPS!**

Why Desktop and Web migrations differ:
- **Desktop EXE**:
  Historical migrations (0001 through 0021) were squashed into a clean baseline:
  - `0001_baseline.py`
  - `0002_add_2fa_ratelist_sharedlink.py`
  Desktop updates track schema changes via the `schema_version` table in SQLite managed by `Setup.py`.
- **Web VPS**:
  The live MySQL database on the VPS has an existing `django_migrations` table tracking chronological migrations:
  - `0001_initial.py` through `0014_...` (or higher).

#### Procedure for Schema Changes on VPS:
1. Make the field change in `home/models.py`.
2. On the VPS (or in the web staging environment), run:
   ```bash
   python manage.py makemigrations home
   python manage.py migrate
   ```
3. Commit that specific migration file to the web codebase.

---

### 3.5. `home/views.py`

`home/views.py` contains all request handling, calculation logic, and registrar scraping routines.

#### Rules for Views:
1. **Desktop Background Uploads**:
   The desktop application triggers an automated SQLite database backup to the cloud server upon certain actions:
   ```python
   if getattr(settings, 'IS_EXE', False) and request.user and request.user.is_authenticated:
       trigger_background_db_upload(request.user.username)
   ```
   This guard **must never be removed**. On the Web VPS, `IS_EXE` is `False`, ensuring the server never attempts to upload its own database.
2. **File Paths**:
   Never hardcode Windows drive letters (`C:\...`) or absolute Linux paths (`/home/admin/...`) inside view functions. Always resolve paths relative to `settings.BASE_DIR`:
   ```python
   cert_path = os.path.join(settings.BASE_DIR, 'pemfile', 'kfintech.pem')
   ```
3. **External Binaries**:
   If a view generates PDF or images using `imgkit` or `wkhtmltopdf`, ensure it checks the operating system or environment before invoking Windows binaries (`wkhtmltoimage.exe`).

---

### 3.6. `templates/` & HTML Files

The template files are shared between Desktop and Web, with UI adaptations controlled by template variables.

#### Rules for Templates:
1. **PWA Elements**:
   PWA tags and install banners must only render when running on the web server:
   ```html
   {% if IS_WEB %}
   <link rel="manifest" href="/manifest.json">
   <meta name="theme-color" content="#f0a500">
   <link rel="apple-touch-icon" href="{% static 'image/pwa_icon_192.png' %}">
   {% endif %}
   ```
   Do not use the raw `{% load pwa %}` tag at the top of templates unless `pwa` is installed in both environments; using standard `<link rel="manifest">` guarded by `{% if IS_WEB %}` is safe everywhere.
2. **Desktop-Hidden UI Elements**:
   Certain buttons or sections (e.g., cloud sync controls or web-only links) can be hidden on desktop:
   ```html
   <button class="btn btn-secondary" {% if IS_EXE %}style="display: none;"{% endif %}>
       Web Only Action
   </button>
   ```
3. **URL Routing**:
   Always use Django's `{% url 'route_name' %}` syntax instead of hardcoding absolute domains or local host URLs.

---

### 3.7. `requirements.txt` Dependencies

While both environments share core libraries (Django, REST framework, pandas, openpyxl, reportlab, pyotp, qrcode, ddddocr, beautifulsoup4), their platform-specific packages differ:

| Package | Desktop EXE | Web VPS | Purpose |
|---|---|---|---|
| `sqlcipher3` | **Required** | Not used | Encrypted SQLite backend |
| `pywebview` | **Required** | Not used | Desktop GUI window wrapper |
| `pyinstaller` | **Required** | Not used | Building the standalone executable |
| `pymysql` / `mysqlclient` | Optional (fallback) | **Required** | Production MySQL database connection |
| `gunicorn` | Not used | **Required** | Production WSGI HTTP server |
| `whitenoise` | Not used | **Required** | Serving compressed static files |
| `django-pwa` | Not used | **Required** | PWA manifest and service worker |

---

### 3.8. `pemfile/` (SSL Registrar Certificates)

All registrar `.pem` certificates (`kfintech.pem`, `_.bigshareonline.pem`, `integrated.pem`, `purvashare.pem`, `maashitla.pem`, `cambridge.pem`, `skylinerta.pem`, `my_trust_store.pem`) are **identical** across both platforms.

- When a registrar updates their SSL certificate, the new `.pem` file must be updated in **both** `ipo-exe/pemfile/` and `Ipoutility-production-ready/pemfile/`.

---

## 4. VPS Safe Deployment Checklist

Before uploading or pulling files to the Web VPS, run through this checklist:

- [ ] **1. File Classification Verified**: Ensure no desktop-only files (`Setup.py`, `*.spec`, `*.exe`, `sys_usb.json`) are uploaded to the VPS.
- [ ] **2. Execution Mode Preserved**: Ensure `IS_EXE` evaluates to `False` on the VPS.
- [ ] **3. Database Settings Untouched**: Verify `settings.DATABASES` connects to MySQL on the VPS and is not overwritten with local SQLCipher settings.
- [ ] **4. Migrations Handled Correctly**: Never overwrite the VPS `home/migrations/` folder with squashed desktop migration files. Run `makemigrations` and `migrate` on the VPS independently if models changed.
- [ ] **5. Static Assets Collected**: After updating CSS/JS/images, run `python manage.py collectstatic --noinput` on the VPS.
- [ ] **6. Web Service Reloaded**: Restart the production WSGI server (e.g., `touch passenger_wsgi.py` or `sudo systemctl restart gunicorn`).
- [ ] **7. Verification Test**: Open `https://ipoutility.in` and verify login, dashboard loading, and registrar allotment status checks.
