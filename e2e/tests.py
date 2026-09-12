import json
import re
import uuid
from unittest.mock import patch
import requests
from django.utils import timezone
from playwright.sync_api import expect
from home.models import Accounting, ClientDetail, GroupDetail, CurrentIpoName, Order, SharedLink
from .browser import BrowserCase
from .seed import seed, PHONE


class Workflows(BrowserCase):
    def setUp(self):
        seed(self)
        self.start_browser()

    def signed_in(self):
        self.login()
        self.page.wait_for_url(self.live_server_url + '/')

    def test_login_refresh_logout_protects_deep_link(self):
        self.signed_in()
        expect(self.page.get_by_role('heading', name='Current IPOs')).to_be_visible()
        self.page.reload()
        expect(self.page.get_by_text('TEST IPO', exact=True)).to_be_visible()
        self.navigate('/logout')
        self.navigate('/ClientSetup')
        expect(self.page).to_have_url(self.live_server_url + '/login')
        self.page.go_back()
        self.navigate('/GroupSetup')
        expect(self.page).to_have_url(self.live_server_url + '/login')

    def test_login_required_fields(self):
        self.navigate('/login')
        self.page.get_by_role('button', name='Login').click()
        self.assertFalse(self.page.locator('form').evaluate('(f) => f.checkValidity()'))
        expect(self.page).to_have_url(self.live_server_url + '/login')

    def test_customer_cannot_access_broker_setup(self):
        self.login('e2e-customer')
        self.page.wait_for_url(self.live_server_url + '/indexforCustomer')
        self.navigate('/GroupSetup')
        expect(self.page.get_by_text('You are not authorized to view this page')).to_be_visible()
        expect(self.page.locator('form[action="AddGroup"]')).to_have_count(0)

    def test_login_csrf_rejected(self):
        self.navigate('/login')
        response = self.post('/login', {'username':'e2e-broker','password':'test-password-123'}, csrf=False)
        self.assertEqual(response.status, 403)

    def test_group_create_duplicate_edit_delete_cancel(self):
        self.signed_in()
        self.navigate('/GroupSetup')
        self.page.locator('[data-bs-target="#ADDGROUP"]').click()
        form = self.page.locator('#ADDGROUP')
        form.locator('[name="GroupName"]').fill('NEW GROUP')
        form.locator('[name="MobileNo"]').fill(PHONE)
        form.get_by_role('button', name='Submit Form').click()
        expect(self.page.get_by_text('Group Added successfully.')).to_be_visible()
        response = self.post('/AddGroup', {'GroupName':'NEW GROUP', 'MobileNo':PHONE})
        self.assertEqual(response.status, 302)
        self.navigate('/GroupSetup')
        expect(self.page.get_by_text('Group Already Exist.')).to_be_visible()
        row = self.page.get_by_role('row').filter(has=self.page.get_by_role('cell', name='NEW GROUP', exact=True))
        row.get_by_role('button', name='Edit', exact=True).click()
        self.page.locator('[name="Address"]').fill('E2E address')
        self.page.locator('form').get_by_role('button', name=re.compile('Update|Submit|Save')).click()
        expect(self.page.get_by_role('cell', name='E2E address', exact=True)).to_be_visible()
        row.get_by_role('button', name='Delete', exact=True).click()
        self.page.locator('.modal:visible').get_by_role('button', name='Cancel', exact=True).click()
        expect(row).to_be_visible()
        row.get_by_role('button', name='Delete', exact=True).click()
        self.page.locator('.modal:visible').get_by_role('button', name='Delete', exact=True).click()
        expect(self.page.get_by_role('cell', name='NEW GROUP', exact=True)).to_have_count(0)

    def test_group_bulk_csv_upload_and_sample_download(self):
        self.signed_in()
        self.navigate('/GroupSetup')
        self.page.locator('#bulk_upload_btn').click()
        with self.page.expect_download() as download:
            self.page.get_by_role('link', name='Download Sample CSV').click()
        self.assertTrue(download.value.suggested_filename)
        form = self.page.locator('.modal:visible')
        form.locator('input[type="file"]').set_input_files({'name':'groups.csv', 'mimeType':'text/csv',
            'buffer':f'GroupName,MobileNo,Email,Address,Remark\nCSV GROUP,{PHONE},csv@example.test,Test,Upload\n'.encode()})
        form.get_by_role('button', name='Upload', exact=True).click()
        expect(self.page.get_by_role('cell', name='CSV GROUP', exact=True)).to_be_visible()

    def test_client_edit_duplicate_and_filter(self):
        self.signed_in()
        self.navigate(f'/EditClient/{self.client_record.pk}')
        self.page.locator('[name="Name"]').fill('EDITED CLIENT')
        self.page.locator('form').get_by_role('button', name=re.compile('Update|Submit|Save')).click()
        expect(self.page.get_by_role('cell', name='EDITED CLIENT', exact=True)).to_be_visible()
        self.post('/AddClient', {'PANNo':'ABCDE1234F','Name':'DUPLICATE','Group':'TEST GROUP'})
        self.navigate('/ClientSetup')
        expect(self.page.get_by_text('Client Already Exist.')).to_be_visible()
        self.page.locator('#table-search').fill('NOT A CLIENT')
        self.page.locator('#table-search').press('End')
        expect(self.page.get_by_role('cell', name='EDITED CLIENT', exact=True)).to_be_hidden()
        self.page.locator('#table-search').fill('EDITED CLIENT')
        self.page.locator('#table-search').press('End')
        expect(self.page.get_by_role('cell', name='EDITED CLIENT', exact=True)).to_be_visible()

    def test_profile_email_saved_and_password_visibility(self):
        self.signed_in()
        self.navigate('/user-profile/')
        self.page.locator('#emailConfigToggle').click()
        self.page.get_by_placeholder('Enter Email Id', exact=True).fill('e2e@example.test')
        self.page.locator('#emailConfigContent [name="app_password"]').fill('e2e-fake-password')
        self.page.get_by_role('button', name='Update Email').click()
        expect(self.page.get_by_text('Profile updated successfully!')).to_be_visible()
        self.page.reload()
        expect(self.page.get_by_placeholder('Enter Email Id', exact=True)).to_have_value('e2e@example.test')
        self.page.locator('#passwordConfigToggle').click()
        self.page.locator('#toggleOldPassword').click()
        expect(self.page.locator('#inputPassword_up')).to_have_attribute('type', 'text')

    def test_accounting_journal_payment_persists(self):
        self.signed_in()
        self.navigate('/accounting/')
        self.page.locator('[data-bs-target="#transactionModal"]').first.click()
        form = self.page.locator('#transactionModal form')
        form.locator('#trans_group').select_option(str(self.group.pk))
        form.locator('#trans_jv').check()
        form.locator('#trans_amount').fill('40')
        form.locator('#trans_remark').fill('E2E journal payment')
        form.locator('#add_date_time').fill(timezone.localtime().strftime('%Y-%m-%dT%H:%M:%S'))
        form.get_by_role('button', name='Save', exact=True).click()
        expect(self.page.locator('textarea').filter(has_text='E2E journal payment')).to_be_visible()
        self.page.reload()
        expect(self.page.locator('textarea').filter(has_text='E2E journal payment')).to_be_visible()
        self.stop_browser()
        self.assertTrue(Accounting.objects.filter(user=self.user, amount=40, jv=True, remark='E2E journal payment').exists())

    def test_shared_link_expired_and_missing(self):
        response = self.navigate(f'/access-link/{self.expired_link.pk}/BUY')
        self.assertEqual(response.status, 403)
        expect(self.page.get_by_role('heading', name='This link has expired.')).to_be_visible()
        self.assertEqual(self.navigate(f'/access-link/{uuid.uuid4()}/BUY').status, 404)

    def test_shared_link_guest_shows_only_assigned_group(self):
        self.navigate(f'/access-link/{self.link.pk}/BUY')
        expect(self.page.locator('input[value="ABCDE1234F"]')).to_be_visible()
        expect(self.page.get_by_text('PRIVATE GROUP', exact=True)).to_have_count(0)

    def test_whatsapp_buy_ui_uses_supplied_number(self):
        self.signed_in()
        self.navigate(f'/{self.ipo.pk}/BUY')
        self.page.locator('[name="item_id"]').select_option(label='TEST GROUP')
        self.page.locator('[name="datetime"]').fill(timezone.localtime().strftime('%Y-%m-%dT%H:%M'))
        self.page.locator('[name="KostakQTY"]').fill('1')
        self.page.locator('[name="KostakRate"]').fill('100')
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"messages":[{"id":"e2e-message"}]}'
        with patch('whatsapp.client.requests.post', return_value=response) as send:
            with self.page.expect_response(lambda r: '/whatsapp/buy/' in r.url) as sent:
                self.page.get_by_role('button', name='Send to WhatsApp').click()
            self.assertEqual(sent.value.status, 200)
            expect(self.page.get_by_role('heading', name='Recent Orders', exact=False)).to_be_visible()
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.kwargs['json']['to'], '91'+PHONE)
        self.stop_browser()
        self.assertEqual(Order.objects.filter(user=self.user, OrderIPOName=self.ipo).count(), 2)


def invalid_login(username, password, message):
    def test(self):
        self.login(username, password)
        expect(self.page.get_by_text(message)).to_be_visible()
        expect(self.page).to_have_url(self.live_server_url+'/login')
    return test

for name, username, password, message in [
    ('wrong_password','e2e-broker','wrong','Username or Password is Incorrect'),
    ('unknown_user','nobody','wrong','Username or Password is Incorrect'),
    ('inactive','e2e-inactive','test-password-123','Username or Password is Incorrect'),
    ('expired','e2e-expired','test-password-123','Your account has expired. Please contact support.')]:
    setattr(Workflows, 'test_login_'+name, invalid_login(username,password,message))
