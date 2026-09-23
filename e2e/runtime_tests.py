"""Explicit regressions for observed application JavaScript defects; no expectedFailure."""
from playwright.sync_api import expect
from .browser import BrowserCase
from .seed import seed


class RuntimeHealth(BrowserCase):
    def setUp(self):
        seed(self)
        self.start_browser()
        self.login()
        self.page.wait_for_url(self.live_server_url + '/')
        self.errors.clear()

    def test_buy_has_no_javascript_errors(self):
        self.navigate(f'/{self.ipo.pk}/BUY')
        expect(self.page.locator('#btnPlaceOnly')).to_be_visible()
        self.assertEqual(self.errors, [])

    def test_order_detail_has_no_javascript_errors(self):
        self.navigate(f'/{self.ipo.pk}/OrderDetail/BUY')
        expect(self.page.locator('#category')).to_be_visible()
        self.assertEqual(self.errors, [])
