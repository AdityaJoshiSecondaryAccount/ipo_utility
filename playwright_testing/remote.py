"""Remote-only Playwright support. No Django imports or database access."""
import argparse
from datetime import datetime, timezone
import getpass
import html
import json
import os
from pathlib import Path
import time
import unittest
import uuid
from urllib.parse import urlsplit

TARGET = 'https://testapp.ipoutility.in'
RESULTS = Path(__file__).resolve().parent / 'results'


def arguments(parser=None):
    parser = parser or argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=TARGET, choices=[TARGET, TARGET + '/'])
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--slow-mo', type=int, default=0)
    parser.add_argument('--ipo-id', default=os.environ.get('IPO_TEST_IPO_ID'))
    return parser


def credentials():
    # username = os.environ.get('IPO_TEST_USERNAME')
    # password = os.environ.get('IPO_TEST_PASSWORD')
    username = "Broker"
    password = "Bro@1234"
    if not username:
        username = input('Test-site username: ').strip()
    if not password:
        password = getpass.getpass('Test-site password: ')
    if not username or not password or username.startswith('[INSERT_') or password.startswith('[INSERT_'):
        raise ValueError('Real test-site credentials are required.')
    return username, password


def require_ipo(args):
    if not args.ipo_id or not str(args.ipo_id).isdigit() or int(args.ipo_id) <= 0:
        raise ValueError('Set --ipo-id or IPO_TEST_IPO_ID to the IPO ID on the test site.')


class RemoteCase(unittest.TestCase):
    config = None
    account = None

    def setUp(self):
        from playwright.sync_api import sync_playwright, expect
        self.artifacts = RESULTS / 'artifacts' / (self.id().replace('.', '_') + '-' + uuid.uuid4().hex[:12])
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.browser = self.pw.chromium.launch(headless=not self.config.headed, slow_mo=self.config.slow_mo)
        self.addCleanup(self.browser.close)
        self.context = self.browser.new_context(viewport={'width': 1600, 'height': 1000},
                                               record_video_dir=str(self.artifacts), service_workers="allow")
        self.addCleanup(self.context.close)
        self.context.route('**/*', self.guard)
        self.page = self.context.new_page()
        expect.set_options(timeout=15000)
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(60000)
        self.browser_errors = []
        self.page.on('pageerror', lambda error: self.browser_errors.append(
            f'{self.page.url}\n{error.stack or str(error)}'))
        self.page.on('response', lambda response: self.browser_errors.append(f'HTTP {response.status}: {response.url}')
                     if response.status >= 500 and urlsplit(response.url).netloc == urlsplit(TARGET).netloc else None)
        self.addCleanup(self.capture)
        self.live_server_url = TARGET  # Retained name for the existing calculation locator helpers.
        self.navigate('/login')
        self.page.get_by_placeholder('User Name', exact=True).fill(self.account[0])
        field = self.page.get_by_placeholder('Password', exact=True)
        field.fill(self.account[1])
        field.press('Enter')
        self.page.wait_for_url(lambda url: urlsplit(str(url)).path.rstrip('/') != '/login')
        self.assertEqual(urlsplit(self.page.url).netloc, urlsplit(TARGET).netloc)

    def guard(self, route):
        url = urlsplit(route.request.url)
        # Other origins can supply passive assets only, never application requests.
        allowed = (url.scheme == 'https' and url.netloc == urlsplit(TARGET).netloc)
        static = (url.scheme == 'https' and route.request.method == 'GET' and
                  route.request.resource_type in ('stylesheet', 'script', 'image', 'font') and
                  url.hostname not in ('localhost', '127.0.0.1', '::1') and not url.hostname.endswith('.localhost'))
        route.continue_() if allowed or static else route.abort('blockedbyclient')

    def navigate(self, path):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Only paths on the configured test domain are permitted')
        response = self.page.goto(TARGET + path, wait_until='load')
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200, f'{path}: HTTP {response.status}')
        if path not in ('/login', '/logout'):
            self.assertNotEqual(urlsplit(self.page.url).path.rstrip('/'), '/login', 'Session expired or access denied')
        return response

    def capture(self):
        if not self.page.is_closed():
            self.page.screenshot(path=str(self.artifacts / 'page.png'), full_page=True)
        (self.artifacts / 'browser-errors.json').write_text(json.dumps(self.browser_errors, indent=2))

    def tearDown(self):
        self.assertFalse(self.browser_errors, '\n'.join(self.browser_errors))


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def record(self, test, status, detail=''):
        if status in ('failed', 'error') and hasattr(test, 'page') and not test.page.is_closed():
            try:
                test.page.screenshot(path=str(test.artifacts / f'failure-{len(self.records)}.png'), full_page=True)
            except Exception as exc:
                detail += f'\nScreenshot unavailable: {exc}'
        self.records.append(dict(id=test.id(), status=status, detail=detail,
                                 duration_seconds=round(time.monotonic() - self.started.get(test.id(), time.monotonic()), 3),
                                 artifacts=str(test.artifacts.relative_to(RESULTS)) if hasattr(test, 'artifacts') else None))

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failed', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error', self._exc_info_to_string(err, test))


    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped', reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.record(test, 'failed', str(subtest) + '\n' + self._exc_info_to_string(err, test))


