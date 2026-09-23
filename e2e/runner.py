import html
import ipaddress
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from django.conf import settings
from django.test.runner import DiscoverRunner


class ReportResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())
    def startTest(self, test):
        super().startTest(test)
        self.current = test.id()


class ReportTextRunner(unittest.TextTestRunner):
    resultclass = ReportResult


class SafeRunner(DiscoverRunner):
    test_runner = ReportTextRunner
    def setup_databases(self, **kwargs):
        db = settings.DATABASES['default']
        expected = Path(settings.E2E_RUN_DIR) / 'playwright-e2e.sqlite3'
        if (Path(db['NAME']).resolve() != expected or
                Path(db['TEST']['NAME']).resolve() != expected or self.keepdb or self.parallel > 1):
            raise RuntimeError('Unsafe E2E database configuration')
        return super().setup_databases(**kwargs)

    def run_tests(self, *args, **kwargs):
        from .inventory import write_coverage, write_resolved_inventory, append_framework_coverage
        write_coverage()
        append_framework_coverage(write_resolved_inventory())
        original = socket.socket.connect
        def local_only(sock, address):
            if isinstance(address, tuple):
                try:
                    local = ipaddress.ip_address(address[0]).is_loopback
                except ValueError:
                    local = address[0] == 'localhost'
                if not local:
                    raise RuntimeError(f'E2E blocked external connection to {address[0]}')
            return original(sock, address)
        # Covers requests, SMTP, aiohttp and Telegram; explicit mocks take precedence.
        with patch('socket.socket.connect', local_only):
            return super().run_tests(*args, **kwargs)

    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        out = Path(settings.BASE_DIR) / 'test-results'
        out.mkdir(exist_ok=True)
        failures = [(t.id(), trace) for t, trace in result.failures + result.errors]
        summary = {'tests': result.testsRun, 'passed': result.testsRun - len(failures) - len(result.skipped),
                   'failed': len(failures), 'skipped': len(result.skipped), 'failures': failures,
                   'passed_ids': result.passed_ids,
                   'skipped_details': [(str(t), reason) for t, reason in result.skipped]}
        (out / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        (out / 'report.html').write_text('<!doctype html><meta charset="utf-8"><title>E2E report</title>'
            '<h1>Playwright E2E results</h1><pre>' + html.escape(json.dumps(summary, indent=2)) + '</pre>', encoding='utf-8')
        return result
