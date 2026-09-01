from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now, timedelta
from django.utils import timezone
import uuid

# Create your models here.


class CustomUser(AbstractUser):
    Broker_id = models.CharField(max_length=1000, default=None, null=True)
    Group_id = models.CharField(max_length=1000, default=None, null=True)
    Order_limit = models.IntegerField(blank=True, null=True)
    IPO_limit = models.IntegerField(blank=True, null=True)
    Client_limit = models.IntegerField(blank=True, null=True)
    Group_limit = models.IntegerField(blank=True, null=True)
    Premium_Order_limit = models.IntegerField(blank=True, null=True)
    Allotment_access = models.BooleanField(max_length=100, default=False, null=True)
    Expiry_Date = models.DateField(default=now() + timedelta(days=365))
    AppPassword = models.CharField(max_length=100, default=None,blank=True,null=True)
    # Broker_Id = models.OneToOneField(User, on_delete=models.CASCADE)

    TelegramApi_id = models.CharField(max_length=100, blank=True, null=True)
    TelegramApi_key = models.CharField(max_length=100, blank=True, null=True)
    Mobileno = models.CharField(max_length=15, blank=True, null=True)
    Telegram_session = models.CharField(max_length=10000, blank=True, null=True)

class CurrentIpoName(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="IPO", null=True)
    IPOType = models.CharField(max_length=100, null=True, default=None)
    IPOName = models.CharField(max_length=100, default=None)
    IPOPrice = models.FloatField(blank=True)
    PreOpenPrice = models.FloatField(default=0)
    LotSizeRetail = models.FloatField(null=True, default=None)
    LotSizeSHNI = models.FloatField(null=True, default=None)
    LotSizeBHNI = models.FloatField(null=True, default=None)    
    Remark = models.CharField(max_length=500, blank=True)
    TotalIPOSzie = models.CharField(max_length=100, blank=True)
    RetailPercentage = models.CharField(max_length=100, blank=True)
    SHNIPercentage = models.CharField(max_length=100, blank=True)
    BHNIPercentage = models.CharField(max_length=100, blank=True)
    ExpecetdRetailApplication = models.CharField(max_length=100, blank=True)
    ExpecetdSHNIApplication = models.CharField(max_length=100, null=True, blank=True)
    ExpecetdBHNIApplication = models.CharField(max_length=100, null=True, blank=True)
    ProfitMargin = models.CharField(max_length=100, blank=True)
    Premium = models.CharField(max_length=100, blank=True)
    Active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.IPOName = self.IPOName.upper()
        super(CurrentIpoName, self).save(*args, **kwargs)

    def __str__(self):
        return self.IPOName


