#!/usr/bin/env python3
"""Interactive remote-only Playwright launcher."""
import os
from pathlib import Path
import subprocess
import sys
from playwright_testing.remote import TARGET, RESULTS, credentials, report

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
TEST_PYTHON = str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable


def choose(title, options):
    print('\n' + title)
    for key, label in options.items():
        print(f'  {key}. {label}')
    while True:
        answer = input('Select an option: ').strip()
        if answer in options:
            return answer
        print('Choose ' + ', '.join(options))


def main():
    print(f'Test environment: {TARGET}')
    suite = choose('Which tests?', {'1': 'E2E', '2': 'Calculation', '3': 'All'})
    headed = choose('Show the browser window?', {'1': 'Yes', '2': 'No'}) == '1'
    modules = 'import playwright.sync_api' + ('; import openpyxl' if suite in ('2', '3') else '')
    check = subprocess.run([TEST_PYTHON, '-c', modules], capture_output=True, text=True)
    if check.returncode:
        print(f'Testing Python: {TEST_PYTHON}')
        print(check.stderr.strip())
        print(f'Install dependencies with: "{TEST_PYTHON}" -m pip install playwright openpyxl')
        print(f'Then install Chromium: "{TEST_PYTHON}" -m playwright install chromium')
        return 2
    print(f'Testing Python: {TEST_PYTHON}')
    username, password = credentials()
    ipo = os.environ.get('IPO_TEST_IPO_ID') or input('Remote IPO ID (DEEPA JEWELLERS for calculations): ').strip()
    if not ipo.isdigit() or int(ipo) <= 0:
        print('IPO ID must be a positive integer.')
        return 2
    env = dict(os.environ, IPO_TEST_USERNAME=username, IPO_TEST_PASSWORD=password, IPO_TEST_IPO_ID=ipo)
    RESULTS.mkdir(parents=True, exist_ok=True)
    # These three generated summaries belong to the previous menu run.
    # Media uses separate run folders and remains available for investigation.
    for filename in ('results.json', 'calculation-run.json', 'calculation-reference-comparison.json'):
        (RESULTS / filename).unlink(missing_ok=True)
    seed_mode = 'existing'
    if suite in ('2', '3'):
        choice = choose('Calculation data setup?', {
            '1': 'Insert/resume all 840 orders through Buy/Sell UI, load allotments, then verify',
            '2': 'Verify existing remote data only',
        })
        seed_mode = 'ui' if choice == '1' else 'existing'
    commands = []
    if suite in ('1', '3'):
        commands.append(ROOT / 'playwright_testing/run_e2e.py')
    if suite in ('2', '3'):
        print(f'Calculation setup: {seed_mode}. Target: {TARGET}; IPO: {ipo}')
        commands.append(ROOT / 'playwright_testing/calculation/verify_calculations.py')
    codes = []
    try:
        for script in commands:
            command = [TEST_PYTHON, str(script), '--ipo-id', ipo]
            if script.name == 'verify_calculations.py':
                command.extend(['--seed-mode', seed_mode])
            if headed:
                command.append('--headed')
            codes.append(subprocess.run(command, cwd=ROOT, env=env).returncode)
    finally:
        report()
    return 1 if any(codes) else 0


if __name__ == '__main__':
    raise SystemExit(main())
