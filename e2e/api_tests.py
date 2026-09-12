"""Request-level contracts stay separate from browser journeys."""
import json
import re
from datetime import timedelta
from urllib.parse import quote
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.utils import timezone
from playwright.sync_api import sync_playwright
from home.models import Accounting, AccountingAuditLog, GroupDetail, SharedLink, Order, OrderDetail, ClientDetail
from .inventory import discover
from .seed import seed, PHONE


class APIBase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        if settings.SETTINGS_MODULE != 'userproject.e2e_settings':
            raise RuntimeError('Use scripts/run_e2e.py')
        super().setUpClass()

    def setUp(self):
        seed(self)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.api = self.pw.request.new_context(base_url=self.live_server_url)
        self.addCleanup(self.api.dispose)
        self.api.get('/login')

    def token(self):
        return next(c['value'] for c in self.api.storage_state()['cookies'] if c['name']=='csrftoken')

    def login(self, username='e2e-broker'):
        response = self.api.post('/login', form={'username':username, 'password':'test-password-123'},
            headers={'X-CSRFToken':self.token()}, max_redirects=0)
        self.assertEqual(response.status, 302)

    def post(self, path, form=None, data=None):
        return self.api.post(path, form=form, data=data, headers={'X-CSRFToken':self.token()}, max_redirects=0)

    def orm(self, fn):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        def run():
            try:
                return fn()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(1) as pool:
            return pool.submit(run).result()


