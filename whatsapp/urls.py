from django.urls import path

from . import views


app_name = "whatsapp"

urlpatterns = [
    path("buy/<int:ipo_id>/send/", views.send_buy_order, name="send_buy_order"),
    path("sell/<int:ipo_id>/send/", views.send_sell_order, name="send_sell_order"),
]

