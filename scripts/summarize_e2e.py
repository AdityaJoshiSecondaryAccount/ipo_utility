"""Write the reviewable coverage/results report from actual runner output."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
result=json.loads((ROOT/'test-results/results.json').read_text(encoding='utf-8'))
routes=json.loads((ROOT/'docs/playwright-routes.json').read_text(encoding='utf-8'))
resolved=json.loads((ROOT/'docs/playwright-resolved-routes.json').read_text(encoding='utf-8'))
first_path=ROOT/'test-results/full-run-1.json'
first=json.loads(first_path.read_text(encoding='utf-8')) if first_path.exists() else None
failure_ids={f[0] for f in result['failures']}
lines=['# Playwright E2E execution report','',
       '**This suite is not a claim of exhaustive functional coverage.** Every route is accounted for, but many action routes have anonymous-response coverage only. Detailed remaining gaps are in playwright-coverage.md.', '',
       '## Actual execution','',
       '| Tests run | Passed | Failed | Skipped |', '|---:|---:|---:|---:|',
       f"| {result['tests']} | {result['passed']} | {result['failed']} | {result['skipped']} |",'']
if first:
    same={f[0] for f in first['failures']} == failure_ids
    lines += [f"Previous complete run: {first['tests']} tests, {first['passed']} passed, {first['failed']} failed, {first['skipped']} skipped.",
              f"The two complete runs have {'the same' if same else 'different'} failing test IDs.",'']
lines += ['Failures remain ordinary failing tests. None is hidden with skip or expectedFailure. Test/environment bugs found during development were corrected; application views/templates were not changed.', '',
          '## Inventories and test files','',
          f'- {len(routes)} application route declarations and {len(resolved)} recursively resolved URLs including admin/PWA. See playwright-routes.md, playwright-routes.json and playwright-resolved-routes.json.',
          '- playwright-interactions.json inventories forms, field constraints, buttons, links and AJAX references in 38 template files.',
          '- playwright-coverage.md maps every route to checks, scope and exclusions.',
          '- Preserved and hardened: home/test_e2e.py (two original browser tests).',
          '- Added tests: e2e/tests.py, e2e/pages_tests.py, e2e/api_tests.py, e2e/runtime_tests.py.',
          '- Added helpers: e2e/browser.py, e2e/seed.py, e2e/inventory.py, e2e/runner.py.',
          '- Added infrastructure: scripts/run_e2e.py, userproject/e2e_settings.py, package.json, .env.e2e.example and .github/workflows/playwright.yml.',
          '- Existing ignored home migrations 0008–0011 were exposed by .gitignore for CI inclusion; their contents were not authored or modified for this task.', '',
          '## Database and fixture strategy','',
          'Each invocation uses tmp/playwright-e2e-<random>/playwright-e2e.sqlite3. Both NAME and TEST.NAME resolve to that same file. The runner uses one worker and verifies the path before database creation/migration. It runs from the temporary directory, isolates media/relative exports, closes Django and browsers, and removes the directory in finally cleanup.', '',
          'No development database was migrated, flushed, seeded, reset or modified. Broker/customer/admin/other-owner/inactive/expired fixtures are created afresh per test. Temporary users use test-password-123. Phone fixtures use 7016868618; WhatsApp payload tests assert 917016868618. Provider calls are simulated; no real WhatsApp or email was sent.', '',
          '## Application regressions reproduced','',
          '| Failing test | Route / observation |', '|---|---|']
for test,trace in result['failures']:
    match=re.search(r'test_(\d{3})_',test)
    if match:
        r=routes[int(match[1])]
        observation=f"`{r['route']}` — anonymous request returned HTTP 500 instead of a controlled response"
    elif 'customer_create' in test:
        observation='Customer dashboard cards omit IPO names: indexforCustomer supplies zip tuples while index.html expects IPO objects.'
    elif 'backup' in test:
        observation='Backup page-size POST form is malformed (unclosed style quote), loses its CSRF input and targets ClientSetup.'
    elif 'pan_allotted' in test:
        observation='PAN-allotted page raises JavaScript ReferenceError: b is not defined.'
    elif 'order_detail_has_no' in test:
        observation='Order-detail page raises JavaScript TypeError: node.getAttribute is not a function.'
    else:
        observation=next((x for x in reversed(trace.splitlines()) if 'Error' in x or 'Assertion' in x),'See HTML report/trace')
    lines.append('| `'+test+'` | '+observation.replace('|','\\|')+' |')
lines += ['', 'HTTP 500 findings are error-handling/access-contract defects; they are not by themselves proof of unauthorized data disclosure. Empty-rate and explicit invalid-method JSON responses are asserted according to the actual implementation rather than mislabeled as access failures.', '',
          '## Features not fully exercised','',
          '- Live registrar CAPTCHA/allotment services, Telegram sessions/OTP and SMTP delivery: excluded to prevent real external actions; WhatsApp has a simulated provider contract.',
          '- Exhaustive multi-group transfers, every export format/upload parser, all order category boundaries and all table filtering/pagination combinations: additional functional tests remain necessary.',
          '- Admin: representative group CRUD/authorization is covered; not every registered model field and admin operation.',
          '- Browser compatibility: Chromium only. CI configuration was created but hosted CI was not executed.',
          '- Static CDN resources are still network dependencies. Non-static external browser calls and external server sockets are blocked.', '',
          '## Exact commands','',
          'Full suite (Windows, repository root):','',
          '```powershell',r'.\.venv\Scripts\python.exe scripts/run_e2e.py','```','',
          'Headed:','', '```powershell',r'.\.venv\Scripts\python.exe scripts/run_e2e.py --headed','```','',
          'Print the report URL to open:','', '```powershell',r'.\.venv\Scripts\python.exe scripts/run_e2e.py --report','```','',
          'Report file: test-results/report.html. For npm wrappers, activate the Python virtual environment and use npm run test:e2e, npm run test:e2e:headed or npm run test:e2e:report.', '',
          'Playwright traces: python -m playwright show-trace "test-results/<test-id>/trace.zip". Installation, CI and troubleshooting details are in playwright.md.']
(ROOT/'docs/playwright-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f"{result['tests']} tests: {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped")