def report():
    """One report with both suites, individual checks, and click-to-open media."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    esc = lambda value: html.escape(str(value))
    body = ['<h1>Playwright test report</h1>', f'<p>Target: {TARGET}</p>']
    for filename, title in [('results.json', 'E2E'), ('calculation-run.json', 'Calculation')]:
        path = RESULTS / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        body.append(f'<h2>{title}: {"PASSED" if data["passed"] else "FAILED"}</h2><p>{esc(data["time"])} · {data["tests"]} tests</p>')
        for record in data['records']:
            artifact = RESULTS / (record.get('artifacts') or 'no-artifacts')
            body.append(f'<details><summary>{esc(record["status"].upper())} — {esc(record["id"])} ({record.get("duration_seconds", 0)}s)</summary><pre>{esc(record["detail"])}</pre>')
            for media in sorted(artifact.glob('*')):
                if media.suffix not in ('.png', '.webm'):
                    continue
                relative = media.relative_to(RESULTS).as_posix()
                body.append(f'<button data-src="{esc(relative)}" data-video="{str(media.suffix == ".webm").lower()}" onclick="showMedia(this)">Open {esc(media.name)}</button>')
            body.append('</details>')
    path = RESULTS / 'calculation-reference-comparison.json'
    if path.exists():
        data = json.loads(path.read_text())
        body.append('<h2>Calculation measurements</h2><table><tr><th>Check</th><th>Expected</th><th>UI</th><th>Status</th></tr>')
        for check in data.get('oracle_checks', []) + data.get('checks', []):
            body.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in
                        (check['label'], check['expected'], check['ui_text'], 'PASS' if check['passed'] else 'FAIL')) + '</tr>')
        body.append('</table>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Playwright report</title>
<style>body{font:15px system-ui;background:#101827;color:#edf3fa;max-width:1300px;margin:32px auto;padding:20px}details{background:#1e293b;padding:16px;margin:10px 0;border-radius:10px}summary,button{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #526077;text-align:left}dialog{max-width:90vw;background:#101827;color:white}dialog img,dialog video{max-width:85vw;max-height:80vh}button{padding:8px;margin:5px}</style>'''
    document += ''.join(body) + '''<dialog id="media"><button onclick="document.getElementById('media').close()">Close</button><div id="content"></div></dialog>
<script>function showMedia(b){const c=document.getElementById('content');c.replaceChildren();const e=document.createElement(b.dataset.video==='true'?'video':'img');e.src=b.dataset.src;if(e.tagName==='VIDEO')e.controls=true;c.append(e);document.getElementById('media').showModal()}document.getElementById('media').addEventListener('close',()=>document.getElementById('content').replaceChildren());</script></html>'''
    (RESULTS / 'report.html').write_text(document, encoding='utf-8')
    print(f'Report: {RESULTS / "report.html"}', flush=True)


def run(factory, args, name):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / ('results.json' if name == 'e2e' else 'calculation-run.json')
    data = dict(time=datetime.now(timezone.utc).isoformat(), passed=False, tests=0, records=[])
    try:
        account = credentials()
        require_ipo(args)
        case = factory(args)
        case.config, case.account = args, account
        result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromTestCase(case))
        data.update(passed=result.wasSuccessful(), tests=result.testsRun, records=result.records)
        return 0 if result.wasSuccessful() else 1
    except (Exception, KeyboardInterrupt) as exc:
        data['records'].append(dict(id=f'{name}.setup', status='error', detail=str(exc)))
        print(f'{name} could not complete: {exc}', flush=True)
        return 1
    finally:
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        report()
