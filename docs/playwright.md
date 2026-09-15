# Playwright E2E tests

This project keeps its existing **Python Playwright + Django StaticLiveServerTestCase** architecture. There is no second Node Playwright installation or playwright.config.ts. The two original tests remain in home/test_e2e.py. Additional suites use the same live server, browser engine and database lifecycle.

## Run

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/run_e2e.py
.\.venv\Scripts\python.exe scripts/run_e2e.py --headed
.\.venv\Scripts\python.exe scripts/run_e2e.py --report
```

The last command prints the local HTML report URL. Open test-results/report.html in a browser. This is the Python runner's report, not the Node Playwright HTML reporter.

On Linux/macOS, or with the virtual environment activated, use `python` instead of the explicit Windows interpreter path. npm wrappers are optional and require that the intended Python virtual environment is activated:

```text
npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:report
```

Run one independently seeded test or module:

```powershell
.\.venv\Scripts\python.exe scripts/run_e2e.py e2e.tests.Workflows.test_whatsapp_buy_ui_uses_supplied_number
.\.venv\Scripts\python.exe scripts/run_e2e.py e2e.api_tests.Contracts
```

Inspect a retained failure trace:

```powershell
.\.venv\Scripts\python.exe -m playwright show-trace "test-results/<test-id>/trace.zip"
```

Do not invoke these browser suites with ordinary development settings or `--keepdb`. Do not run `migrate`, `flush`, seed scripts, or runserver against the development database to prepare these tests.

## Isolation and lifecycle

1. scripts/run_e2e.py allocates a unique tmp/playwright-e2e-<random>/ directory.
2. The launcher sets PLAYWRIGHT_TEST=1, E2E_RUN_DIR, and DJANGO_SETTINGS_MODULE=userproject.e2e_settings. It runs Django from that temporary working directory, isolating relative export/upload files as well as media.
3. e2e_settings replaces both DATABASES.default.NAME and TEST.NAME with the **same temporary file** named playwright-e2e.sqlite3. Its path must resolve to the launcher's unique directory directly under this project's tmp/. No development database connection is needed.
4. SafeRunner checks both names again before Django creates the schema or runs migrations. It rejects keepdb and parallel workers. Django applies the project's actual migrations to the temporary file.
5. StaticLiveServerTestCase starts a server on an OS-assigned local port, in a thread in the test process. Browser and request tests use that server's actual URL. No pre-existing server or authentication session is reused.
6. Django flushes only the temporary test database between tests. Each test seeds its own users and entities. Primary keys need not restart at one; tests use the IDs returned by fixtures.
7. Django stops the live server and destroys the temporary database. The launcher removes only the specific directory it allocated, in a finally block. Media and relative exports are removed with it.

Both db.sqlite3 and old-db.sqlite3 remain outside the E2E directory. Tests do not open, seed, migrate, copy, reset or modify them. BASE_URL and arbitrary E2E_DB_PATH overrides are not accepted. Only one worker mutates a database. Separate launcher invocations use separate database files, but reports share test-results, so run the reporting suite sequentially.

The original setup used Django's default SQLite test database (shared in-memory in the same process). That was viable for its threaded server. The explicit file improves auditability and avoids relying on shared-memory SQLite behavior.

## Fixtures, CSRF and integrations

e2e/seed.py creates broker, customer, second-owner broker, admin, inactive, expired and unassigned users. Their password is `test-password-123`, exclusively in the temporary database. The fixture graph includes Mainboard/SME IPOs, owned/foreign groups, a client, an order with PAN detail, a payment, and live/expired shared links. Test phone: **7016868618**; WhatsApp normalization is asserted as **917016868618**.

Fixtures are created by the ORM before Playwright starts. Request tests use a separate worker thread for later ORM assertions and close its database connections. No global DJANGO_ALLOW_ASYNC_UNSAFE bypass is used.

Django CSRF middleware remains enabled. Browser forms use their generated tokens; Playwright request helpers obtain the real CSRF cookie. Tests deliberately omit the token only when verifying rejection. Existing application csrf_exempt decorators are not changed.

The test runner denies server socket connections outside loopback. This catches requests, SMTP, aiohttp and Telegram outbound connections. WhatsApp tests mock the provider boundary and verify the real payload; they do not send messages. Django email uses locmem and WhatsApp credentials are fake. Browser requests to local Django are allowed; external data requests/form navigations are blocked, while public GET static libraries/fonts/images are permitted because templates depend on CDN assets. Therefore these tests are not fully offline.

Do not replace a provider mock with a real account or allow an external hostname in the server guard. Registrar CAPTCHA/allotment, real Telegram OTP/session creation, real SMTP and production payment actions are not live-tested.

## Structure and coverage

- home/test_e2e.py: preserved client-creation and Mainboard IPO/eight-card workflows.
- e2e/tests.py: authentication, group/client workflows, CSV, profile, accounting payment, guest links and WhatsApp browser flow.
- e2e/pages_tests.py: additional deep links and refresh checks, admin CRUD, customer creation, password change, IPO edit and rate save.
- e2e/api_tests.py: request-level validation, ownership, accounting audit, atomic payments, bulk deletion, PAN calculations, order updates, shared links, WhatsApp contracts and source-generated anonymous route checks.
- e2e/runtime_tests.py: explicit regressions for observed JavaScript failures. These remain ordinary failing tests, not skipped/expected failures.
- e2e/browser.py, e2e/seed.py: shared fixtures, request helpers and failure artifacts.
- e2e/runner.py, userproject/e2e_settings.py, scripts/run_e2e.py: guarded database lifecycle, external network boundary and reporting.
- e2e/inventory.py: AST-derived application route metadata, template controls and recursive Django resolver inventory.

See playwright-routes.md and the JSON inventories for routes, names, namespaces, parameters, decorators, templates, redirects, inputs, buttons, links and AJAX references. See playwright-coverage.md for the per-route matrix and explicit functional gaps. A route marked TESTED may have only an anonymous-response check; it does not imply every form, role or branch is covered.

When adding a test, seed state independently, use returned IDs, use semantic locators or stable names/IDs, and assert a visible outcome or persistence. Never depend on another test's writes. Add a dedicated browser journey when testing user interaction; keep pure endpoint contracts in api_tests. Add controlled provider fixtures before exercising integrations. Use locator assertions, URL waits or response waits rather than sleeps.

Known runtime errors are captured in browser-errors.json. Two exact signatures are separated from functional journeys and asserted without an allowlist in runtime_tests, allowing other business-flow checks to continue. Any other browser exception or local HTTP 5xx fails a browser test. Full traces/videos/screenshots are retained for failures; successful runs retain the small error log only.

## CI and troubleshooting

.github/workflows/playwright.yml installs Python dependencies and Chromium, runs the same isolated launcher, and uploads artifacts even if tests fail. Node is unnecessary. All home/migrations/*.py must be included in the checkout; the repository previously ignored some existing migrations, so .gitignore now exposes them for version control. CI was configured locally; a hosted Actions run was not performed.

For SQLite locks, first verify that only the current launcher uses its unique directory. Do not flush or delete a development database. Stop the specific interrupted E2E process, then remove only its verified tmp/playwright-e2e-<random>/ directory if an OS termination prevented finally cleanup. Never remove tmp wholesale: it contains unrelated files.

A missing browser error requires `python -m playwright install chromium` using the same Python environment. A missing table in CI usually means migrations were omitted from the checkout. Missing frontend controls can indicate CDN availability or a real JavaScript error; inspect trace.zip, failure.png, failure.html and browser-errors.json before changing selectors. Do not disable CSRF or suppress an application exception to make a test pass.

Ordinary Ctrl+C and test failures go through launcher cleanup. Forced OS termination or power loss cannot guarantee finally cleanup. An explicit safe directory check guards normal deletion.
