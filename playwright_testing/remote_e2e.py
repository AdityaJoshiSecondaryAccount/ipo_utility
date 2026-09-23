"""Browser-only workflows against an existing IPO on the test deployment."""
import re
import uuid
from .remote import RemoteCase


def make_case(args):
    from playwright.sync_api import expect

    class RemoteE2E(RemoteCase):
        def test_session_refresh_logout(self):
            self.navigate('/')
            self.page.reload()
            expect(self.page.get_by_role('heading', name='Current IPOs')).to_be_visible()
            self.navigate('/logout')
            self.page.goto(self.live_server_url + '/GroupSetup')
            expect(self.page).to_have_url(re.compile(r'/login/?$'))

        def test_group_create_edit_cancel_delete(self):
            # Delete only the uniquely named record created by this test.
            name = 'PW ' + uuid.uuid4().hex[:12].upper()
            self.navigate('/GroupSetup')
            # Server pagination hides new records in an already populated account.
            # This preference belongs to this test's isolated login session.
            page_size = self.page.locator('#Gp_page_size')
            if page_size.input_value() != 'All':
                with self.page.expect_navigation(wait_until='load'):
                    page_size.select_option('All')
            expect(page_size).to_have_value('All')
            self.page.locator('[data-bs-target="#ADDGROUP"]').click()
            modal = self.page.locator('#ADDGROUP')
            modal.locator('[name="GroupName"]').fill(name)
            modal.locator('[name="MobileNo"]').fill('9999999999')
            with self.page.expect_navigation(wait_until='load'):
                modal.get_by_role('button', name='Submit Form').click()
            # Verify persistent data, not a transient toast whose markup can change.
            row = self.page.get_by_role('row').filter(has=self.page.get_by_role('cell', name=name, exact=True))
            expect(row, 'Created group missing; server messages: ' + ' | '.join(
                self.page.locator('[role=alert]').all_text_contents())).to_have_count(1)
            row.get_by_role('button', name='Edit', exact=True).click()
            self.page.locator('[name="Address"]').fill('Playwright remote verification')
            with self.page.expect_navigation(wait_until='load'):
                self.page.locator('form').get_by_role('button', name=re.compile('Update|Submit|Save')).click()
            self.page.reload()
            expect(row).to_contain_text('Playwright remote verification')
            row.get_by_role('button', name='Delete', exact=True).click()
            self.page.locator('.modal:visible').get_by_role('button', name='Cancel', exact=True).click()
            expect(self.page.locator('.modal:visible')).to_have_count(0)
            expect(row).to_be_visible()
            row.get_by_role('button', name='Delete', exact=True).click()
            with self.page.expect_navigation(wait_until='load'):
                self.page.locator('.modal:visible').get_by_role('button', name='Delete', exact=True).click()
            expect(row).to_have_count(0)
            self.page.reload()
            expect(row).to_have_count(0)

    routes = {
        'ipo_list': ('/IPOSETUP', 'IPO'),
        'groups': ('/GroupSetup', 'Group'),
        'clients': ('/ClientSetup', 'Client'),
        'group_positions': ('/group-billing-details/', 'Positions'),
        'buy': (f'/{args.ipo_id}/BUY', 'BUY'),
        'sell': (f'/{args.ipo_id}/SELL', 'SELL'),
        'orders': (f'/{args.ipo_id}/Order', 'Order'),
        'buy_details': (f'/{args.ipo_id}/OrderDetail/BUY', 'Order Detail'),
        'sell_details': (f'/{args.ipo_id}/OrderDetail/SELL', 'Order Detail'),
        'billing': (f'/{args.ipo_id}/Billing', 'Billing'),
        'status': (f'/{args.ipo_id}/Status', 'Group Wise Billing'),
    }

    def page_check(route, content):
        def test(self):
            self.navigate(route)
            expect(self.page.locator('body')).to_contain_text(content)
            self.page.reload()
            expect(self.page.locator('body')).to_contain_text(content)
            expect(self.page.locator('body')).not_to_contain_text('Traceback')
            for form in self.page.locator('form[method="post" i]').all():
                if form.is_visible():
                    expect(form.locator('[name="csrfmiddlewaretoken"]')).to_be_attached()
        return test

    for name, (route, content) in routes.items():
        setattr(RemoteE2E, 'test_page_' + name, page_check(route, content))
    return RemoteE2E