class Contracts(APIBase):
    def test_bulk_deletes_preserve_referenced_clients_groups_and_foreign_data(self):
        self.login()
        self.assertTrue(self.post('/BulkDeleteClients',form={'ids[]':str(self.client_record.pk)}).json()['success'])
        self.assertTrue(self.orm(lambda: ClientDetail.objects.filter(pk=self.client_record.pk).exists()))
        response=self.post('/BulkDeleteGroup',data={'group_ids':[self.group.pk,self.other_group.pk]})
        self.assertEqual(response.json()['blocked_count'],1)
        self.assertEqual(self.orm(lambda: GroupDetail.objects.count()),2)
        response=self.post(f'/{self.ipo.pk}/BulkDeleteOrders/',data={'order_ids':[self.order.pk]})
        self.assertEqual(response.json()['status'],'success')
        self.assertFalse(self.orm(lambda: OrderDetail.objects.filter(Order_id=self.order.pk).exists()))
        self.assertFalse(self.orm(lambda: Order.objects.filter(pk=self.order.pk).exists()))
        self.post('/BulkDeleteClients',form={'ids[]':str(self.client_record.pk)})
        self.assertFalse(self.orm(lambda: ClientDetail.objects.filter(pk=self.client_record.pk).exists()))
        self.post('/BulkDeleteGroup',data={'group_ids':[self.group.pk]})
        self.assertTrue(self.orm(lambda: Accounting.objects.filter(pk=self.entry.pk,group=None,group_name='TEST GROUP').exists()))

    def test_pan_validation_update_clear_and_billing_calculation(self):
        self.login()
        path=f'/{self.ipo.pk}/BUY/AddPan-{self.detail.pk}/All/All/All/None/None'
        self.post(path,form={'PAN':'INVALID','clientname':'Invalid'})
        self.assertEqual(self.orm(lambda: OrderDetail.objects.get(pk=self.detail.pk).OrderDetailPANNo_id),self.client_record.pk)
        self.post(path,form={'PAN':'ABCDE1234F','clientname':'TEST CLIENT','allotedqty':'100','Application':'E2E123','DematNo':'1234567890123456'})
        self.assertEqual(self.orm(lambda: OrderDetail.objects.get(pk=self.detail.pk).AllotedQty),100)
        self.post(f'/{self.ipo.pk}/updatepreopenprice/All/All/All',form={'PreOpenPrice':'160'})
        self.assertEqual(self.orm(lambda: OrderDetail.objects.get(pk=self.detail.pk).Amount),900)
        self.post(path,form={'PAN':''})
        self.assertIsNone(self.orm(lambda: OrderDetail.objects.get(pk=self.detail.pk).OrderDetailPANNo_id))

    def test_bulk_payment_is_atomic_on_invalid_total(self):
        self.login()
        item={'group_id':self.group.pk,'jv':1,'amount':40,'amount_type':'credit',
              'date_time':timezone.localtime().strftime('%Y-%m-%dT%H:%M:%S'),'remark':'E2E allocation'}
        before=self.orm(lambda: Accounting.objects.count())
        response=self.post('/bulk_ipo_transactions/',form={'transactions':json.dumps([item]),'master_amount':'50','master_amount_type':'credit'})
        self.assertEqual(response.status,400)
        self.assertEqual(self.orm(lambda: Accounting.objects.count()),before)
        response=self.post('/bulk_ipo_transactions/',form={'transactions':json.dumps([item]),'master_amount':'40','master_amount_type':'credit'})
        self.assertEqual(response.json()['status'],'success')
        self.assertEqual(self.orm(lambda: Accounting.objects.count()),before+1)

    def test_payment_amount_boundaries_and_ownership(self):
        self.login()
        before=self.orm(lambda: Accounting.objects.count())
        for value in ('0','-1','NaN','Infinity','10000000000'):
            with self.subTest(amount=value):
                form={'group_id':str(self.group.pk),'jv':'1','amount':value,'amount_type':'credit',
                      'date_time':'2026-09-11T10:30:00'}
                self.post('/add-transaction/',form=form)
                self.assertEqual(self.orm(lambda: Accounting.objects.count()),before)
        form['amount']='10'; form['group_id']=str(self.other_group.pk)
        self.post('/add-transaction/',form=form)
        self.assertEqual(self.orm(lambda: Accounting.objects.count()),before)
        form['group_id']=str(self.group.pk); form['amount']='1.001'
        self.post('/add-transaction/',form=form)
        self.assertTrue(self.orm(lambda: Accounting.objects.filter(user=self.user,amount='1.00',jv=True).exists()))

    def test_order_update_changes_rate_and_quantity(self):
        self.login()
        response=self.post(f'/{self.ipo.pk}/{self.order.pk}/UpdateOrder/All/All/All',form={
            'Group':'TEST GROUP','OrderType':'BUY','Qty':'2','InvestorType':'RETAIL',
            'OrderCategory':'Kostak','Rate':'125','datetime':'2026-09-11T10:30:00'})
        self.assertEqual(response.status,302)
        self.assertEqual(self.orm(lambda: Order.objects.get(pk=self.order.pk).Rate),125)
        self.assertEqual(self.orm(lambda: OrderDetail.objects.filter(Order_id=self.order.pk).count()),2)

    def test_accounting_delete_reason_restore_and_audit(self):
        self.login()
        path = f'/soft-delete-accounting/{self.entry.pk}/'
        self.assertEqual(self.post(path, data={'reason':''}).status, 400)
        self.assertTrue(self.post(path, data={'reason':'E2E correction'}).json()['success'])
        self.assertTrue(self.orm(lambda: Accounting.objects.get(pk=self.entry.pk).is_deleted))
        self.assertTrue(self.post(f'/restore-accounting/{self.entry.pk}/', data={}).json()['success'])
        self.assertFalse(self.orm(lambda: Accounting.objects.get(pk=self.entry.pk).is_deleted))
        self.assertEqual(self.orm(lambda: AccountingAuditLog.objects.filter(accounting_id=self.entry.pk).count()), 2)

    def test_accounting_foreign_owner_delete_is_404(self):
        self.login('e2e-other')
        self.assertEqual(self.post(f'/soft-delete-accounting/{self.entry.pk}/', data={'reason':'Invalid owner'}).status,404)
        self.assertFalse(self.orm(lambda: Accounting.objects.get(pk=self.entry.pk).is_deleted))

    def test_shared_link_create_update_delete(self):
        self.login()
        expiry=(timezone.localtime()+timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        response=self.post('/generate-shared-link/', form={'ipo_id':str(self.ipo.pk),'group_name':'TEST GROUP','expiry_at':expiry})
        self.assertEqual(response.json()['status'],'success')
        pk=response.json()['link'].rstrip('/').split('/')[-1]
        self.assertEqual(self.post(f'/update-link/{pk}/',form={'expiry':expiry}).json()['status'],'success')
        self.assertEqual(self.post('/delete-link/',form={'link_id':pk}).json()['status'],'success')
        self.assertFalse(self.orm(lambda: SharedLink.objects.filter(pk=pk).exists()))

    def test_group_server_validation(self):
        self.login()
        for mobile,email,message in [('123','','Invalid Mobile Number.'),(PHONE,'bad-email','Invalid email format.')]:
            self.post('/AddGroup',form={'GroupName':'INVALID GROUP','MobileNo':mobile,'Email':email})
            self.assertIn(message,self.api.get('/GroupSetup').text())
            self.assertFalse(self.orm(lambda: GroupDetail.objects.filter(GroupName='INVALID GROUP').exists()))


def route_path(case, route):
    values={'IPOid':case.ipo.pk,'ipo_id':case.ipo.pk,'OrderId':case.order.pk,'OrderDetailId':case.detail.pk,
        'PanNoId':case.client_record.pk,'PANNoId':case.client_record.pk,'GroupNameId':case.group.pk,
        'group_id':case.group.pk,'entry_id':case.entry.pk,'IPOType':'All','IPOTypefilter':'All',
        'OrderType':'BUY','Ordtyp':'BUY','order_type':'BUY','Action':'BUY','value':'A',
        'OrderDate':'All','OrderTime':'All','link_id':case.link.pk,'linkId':case.link.pk,
        'batch_id':'00000000-0000-0000-0000-000000000001','Rate':'All','selectgroup':'TEST GROUP'}
    return re.sub(r'<(?:[^:>]+:)?([^>]+)>',lambda m:quote(str(values.get(m[1],'All')),safe=''),route)


class AnonymousRoutes(APIBase):
    pass


# Only explicit public login/logout/shared links are exempt. GET safety is independent of CSRF.
PUBLIC={'loginUser','logoutUser','resolve_shared_link'}
for index, record in enumerate(discover()):
    if record['view'] in PUBLIC:
        continue
    def check(self, record=record):
        path=route_path(self,record['route'])
        response=self.api.get(path,max_redirects=0)
        if record['view'] == 'get_rates_json':
            self.assertEqual(response.json(), {'rates': []})
            return
        if record['view'] == 'update_telly_status':
            self.assertEqual(response.json(), {'success': False, 'error': 'Invalid request'})
            return
        if record['view'] in ('save_transaction','save_transaction_group','ipo_transaction','ipo_transaction1'):
            self.assertEqual(response.json(), {'status':'error','message':'Invalid request'})
            return
        if record['view'] == 'update_all_expiries':
            self.assertEqual(response.status,400)
            self.assertEqual(response.json(), {'status':'error','message':'Invalid request.'})
            return
        self.assertIn(response.status,(301,302,401,403,405),
            f"Anonymous {path}: HTTP {response.status}; expected access denial or method restriction")
        if response.status in (301,302):
            # A redirect must not expose data; destination is recorded in the assertion.
            self.assertTrue(response.headers.get('location'))
    setattr(AnonymousRoutes,f'test_{index:03d}_{record["view"]}',check)
