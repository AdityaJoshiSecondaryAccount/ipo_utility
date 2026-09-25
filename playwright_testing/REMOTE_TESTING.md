# Testing the remote deployment

Both supported entry points now target **https://testapp.ipoutility.in**.
They use standalone Playwright, without Django startup, migrations, ORM access,
a local HTTP server, or a temporary database. Other application origins are blocked.
The old Django-dependent test modules remain as source references; these launchers
never execute them. Chaos testing remains deferred.

## Interactive run

From the project directory, using a Python environment with `playwright` and
`openpyxl` installed and Playwright Chromium available:

```sh
python testing.py
```

Choose E2E, Calculation or All, then visible/headless browser. Enter the remote
account username, password (hidden terminal input), and remote IPO ID. Find the ID
in the site's URL, for example `/123/BUY` means ID `123`.
No credentials are committed to the repository. Use a dedicated test-site account.

First-time dependencies, if needed:

```sh
python -m pip install playwright openpyxl
python -m playwright install chromium
```

## Direct commands / automation

Set `IPO_TEST_USERNAME`, `IPO_TEST_PASSWORD`, and `IPO_TEST_IPO_ID` through your
terminal/CI secret environment. Without credentials the script prompts interactively.
Do not put passwords in command-line arguments.

```sh
python playwright_testing/run_e2e.py --headed --ipo-id 123
python playwright_testing/calculation/verify_calculations.py --headed --ipo-id 123
```

Omit `--headed` to run without a window. The only accepted `--base-url` is the test
domain. `--seed-mode ui` (the direct calculation command default) inserts/resumes orders and imports allotments.
`--seed-mode existing` only verifies. Local DB and ORM seed modes are not available.

## Coverage and data requirements

**E2E:** login/refresh/logout, group creation/edit/delete cancellation/deletion, and
11 authenticated page/refresh/CSRF checks covering setup, orders, buy/sell,
application details and billing. The group test only deletes its own randomly named
`PW ...` group. A failure before deletion can leave that group for investigation.
It never edits existing orders, IPO configuration, passwords or other user accounts.
The former local suite's direct ORM, superuser, synthetic account and mocked-service
checks are **not claimed as remote coverage**. The remote suite contains 13 tests.

**Calculation:** the menu now offers data setup or verification only. Setup creates
missing source groups, sets the selected DEEPA JEWELLERS IPO price to 177 and
pre-open price to 221, and submits **all 840 orders through Buy/Sell UI** using the
plain Place Order button. It then imports 9,114 PAN application records through
the authenticated CSV form endpoint and updates two blank-PAN application slots
through the normal allotment-edit endpoint. No Telegram, WhatsApp or email buttons
are used. PAN clients are created by the application's importer. This updates only
the selected IPO, but source groups and clients belong to the logged-in account;
use a dedicated test account because importing PANs can update client details.

Setup reads back and verifies every order (including duplicate source rows) and
all 9,116 application slots before running calculation assertions. The remaining
272 detail-export rows represent standalone Premium orders, not application slots.
No expected billing amounts are written to the server. The application calculates
them from prices, rates and allotments.

The persistent `results/seed-state/` journal is scoped to the account, IPO and
source fingerprint. An interrupted run resumes only if the entire remote order
multiset equals the exact source prefix already submitted. Unexpected rows,
changed datasets, partial/rejected submissions or a populated IPO without a matching
journal stop the process instead of blindly appending or deleting orders. Keep
this directory between runs. Concurrent seeding for the same IPO is blocked with
a process lock (Linux/macOS). A completed order setup is not inserted again.

The independent Decimal oracle verifies all 40 groups, main tables, Share modal
categories/options, and the client workbook's first 50-row page. The source contains
840 orders and 9,388 export detail rows. The client reference requires the same
page ordering as the original export. A rejected import or differing result is a
failure, never silently repaired with database writes or synthetic PANs.

## Results

After execution, open `playwright_testing/results/report.html`. This is the single
HTML report and is overwritten by the next run. Each suite's run timestamp is shown.
The menu clears previous summary JSON files, so “All” combines only its current runs.
Direct commands update their own suite; the other suite, if present, retains its
explicitly displayed timestamp. Individual mathematical comparisons and failure
tracebacks appear in the report. Screenshot/video buttons open a popup. Keep the
adjacent `artifacts/` folders with the report; media is linked, not embedded.
Recordings can contain account data; keep reports private. Credentials are not
written to report JSON. Artifact folders are unique per execution.

These remote workflows need real test-site credentials to execute. Source/syntax
inspection is not a live test pass.
