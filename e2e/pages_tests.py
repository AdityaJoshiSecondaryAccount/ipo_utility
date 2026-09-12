"""Deep-link, content, refresh and form checks for additional page families."""
import re
from playwright.sync_api import expect
from .browser import BrowserCase
from .seed import seed


PAGE_CASES = [
    ('ipo_list','/IPOSETUP','TEST IPO'),
    ('groups','/GroupSetup','TEST GROUP'),
    ('clients','/ClientSetup','TEST CLIENT'),
    ('ipo_edit','/edit/{ipo}','TEST IPO'),
    ('client_edit','/EditClient/{client}','TEST CLIENT'),
    ('group_edit','/EditGroup/{group}','TEST GROUP'),
    ('order_edit','/{ipo}/EditOrder/{order}/All/All/All','TEST GROUP'),
    ('rates','/{ipo}/SetRate','BUY'),
    ('group_dashboard','/GroupWiseDashboard','TEST GROUP'),
    ('group_positions','/group-billing-details/{group}/','Positions'),
    ('positions','/group-billing-details/','Positions'),
    ('backup','/BackUp','BACK UP'),
    ('accounting_logs','/accounting-logs/','Accounting Activity'),
    ('sme_analysis_a','/{sme}/Dashboard/A','Analysis'),
    ('sme_analysis_b','/{sme}/Dashboard/B','Analysis'),
    ('sme_analysis_c','/{sme}/Dashboard/C','Analysis'),
    ('analysis_b','/{ipo}/Dashboard/B','Analysis'),
    ('analysis_c','/{ipo}/Dashboard/C','Analysis'),
    ('sme_buy','/{sme}/BUY','BUY'),
    ('sme_sell','/{sme}/SELL','SELL'),
    ('sme_orders','/{sme}/Order','Order'),
    ('sme_pan_buy','/{sme}/OrderDetail/BUY','Order Detail'),
    ('sme_pan_sell','/{sme}/OrderDetail/SELL','Order Detail'),
    ('sme_billing','/{sme}/Billing','Billing'),
    ('sme_status','/{sme}/Status','Group Wise Billing'),
]


class Pages(BrowserCase):
    def setUp(self):
        seed(self)
        self.start_browser()
        self.login()
        self.page.wait_for_url(self.live_server_url+'/')

    def test_rates_save_and_reopen(self):
        self.navigate(f'/{self.ipo.pk}/SetRate')
        for field in ('KostakQTY','KostakRate','SubjectToQTY','SubjectToRate','PremiumQTY','PremiumRate',
                      'KostakSellQTY','KostakSellRate','SubjectToSellQTY','SubjectToSellRate','PremiumSellQTY','PremiumSellRate'):
            self.page.locator(f'[name="{field}"]').fill('10')
        self.page.get_by_role('button',name='Save',exact=True).click()
        self.page.wait_for_url(self.live_server_url+'/')
        self.navigate(f'/{self.ipo.pk}/SetRate')
        expect(self.page.locator('[name="KostakRate"]')).to_have_value(re.compile(r'^\s*10(?:\.0)?\s*$'))

    def test_ipo_edit_persists_price_and_name(self):
        self.navigate(f'/edit/{self.ipo.pk}')
        self.page.locator('[name="name"]').fill('EDITED IPO')
        self.page.locator('[name="IPOPrice"]').fill('175')
        self.page.locator('button[type="submit"]').click()
        expect(self.page.get_by_text('IPO Edit successfully.')).to_be_visible()
        self.navigate(f'/edit/{self.ipo.pk}')
        expect(self.page.locator('[name="name"]')).to_have_value('EDITED IPO')
        expect(self.page.locator('[name="IPOPrice"]')).to_have_value('175.0')

    def test_password_mismatch_then_change_and_relogin(self):
        self.navigate('/user-profile/')
        self.page.locator('#passwordConfigToggle').click()
        form=self.page.locator('#passwordConfigContent')
        form.locator('[name="NewPassword"]').fill('UpdatedPassword123!')
        form.locator('[name="ConfirmPassword"]').fill('WrongPassword123!')
        form.get_by_role('button',name=re.compile('Update|Change')).click()
        expect(self.page.get_by_text('New Password and Confirm Password is not equal')).to_be_visible()
        self.navigate('/user-profile/')
        self.page.locator('#passwordConfigToggle').click()
        form.locator('[name="NewPassword"]').fill('UpdatedPassword123!')
        form.locator('[name="ConfirmPassword"]').fill('UpdatedPassword123!')
        form.get_by_role('button',name=re.compile('Update|Change')).click()
        self.page.wait_for_url(self.live_server_url+'/ChangeUserpassword')
        self.navigate('/logout')
        self.login(password='UpdatedPassword123!')
        self.page.wait_for_url(self.live_server_url+'/')

    def test_admin_broker_denied_and_superuser_crud(self):
        self.navigate('/admin/')
        expect(self.page).to_have_url(re.compile('/admin/login/'))
        self.navigate('/logout')
        self.login('e2e-admin')
        self.navigate('/admin/home/groupdetail/add/')
        self.page.locator('#id_user').select_option(str(self.admin_user.pk))
        self.page.locator('#id_GroupName').fill('ADMIN GROUP')
        self.page.locator('#id_Collection').fill('0')
        self.page.locator('[name="_save"]').click()
        expect(self.page.get_by_text('was added successfully',exact=False)).to_be_visible()
        self.page.locator('#result_list').get_by_role('link',name='ADMIN GROUP',exact=True).click()
        self.page.locator('#id_Address').fill('Admin address')
        self.page.locator('[name="_save"]').click()
        expect(self.page.get_by_text('was changed successfully',exact=False)).to_be_visible()
        self.page.locator('#result_list').get_by_role('link',name='ADMIN GROUP',exact=True).click()
        self.page.get_by_role('link',name='Delete',exact=True).click()
        self.page.get_by_role('button',name="Yes, I’m sure").click()
        expect(self.page.get_by_text('was deleted successfully',exact=False)).to_be_visible()


def page_check(route, content):
    def test(self):
        path=route.format(ipo=self.ipo.pk,sme=self.sme.pk,group=self.group.pk,
                          client=self.client_record.pk,order=self.order.pk)
        response=self.navigate(path)
        self.assertEqual(response.status,200)
        # Content may be in an editable input; ensure the expected entity/heading is rendered.
        self.assertIn(content,self.page.content())
        expect(self.page.locator('body')).not_to_contain_text('Traceback')
        self.page.reload()
        self.assertIn(content,self.page.content())
        for form in self.page.locator('form[method="post"],form[method="POST"]').all():
            if form.is_visible():
                expect(form.locator('[name="csrfmiddlewaretoken"]')).to_be_attached()
    return test

for name,route,content in PAGE_CASES:
    setattr(Pages,'test_page_'+name,page_check(route,content))
