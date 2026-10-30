from django.urls import path

from . import views


app_name = "whatsapp"

urlpatterns = [
    path("webhook/", views.webhook, name="webhook"),
    path("flow-endpoint/", views.flow_data_endpoint, name="flow_data_endpoint"),
    path("buy/<int:ipo_id>/send/", views.send_buy_order, name="send_buy_order"),
    path("sell/<int:ipo_id>/send/", views.send_sell_order, name="send_sell_order"),
]

