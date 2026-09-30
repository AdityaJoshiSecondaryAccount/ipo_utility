# Playwright E2E execution report

**This suite is not a claim of exhaustive functional coverage.** Every route is accounted for, but many action routes have anonymous-response coverage only. Detailed remaining gaps are in playwright-coverage.md.

## Actual execution

| Tests run | Passed | Failed | Skipped |
|---:|---:|---:|---:|
| 196 | 169 | 27 | 0 |

Failures remain ordinary failing tests. None is hidden with skip or expectedFailure. Test/environment bugs found during development were corrected; application views/templates were not changed.

## Inventories and test files

- 136 application route declarations and 198 recursively resolved URLs including admin/PWA. See playwright-routes.md, playwright-routes.json and playwright-resolved-routes.json.
- playwright-interactions.json inventories forms, field constraints, buttons, links and AJAX references in 38 template files.
- playwright-coverage.md maps every route to checks, scope and exclusions.
- Preserved and hardened: home/test_e2e.py (two original browser tests).
- Added tests: e2e/tests.py, e2e/pages_tests.py, e2e/api_tests.py, e2e/runtime_tests.py.
- Added helpers: e2e/browser.py, e2e/seed.py, e2e/inventory.py, e2e/runner.py.
- Added infrastructure: scripts/run_e2e.py, userproject/e2e_settings.py, package.json, .env.e2e.example and .github/workflows/playwright.yml.
- Existing ignored home migrations 0008–0011 were exposed by .gitignore for CI inclusion; their contents were not authored or modified for this task.

## Database and fixture strategy

Each invocation uses tmp/playwright-e2e-<random>/playwright-e2e.sqlite3. Both NAME and TEST.NAME resolve to that same file. The runner uses one worker and verifies the path before database creation/migration. It runs from the temporary directory, isolates media/relative exports, closes Django and browsers, and removes the directory in finally cleanup.

No development database was migrated, flushed, seeded, reset or modified. Broker/customer/admin/other-owner/inactive/expired fixtures are created afresh per test. Temporary users use test-password-123. Phone fixtures use 7016868618; WhatsApp payload tests assert 917016868618. Provider calls are simulated; no real WhatsApp or email was sent.

## Application regressions reproduced

| Failing test | Route / observation |
|---|---|
| `e2e.tests.Workflows.test_accounting_journal_payment_persists` | AssertionError: Lists differ: ["Cannot set properties of null (setting 'disabled')"] != [] |
| `e2e.pages_tests.Pages.test_customer_create_through_form` | Customer dashboard cards omit IPO names: indexforCustomer supplies zip tuples while index.html expects IPO objects. |
| `e2e.pages_tests.Pages.test_page_backup` | Backup page-size POST form is malformed (unclosed style quote), loses its CSRF input and targets ClientSetup. |
| `e2e.pages_tests.Pages.test_page_pan_allotted` | PAN-allotted page raises JavaScript ReferenceError: b is not defined. |
| `e2e.pages_tests.Pages.test_page_sme_status` | AssertionError: Lists differ: ["Cannot set properties of null (setting '[59 chars]d')"] != [] |
| `e2e.api_tests.AnonymousRoutes.test_002_Update_pann` | `/<str:IPOid>/<str:OrderType>/update_pann/<str:GrpName>/<str:OrderCategory>/<str:InvestorType>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_005_get_options` | `/get-options/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_043_EditOrder` | `/<str:IPOid>/EditOrder/<str:OrderId>/<str:Grpf>/<str:OrCtf>/<str:InTyf>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_057_FileterBilling` | `/<str:IPOid>/Billing/<str:group>/<str:IPOType>/<str:InvestType>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_058_FileterBilling` | `/<str:IPOid>/Billing/<str:group>/<str:IPOType>/<str:InvestType>/<str:Rate>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_060_exportGroupwise` | `/download-Groupwise` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_061_Sempale_Order` | `/<str:IPOid>/Sempale-Order` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_062_exportBillingFilterpdf` | `/<str:IPOid>/download-Billing-Pdf/<str:group>/<str:IPOType>/<str:InvestorType>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_064_AllIpoBackup` | `/AllIpoBackup` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_080_BackUp` | `/BackUp` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_084_Order_upload` | `/<str:IPOid>/upload-csv/<str:Groupfilter>/<str:Ordercatagoryfilter>/<str:InvestorTypefilter>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_090_get_accounting_entries` | `/get-accounting-entries/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_102_AccountingBackup` | `/AccountingBackup/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_103_Share_AppDetails` | `/share-records/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_106_send_telegram_otp` | `/send-telegram-otp/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_107_verify_telegram_otp` | `/verify-telegram-otp/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_117_get_all_groups` | `/<int:IPOid>/get-all-groups/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_120_generate_shared_link` | `/generate-shared-link/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_123_get_user_links` | `/get-user-links/<int:IPOid>/<str:order_type>` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_128_send_all_link_mails` | `/send-all-link-mails/<int:IPOid>/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.api_tests.AnonymousRoutes.test_129_bulk_generate_links` | `/bulk-generate-links/<str:IPOid>/` — anonymous request returned HTTP 500 instead of a controlled response |
| `e2e.runtime_tests.RuntimeHealth.test_order_detail_has_no_javascript_errors` | Order-detail page raises JavaScript TypeError: node.getAttribute is not a function. |

HTTP 500 findings are error-handling/access-contract defects; they are not by themselves proof of unauthorized data disclosure. Empty-rate and explicit invalid-method JSON responses are asserted according to the actual implementation rather than mislabeled as access failures.

## Features not fully exercised

- Live registrar CAPTCHA/allotment services, Telegram sessions/OTP and SMTP delivery: excluded to prevent real external actions; WhatsApp has a simulated provider contract.
- Exhaustive multi-group transfers, every export format/upload parser, all order category boundaries and all table filtering/pagination combinations: additional functional tests remain necessary.
- Admin: representative group CRUD/authorization is covered; not every registered model field and admin operation.
- Browser compatibility: Chromium only. CI configuration was created but hosted CI was not executed.
- Static CDN resources are still network dependencies. Non-static external browser calls and external server sockets are blocked.

## Exact commands

Full suite (Windows, repository root):

```powershell
.\.venv\Scripts\python.exe scripts/run_e2e.py
```

Headed:

```powershell
.\.venv\Scripts\python.exe scripts/run_e2e.py --headed
```

Print the report URL to open:

```powershell
.\.venv\Scripts\python.exe scripts/run_e2e.py --report
```

Report file: test-results/report.html. For npm wrappers, activate the Python virtual environment and use npm run test:e2e, npm run test:e2e:headed or npm run test:e2e:report.

Playwright traces: python -m playwright show-trace "test-results/<test-id>/trace.zip". Installation, CI and troubleshooting details are in playwright.md.
