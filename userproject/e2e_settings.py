"""Only the E2E launcher may activate these settings."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403

run_dir = Path(os.environ.get('E2E_RUN_DIR', '')).resolve()
tmp_root = (Path(BASE_DIR) / 'tmp').resolve()
if (os.environ.get('PLAYWRIGHT_TEST') != '1' or run_dir.parent != tmp_root
        or not run_dir.name.startswith('playwright-e2e-') or not run_dir.is_dir()):
    raise ImproperlyConfigured('Use python scripts/run_e2e.py; a unique E2E directory is required.')
db_path = run_dir / 'playwright-e2e.sqlite3'
E2E_RUN_DIR = str(run_dir)
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
    'NAME': str(db_path), 'TEST': {'NAME': str(db_path)}, 'OPTIONS': {'timeout': 30}}}
MEDIA_ROOT = str(run_dir / 'media')
STATIC_ROOT = str(run_dir / 'static')
Path(STATIC_ROOT).mkdir(exist_ok=True)
Path(MEDIA_ROOT).mkdir(exist_ok=True)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SECRET_KEY = 'e2e-only-not-a-deployment-secret'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
TEST_RUNNER = 'e2e.runner.SafeRunner'
