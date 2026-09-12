"""Write a readable report from the most recent local test run."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'test-results' / 'results.json'
if not source.is_file():
    raise SystemExit('No results yet. Run .venv/bin/python scripts/run_e2e.py first.')
result = json.loads(source.read_text(encoding='utf-8'))
lines = [
    '# Local Playwright execution report', '',
    'Results for Ipoutility-production-ready, from test-results/results.json.',
    'Targeted runs overwrite the report too; these counts describe only the latest run.', '',
    '| Tests run | Passed | Failure/error records | Skipped |',
    '|---:|---:|---:|---:|',
    f"| {result['tests']} | {result['passed']} | {result['failed']} | {result['skipped']} |", '',
    'The suite excludes four source-project WhatsApp tests and its two WhatsApp route checks.',
    'Application code is not modified to make tests pass. Real external integrations are not tested.', '',
    '## Failures', '',
]
for test_id, trace in result['failures']:
    lines.extend([f'### {test_id}', '', '```text', trace.rstrip(), '```', ''])
if not result['failures']:
    lines.extend(['No failure/error records.', ''])
lines.extend([
    '## Artifacts and reruns', '',
    'Open test-results/report.html for the JSON summary. Browser failure directories',
    'retain screenshots, HTML, videos, traces, and browser-errors.json.', '',
    '```bash', '.venv/bin/python scripts/run_e2e.py',
    '.venv/bin/python scripts/run_e2e.py e2e.runtime_tests',
    '.venv/bin/python scripts/summarize_e2e.py', '```', '',
    'Route inventories and the coverage matrix are in docs/playwright-*.json and',
    'docs/playwright-coverage.md. Anonymous checks do not prove full workflow coverage.', '',
])
destination = ROOT / 'docs' / 'playwright-report.md'
destination.parent.mkdir(exist_ok=True)
destination.write_text('\n'.join(lines), encoding='utf-8')
print(f"{result['tests']} tests: {result['passed']} passed, {result['failed']} failure/error records, {result['skipped']} skipped")
print(destination)
