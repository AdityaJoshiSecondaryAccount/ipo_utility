import django_filters
from django_filters import DateFilter

from .models import *


class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = OrderDetail
        fields = '__all__'
        exclude = ['OrderDetailIPOName', 'IPOType',
                   'Rate', 'OrderDetailPANNo', 'AllotedQty', 'ApplicationNumber']


# from rest_framework import serializers
# from .models import OrderDetail


# class StringSerializer(serializers.StringRelatedField):
#     def to_internal_value(self, value):
#         return value


# class JournalSerializer(serializers.ModelSerializer):
#     author = StringSerializer(many=False)
#     categories = StringSerializer(many=True)

#     class Meta:
#         model = OrderDetail
#         fields = ('__all__')
