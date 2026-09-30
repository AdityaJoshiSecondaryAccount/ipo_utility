"""Fresh, deterministic fixtures; only called after the test runner creates the DB."""
from datetime import timedelta
from django.contrib.auth.models import Group
from django.utils import timezone
from home.models import (CustomUser, CurrentIpoName, GroupDetail, ClientDetail,
                         Order, OrderDetail, Accounting, SharedLink)

PHONE = '7016868618'
PASSWORD = 'test-password-123'


def seed(case):
    broker = Group.objects.create(name='Broker')
    customer = Group.objects.create(name='Customer')
    def user(name, role=None, **kwargs):
        u = CustomUser.objects.create_user(username=name, password=PASSWORD,
            Expiry_Date=kwargs.pop('Expiry_Date', timezone.localdate()+timedelta(days=30)), **kwargs)
        if role:
            u.groups.add(role)
        return u
    case.user = user('e2e-broker', broker, Mobileno=PHONE)
    case.other = user('e2e-other', broker)
    case.group = GroupDetail.objects.create(user=case.user, GroupName='TEST GROUP', MobileNo=PHONE)
    case.other_group = GroupDetail.objects.create(user=case.other, GroupName='PRIVATE GROUP', MobileNo=PHONE)
    case.customer = user('e2e-customer', customer, Broker_id=str(case.user.pk), Group_id=str(case.group.pk))
    case.admin_user = user('e2e-admin', broker, is_staff=True, is_superuser=True)
    user('e2e-inactive', broker, is_active=False)
    user('e2e-expired', broker, Expiry_Date=timezone.localdate()-timedelta(days=1))
    user('e2e-unassigned')
    case.ipo = CurrentIpoName.objects.create(user=case.user, IPOType='MAINBOARD', IPOName='TEST IPO',
        IPOPrice=150, PreOpenPrice=150, LotSizeRetail=100, LotSizeSHNI=1400, LotSizeBHNI=6700,
        TotalIPOSzie='1200', RetailPercentage='35', SHNIPercentage='5', BHNIPercentage='10',
        ExpecetdRetailApplication='2500000', ExpecetdSHNIApplication='150000',
        ExpecetdBHNIApplication='50000', ProfitMargin='15', Premium='20')
    case.sme = CurrentIpoName.objects.create(user=case.user, IPOType='SME', IPOName='TEST SME',
        IPOPrice=100, PreOpenPrice=100, LotSizeRetail=1200, TotalIPOSzie='100',
        RetailPercentage='35', ExpecetdRetailApplication='100000', ProfitMargin='15', Premium='20')
    case.client_record = ClientDetail.objects.create(user=case.user, Group=case.group,
        PANNo='ABCDE1234F', Name='TEST CLIENT', ClientIdDpId='1234567890123456')
    case.order = Order.objects.create(user=case.user, OrderGroup=case.group, OrderIPOName=case.ipo,
        OrderType='BUY', Rate=100, Quantity=1, OrderCategory='Kostak', InvestorType='RETAIL',
        OrderDate=timezone.localdate(), OrderTime='10:30:00', Amount=-100)
    case.detail = OrderDetail.objects.create(user=case.user, Order=case.order,
        OrderDetailPANNo=case.client_record, PreOpenPrice=150, AllotedQty=0, Amount=-100)
    case.entry = Accounting.objects.create(user=case.user, group=case.group, ipo=case.ipo,
        amount=25, amount_type='credit', date_time=timezone.now(), remark='E2E opening payment')
    case.link = SharedLink.objects.create(user=case.user, group=case.group, ipo=case.ipo,
        expiry_at=timezone.now()+timedelta(days=1))
    case.expired_link = SharedLink.objects.create(user=case.user, group=case.group, ipo=case.ipo,
        expiry_at=timezone.now()-timedelta(days=1))
