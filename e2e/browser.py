import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright


class BrowserCase(StaticLiveServerTestCase):
    """One browser context and flushed temporary DB per test; real CSRF remains on."""
    @classmethod
    def setUpClass(cls):
        if settings.SETTINGS_MODULE != 'userproject.e2e_settings':
            raise RuntimeError('Run browser tests using python scripts/run_e2e.py')
        super().setUpClass()

    def start_browser(self):
        self.playwright = self.browser = self.context = self.page = None
        self.errors = []
        self.artifacts = Path(settings.BASE_DIR) / 'test-results' / self.id()
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.finalize_artifacts)
        self.addCleanup(self.stop_browser)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=os.environ.get('SHOW_BROWSER') != '1')
        self.context = self.browser.new_context(record_video_dir=str(self.artifacts),
            viewport={'width': 1440, 'height': 1000})
        self.context.set_default_timeout(10000)
        self.context.route('**/*', self.route_network)
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('response', lambda response: self.errors.append(f'HTTP {response.status}: {response.url}')
                     if response.status >= 500 and urlsplit(response.url).hostname in ('localhost', '127.0.0.1') else None)

    def route_network(self, route):
        url = urlsplit(route.request.url)
        if url.hostname in ('localhost', '127.0.0.1'):
            route.continue_()
        elif route.request.method == 'GET' and route.request.resource_type in ('script', 'stylesheet', 'font', 'image'):
            # Public static libraries only; no external fetch/XHR/forms or messages.
            route.continue_()
        else:
            route.abort()

    def stop_browser(self):
        try:
            if self.context is not None:
                try:
                    result = self._outcome.result if self._outcome else None
                    failed = bool(result and any(t is self for t, _ in result.failures + result.errors))
                    if failed and self.page and not self.page.is_closed():
                        self.page.screenshot(path=str(self.artifacts / 'failure.png'), full_page=True)
                        (self.artifacts / 'failure.html').write_text(self.page.content(), encoding='utf-8')
                    self.context.tracing.stop(path=str(self.artifacts / 'trace.zip'))
                    (self.artifacts / 'browser-errors.json').write_text(json.dumps(self.errors, indent=2), encoding='utf-8')
                finally:
                    self.context.close()
                    self.context = None
        finally:
            try:
                if self.browser is not None:
                    self.browser.close()
                    self.browser = None
            finally:
                if self.playwright is not None:
                    self.playwright.stop()
                    self.playwright = None

    def finalize_artifacts(self):
        result = self._outcome.result if self._outcome else None
        failed = bool(result and any(t is self for t, _ in result.failures + result.errors))
        if not failed:
            for path in self.artifacts.iterdir():
                if path.suffix in ('.webm', '.zip', '.png', '.html'):
                    path.unlink()

    def tearDown(self):
        # Known runtime defects are separately asserted in RuntimeHealth. New errors fail here.
        known = ("Cannot read properties of null (reading 'addEventListener')", 'node.getAttribute is not a function')
        unexpected = [e for e in self.errors if e not in known]
        self.assertEqual(unexpected, [], 'Unexpected browser/server errors; see browser-errors.json')

    def navigate(self, path):
        response = self.page.goto(self.live_server_url + path, wait_until='domcontentloaded')
        self.assertLess(response.status, 500, path)
        return response

    def login(self, username='e2e-broker', password='test-password-123'):
        self.navigate('/login')
        self.page.get_by_placeholder('User Name', exact=True).fill(username)
        self.page.get_by_placeholder('Password', exact=True).fill(password)
        self.page.get_by_role('button', name='Login', exact=True).click()

    def post(self, path, data=None, json_data=None, csrf=True):
        token = next((c['value'] for c in self.context.cookies() if c['name'] == 'csrftoken'), '')
        headers = {'X-CSRFToken': token} if csrf else {}
        if json_data is not None:
            return self.context.request.post(self.live_server_url + path, data=json_data,
                headers=headers, max_redirects=0)
        return self.context.request.post(self.live_server_url + path, form=data or {},
            headers=headers, max_redirects=0)
