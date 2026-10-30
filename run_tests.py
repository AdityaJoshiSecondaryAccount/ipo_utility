#!/usr/bin/env python
"""
Master runner for the Playwright E2E suite.

    python run_tests.py                 # BUY -> SELL -> Orders, in one run
    python run_tests.py buy             # only the BUY page
    python run_tests.py sell orders     # any subset; always executed in pipeline order
    python run_tests.py --headless      # no visible window, no pause at the end
    python run_tests.py --failfast      # stop at the first failing page

All selected pages run inside ONE `manage.py test` process, which is what lets
them share a single test database and a single browser window: BUY's data is
still there for SELL, and BUY + SELL data is still there for the Orders page.
The browser stays open after the last page until you press Enter.

To add a page, create test_cases/test_<page>_playwright.py and append
"<page>" to PIPELINE below.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Pipeline order matters: later pages reuse the data earlier ones created.
PIPELINE = ["buy", "sell", "orders", "order_detail", "billing", "status", "groupwise", "accounting", "positions", "trades",
            "ipo_setup", "client_setup", "group_setup", "backup"]


def main():
    parser = argparse.ArgumentParser(description="Run the Playwright E2E test pipeline.")
    parser.add_argument("pages", nargs="*", choices=PIPELINE, metavar="page",
                        help=f"pages to run ({', '.join(PIPELINE)}); default: all, in order")
    parser.add_argument("--headless", action="store_true", help="run without a visible browser")
    parser.add_argument("--no-pause", action="store_true", help="don't wait for Enter at the end")
    parser.add_argument("--failfast", action="store_true", help="stop at the first failure")
    args = parser.parse_args()

    selected = [p for p in PIPELINE if not args.pages or p in args.pages]
    labels = [f"test_cases.test_{p}_playwright" for p in selected]

    env = os.environ.copy()
    env["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    env.setdefault("DB_ENGINE", "sqlite")   # never create a test DB on the remote MySQL server
    env["PW_LAST_PAGE"] = selected[-1]      # only the last page keeps the browser open
    if args.headless:
        env["PW_HEADLESS"] = "1"
    if args.no_pause:
        env["PW_NO_PAUSE"] = "1"

    cmd = [sys.executable, "manage.py", "test", *labels, "-v", "0"]
    if args.failfast:
        cmd.append("--failfast")

    print(f"Running pipeline: {' -> '.join(selected)}\n", flush=True)
    sys.exit(subprocess.call(cmd, cwd=ROOT, env=env))


if __name__ == "__main__":
    main()
