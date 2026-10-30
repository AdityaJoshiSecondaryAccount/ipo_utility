import django_filters
from django_filters import DateFilter

from .models import *


class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = OrderDetail
        fields = '__all__'
        exclude = ['OrderDetailIPOName', 'IPOType',
                   'Rate', 'OrderDetailPANNo', 'AllotedQty', 'ApplicationNumber']