class GroupDetail(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="Group", null=True)
    GroupName = models.CharField(max_length=100, default=None)
    MobileNo = models.CharField(max_length=100, blank=True)
    Address = models.CharField(max_length=500,  blank=True)
    Collection = models.FloatField(default=0)
    Remark = models.CharField(max_length=500,  blank=True)
    Email = models.CharField(max_length=100,  blank=True)
    Active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.GroupName = self.GroupName.upper()
        super(GroupDetail, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.GroupName


# class PremiumGroupDetail(models.Model):
#     user = models.ForeignKey(
#         CustomUser, on_delete=models.CASCADE, related_name="PremiumGroup", null=True)
#     GroupName = models.CharField(max_length=100, default=None)
#     GroupType = models.CharField(max_length=100, default=None)
#     MobileNo = models.CharField(max_length=100, blank=True)
#     Address = models.CharField(max_length=500,  blank=True)
#     Remark = models.CharField(max_length=500,  blank=True)
#     Active = models.BooleanField(default=True)

#     def __str__(self):
#         return self.GroupName


class ClientDetail(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="Client", null=True)
    PANNo = models.CharField(max_length=10, default=None)
    Name = models.CharField(max_length=100,  blank=True)
    # Group = models.CharField(max_length=100,  blank=True)
    Group = models.ForeignKey(
        GroupDetail, default=None, on_delete=models.SET_DEFAULT)
    ClientIdDpId = models.CharField(max_length=100,  blank=True)
    Active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.PANNo = self.PANNo.upper()
        self.Name = self.Name.upper()
        # self.Group.GroupName = self.Group.GroupName.upper()
        super(ClientDetail, self).save(*args, **kwargs)

    def __str__(self):
        return self.Name

class Accounting(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="accounting", null=True)
    ipo = models.ForeignKey(
        CurrentIpoName, blank=True, null=True, default=None, on_delete=models.SET_DEFAULT)   
    group = models.ForeignKey(
        GroupDetail,blank=True, null=True, default=None, on_delete=models.SET_DEFAULT)  
    amount = models.DecimalField(max_digits=12, decimal_places=2)  
    amount_type = models.CharField(max_length=10, choices=[("credit", "Credit"), ("debit", "Debit")])
    ipo_name = models.CharField( max_length=1000, default=None, null=True )
    group_name = models.CharField( max_length=1000, default=None, null=True )
    status = models.BooleanField(default=0)
    remark = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField()
    jv = models.BooleanField( default='False') 
  

    def __str__(self):
         return f"{self.ipo} - {self.group} - {self.amount_type} - {self.amount}"

class Order(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="Order", null=True)
    OrderGroup = models.ForeignKey(
        GroupDetail, default=None, on_delete=models.SET_DEFAULT)
    OrderIPOName = models.ForeignKey(
        CurrentIpoName, default=None, on_delete=models.SET_DEFAULT, related_name='IPOName1')
    OrderType = models.CharField(max_length=100, default=None)  # Buy/Sell
    Rate = models.FloatField(default=None)
    Quantity = models.FloatField(default=None)
    # kostak......
    OrderCategory = models.CharField(max_length=100, default=None)
    Amount = models.FloatField(default=0)
    OrderDate = models.DateField()
    Active = models.BooleanField(default=True)
    OrderTime = models.TimeField(null=True)
    InvestorType = models.CharField(max_length=100, default=None, null=True)
    Method = models.CharField(max_length=100, default=None, null=True)
    Telly = models.CharField(max_length=100, default='False', null=True)
    remark = models.JSONField(null=True, blank=True, default=None)
    
    def save(self, *args, **kwargs):
        # self.OrderGroup.GroupName = self.OrderGroup.GroupName.upper()
        # self.OrderIPOName.IPOName = self.OrderIPOName.IPOName.upper()  
        self.OrderType = self.OrderType.upper()
        # self.OrderCategory = self.OrderCategory.upper()
        super(Order, self).save(*args, **kwargs)


def __str__(self):
    return self.OrderIPOName


class OrderDetail(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="OrderDetail", null=True)
    Order = models.ForeignKey(
        Order, default=None, on_delete=models.SET_DEFAULT, null=True)
    OrderDetailPANNo = models.ForeignKey(
        ClientDetail, blank=True, null=True, default=None, on_delete=models.SET_DEFAULT)
    AllotedQty = models.FloatField(blank=True, null=True)
    PreOpenPrice = models.FloatField(default=0)
    ApplicationNumber = models.CharField(
        max_length=100, blank=True)
    DematNumber = models.CharField(
        max_length=100, blank=True)
    Amount = models.FloatField(default=0)
    Active = models.BooleanField(max_length=100, default=True)


def __str__(self):
    return self.OrderDetailIPOName


# class PremiumOrderDetail(models.Model):
#     user = models.ForeignKey(
#         CustomUser, on_delete=models.CASCADE, null=True)
#     PremiumOrderDetaillGroup = models.ForeignKey(
#         GroupDetail, default=None, on_delete=models.SET_DEFAULT)
#     PremiumOrderDetailIPOName = models.ForeignKey(
#         CurrentIpoName, default=None, on_delete=models.SET_DEFAULT)
#     Rate = models.FloatField(default=None)
#     Qty = models.FloatField(blank=True, null=True)
#     Amount = models.FloatField(default=0)
#     OrderType = models.CharField(max_length=100, default=None)
#     SellDate = models.DateField()
#     Active = models.BooleanField(default=True)


# def __str__(self):
#     return self.PremiumOrderDetailIPOName


class RateList(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    RateListIPOName = models.ForeignKey(
        CurrentIpoName, default=None, on_delete=models.SET_DEFAULT)
    kostakBuyRate = models.FloatField(default=0)
    KostakBuyQty = models.FloatField(default=0)
    kostakSellRate = models.FloatField(default=0)
    KostakSellQty = models.FloatField(default=0)
    SubjecToBuyRate = models.FloatField(default=0)
    SubjecToBuyQty = models.FloatField(default=0)
    SubjecToSellRate = models.FloatField(default=0)
    SubjecToSellQty = models.FloatField(default=0)
    PremiumBuyRate = models.FloatField(default=0)
    PremiumBuyQty = models.FloatField(default=0)
    PremiumSellRate = models.FloatField(default=0)
    PremiumSellQty = models.FloatField(default=0)


def __str__(self):
    return self.user

class SharedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    group = models.ForeignKey('GroupDetail', on_delete=models.CASCADE)
    ipo = models.ForeignKey('CurrentIpoName', on_delete=models.CASCADE)
    expiry_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_mail_sent = models.BooleanField(default=False)

    def is_valid(self):
        return timezone.now() < self.expiry_at