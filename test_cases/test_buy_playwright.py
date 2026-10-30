"""BUY page E2E (/<IPOid>/BUY). Runs first in the pipeline; its data is kept for SELL and Orders."""
from test_cases.base import OrderPageFlow, PersistentLiveServerTestCase, pause_for_inspection


class BuyPagePlaywrightTestCase(OrderPageFlow, PersistentLiveServerTestCase):
    ORDER_TYPE = "BUY"
    PAGE_NAME = "buy"
    NEW_GROUP_NAME = "DELTA CAPITAL"
    RATE_SHIFT = 0

    def test_complete_buy_page_flow(self):
        self.run_order_page_flow()
        pause_for_inspection(self.PAGE_NAME)
