"""Cross-platform, fail-closed launcher. Never opens a development database."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--headed', action='store_true')
parser.add_argument('--report', action='store_true')
LABELS = ['home.test_e2e', 'e2e.tests', 'e2e.pages_tests', 'e2e.api_tests', 'e2e.runtime_tests']
parser.add_argument('labels', nargs='*', default=LABELS)
args = parser.parse_args()
if args.report:
    print((ROOT / 'test-results' / 'report.html').as_uri())
    sys.exit(0)
(ROOT / 'tmp').mkdir(exist_ok=True)
run_dir = Path(tempfile.mkdtemp(prefix='playwright-e2e-', dir=ROOT / 'tmp')).resolve()
env = dict(os.environ, PLAYWRIGHT_TEST='1', E2E_RUN_DIR=str(run_dir),
           DJANGO_SETTINGS_MODULE='userproject.e2e_settings',
           SHOW_BROWSER='1' if args.headed else '0', E2E_PHONE='7016868618')
print(f'Isolated E2E database: {run_dir / "playwright-e2e.sqlite3"}', flush=True)
try:
    result = subprocess.run([sys.executable, str(ROOT / 'manage.py'), 'test',
        *(args.labels or LABELS), '--noinput', '--parallel=1', '-v', '2'],
        cwd=run_dir, env=env)
    code = result.returncode
finally:
    # Never remove anything except this launcher's freshly allocated directory.
    if run_dir.parent != (ROOT / 'tmp').resolve() or not run_dir.name.startswith('playwright-e2e-'):
        raise RuntimeError('Refusing unsafe cleanup')
    shutil.rmtree(run_dir)
sys.exit(code)
