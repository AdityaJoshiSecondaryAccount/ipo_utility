"""SELL page E2E (/<IPOid>/SELL). Runs on the same IPO / groups / broker the BUY test left behind."""
from test_cases.base import OrderPageFlow, PersistentLiveServerTestCase, pause_for_inspection


class SellPagePlaywrightTestCase(OrderPageFlow, PersistentLiveServerTestCase):
    ORDER_TYPE = "SELL"
    PAGE_NAME = "sell"
    NEW_GROUP_NAME = "SIGMA CAPITAL"
    RATE_SHIFT = 5   # SELL rates are BUY rates + 5, so the two are easy to tell apart

    def test_complete_sell_page_flow(self):
        self.run_order_page_flow()
        pause_for_inspection(self.PAGE_NAME)
